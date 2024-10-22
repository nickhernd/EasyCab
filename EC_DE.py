from confluent_kafka import Producer, Consumer, KafkaError
import json
import threading
import time
import socket
import os

class DigitalEngine:
    def __init__(self, taxi_id):
        self.taxi_id = taxi_id
        self.kafka_broker = os.environ.get('KAFKA_BROKER', 'kafka:9092')
        self.sensor_port = int(os.environ.get('SENSOR_PORT', 5000))
        
        # Estado del vehículo
        self.position = [1, 1]  # Posición inicial
        self.state = 'IDLE'     # Estado inicial
        self.destination = None
        self.current_ride = None
        self.sensor_status = 'OK'
        
        # Configuración Kafka
        self.setup_kafka()
        
        # Configuración servidor TCP para sensores
        self.setup_sensor_server()
        
        self.is_running = True

    def setup_kafka(self):
        """Configura las conexiones Kafka"""
        # Productor para enviar estados
        self.producer = Producer({
            'bootstrap.servers': self.kafka_broker,
            'client.id': f'taxi-{self.taxi_id}'
        })

        # Consumidor para instrucciones
        self.consumer = Consumer({
            'bootstrap.servers': self.kafka_broker,
            'group.id': f'taxi-{self.taxi_id}',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(['taxiinstructions'])

    def setup_sensor_server(self):
        """Configura el servidor TCP para recibir datos de sensores"""
        self.sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sensor_socket.bind(('0.0.0.0', self.sensor_port))
        self.sensor_socket.listen(5)
        print(f"Sensor server listening on port {self.sensor_port}")

    def handle_sensor_connection(self, connection, address):
        """Maneja las conexiones de los sensores"""
        print(f"New sensor connection from {address}")
        while self.is_running:
            try:
                data = connection.recv(1024)
                if not data:
                    break
                
                sensor_data = json.loads(data.decode('utf-8'))
                self.process_sensor_data(sensor_data)
            except Exception as e:
                print(f"Error processing sensor data: {e}")
                break
        connection.close()

    def process_sensor_data(self, sensor_data):
        """Procesa los datos recibidos de los sensores"""
        status = sensor_data.get('status', 'OK')
        if status != self.sensor_status:
            self.sensor_status = status
            if status != 'OK':
                self.state = 'STOPPED'
                print(f"Emergency stop due to sensor status: {sensor_data}")
            else:
                if self.destination:
                    self.state = 'MOVING'
                print("Resuming normal operation")
        
        self.send_status_update()

    def calculate_next_move(self):
        """Calcula el siguiente movimiento hacia el destino"""
        if not self.destination or self.state != 'MOVING':
            return None
            
        current_x, current_y = self.position
        dest_x, dest_y = self.destination
        
        # Calcular diferencias
        diff_x = dest_x - current_x
        diff_y = dest_y - current_y
        
        # Determinar siguiente movimiento
        new_x = current_x
        new_y = current_y
        
        if diff_x != 0:
            new_x += 1 if diff_x > 0 else -1
        elif diff_y != 0:
            new_y += 1 if diff_y > 0 else -1
            
        # Manejar los límites del mapa (20x20)
        new_x = (new_x + 20) % 20
        new_y = (new_y + 20) % 20
        
        return [new_x, new_y]

    def move(self):
        """Realiza el movimiento del taxi"""
        if self.state == 'MOVING' and self.destination:
            next_position = self.calculate_next_move()
            if next_position:
                self.position = next_position
                self.send_status_update()
                
                # Verificar si llegamos al destino
                if self.position == self.destination:
                    self.state = 'IDLE'
                    self.destination = None
                    print("Reached destination")

    def send_status_update(self):
        """Envía actualización de estado a la central"""
        status = {
            'taxi_id': self.taxi_id,
            'position': self.position,
            'state': self.state,
            'destination': self.destination,
            'current_ride': self.current_ride,
            'sensor_status': self.sensor_status,
            'timestamp': time.time()
        }
        
        try:
            self.producer.produce(
                'taxistatus',
                json.dumps(status).encode('utf-8')
            )
            self.producer.flush()
        except Exception as e:
            print(f"Error sending status update: {e}")

    def process_instruction(self, instruction):
        """Procesa instrucciones recibidas de la central"""
        instruction_type = instruction.get('type')
        
        if instruction_type == 'PICKUP':
            self.destination = instruction.get('destination')
            self.state = 'MOVING'
            self.current_ride = instruction.get('ride_id')
        elif instruction_type == 'STOP':
            self.state = 'STOPPED'
        elif instruction_type == 'RESUME':
            if self.sensor_status == 'OK':
                self.state = 'MOVING'
        elif instruction_type == 'RETURN':
            self.destination = [1, 1]  # Volver a la base
            self.state = 'MOVING'
            self.current_ride = None

    def run(self):
        """Bucle principal del Digital Engine"""
        # Iniciar thread para conexiones de sensores
        sensor_thread = threading.Thread(target=self.accept_sensor_connections)
        sensor_thread.daemon = True
        sensor_thread.start()
        
        # Iniciar thread para movimiento
        movement_thread = threading.Thread(target=self.movement_loop)
        movement_thread.daemon = True
        movement_thread.start()
        
        print(f"Digital Engine running for taxi {self.taxi_id}")
        
        # Bucle principal para procesar instrucciones
        while self.is_running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    print(f"Consumer error: {msg.error()}")
                    continue
                
                instruction = json.loads(msg.value().decode('utf-8'))
                if instruction.get('taxi_id') == self.taxi_id:
                    self.process_instruction(instruction)
                    
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

    def accept_sensor_connections(self):
        """Acepta conexiones de sensores"""
        while self.is_running:
            try:
                connection, address = self.sensor_socket.accept()
                thread = threading.Thread(
                    target=self.handle_sensor_connection,
                    args=(connection, address)
                )
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"Error accepting sensor connection: {e}")

    def movement_loop(self):
        """Bucle para el movimiento del taxi"""
        while self.is_running:
            if self.state == 'MOVING':
                self.move()
            time.sleep(1)  # Actualizar posición cada segundo

    def shutdown(self):
        """Cierra el Digital Engine de manera ordenada"""
        self.is_running = False
        self.sensor_socket.close()
        self.consumer.close()
        self.producer.flush()

if __name__ == "__main__":
    taxi_id = os.environ.get('TAXI_ID', '1')
    digital_engine = DigitalEngine(taxi_id)
    
    try:
        digital_engine.run()
    except KeyboardInterrupt:
        print("Shutting down...")
        digital_engine.shutdown()
    except Exception as e:
        print(f"Fatal error: {e}")
        digital_engine.shutdown()