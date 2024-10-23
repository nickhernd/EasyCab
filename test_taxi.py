from confluent_kafka import Producer, Consumer
import json
import time
import threading
import random

class TestTaxi:
    def __init__(self, taxi_id):
        self.taxi_id = str(taxi_id)
        self.position = [1, 1]  # Posición inicial
        self.state = 'IDLE'
        self.destination = None
        
        # Configuración Kafka
        self.producer = Producer({'bootstrap.servers': 'localhost:9092'})
        self.consumer = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': f'taxi_{self.taxi_id}',
            'auto.offset.reset': 'earliest'
        })
        self.consumer.subscribe(['taxiinstructions'])
        
        # Control de ejecución
        self.is_running = True
        self.movement_thread = None

    def move_towards_destination(self):
        """Simula el movimiento hacia el destino"""
        if not self.destination:
            return

        # Calcular siguiente movimiento
        next_pos = self.position.copy()
        
        # Mover en X
        if self.position[0] != self.destination[0]:
            next_pos[0] += 1 if self.position[0] < self.destination[0] else -1
            next_pos[0] = next_pos[0] % 20  # Mapa esférico
            
        # Mover en Y
        elif self.position[1] != self.destination[1]:
            next_pos[1] += 1 if self.position[1] < self.destination[1] else -1
            next_pos[1] = next_pos[1] % 20  # Mapa esférico

        # Actualizar posición
        self.position = next_pos
        
        # Verificar si llegó al destino
        if self.position == self.destination:
            self.state = 'IDLE'
            self.destination = None
        
        return self.position == self.destination

    def process_instruction(self, instruction):
        """Procesa instrucciones recibidas"""
        if instruction['type'] == 'PICKUP':
            self.destination = instruction['destination']
            self.state = 'MOVING'
            print(f"Taxi {self.taxi_id}: Yendo a recoger en {self.destination}")
        elif instruction['type'] == 'STOP':
            self.state = 'STOPPED'
        elif instruction['type'] == 'RESUME':
            if self.destination:
                self.state = 'MOVING'
        elif instruction['type'] == 'RETURN':
            self.destination = [1, 1]
            self.state = 'MOVING'

    def send_status(self):
        """Envía el estado actual del taxi"""
        status = {
            'taxi_id': self.taxi_id,
            'position': self.position,
            'state': self.state,
            'timestamp': time.time()
        }
        self.producer.produce('taxistatus', json.dumps(status).encode('utf-8'))
        self.producer.flush()
        print(f"Taxi {self.taxi_id}: Estado enviado -> Pos:{self.position} Estado:{self.state}")

    def movement_loop(self):
        """Bucle principal de movimiento"""
        while self.is_running:
            if self.state == 'MOVING' and self.destination:
                if self.move_towards_destination():
                    print(f"Taxi {self.taxi_id}: Llegó a destino {self.destination}")
                self.send_status()
            time.sleep(1)  # Esperar un segundo entre movimientos

    def instruction_loop(self):
        """Bucle de recepción de instrucciones"""
        while self.is_running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    continue
                
                try:
                    instruction = json.loads(msg.value().decode('utf-8'))
                    print(f"Taxi {self.taxi_id} recibió instrucción: {instruction}")
                    
                    if instruction.get('taxi_id') == self.taxi_id:
                        self.process_instruction(instruction)
                        self.send_status()
                except json.JSONDecodeError:
                    print("Mensaje recibido no es JSON válido")
                except Exception as e:
                    print(f"Error procesando instrucción: {e}")
            except Exception as e:
                print(f"Error en loop de instrucciones: {e}")

    def run(self):
        """Inicia el taxi"""
        # Iniciar thread de movimiento
        self.movement_thread = threading.Thread(target=self.movement_loop)
        self.movement_thread.daemon = True
        self.movement_thread.start()
        
        # Iniciar thread de instrucciones
        self.instruction_thread = threading.Thread(target=self.instruction_loop)
        self.instruction_thread.daemon = True
        self.instruction_thread.start()
        
        # Enviar estado inicial
        self.send_status()
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Detiene el taxi"""
        self.is_running = False
        self.consumer.close()

def run_multiple_taxis(num_taxis):
    """Ejecuta múltiples taxis"""
    taxis = []
    for i in range(num_taxis):
        taxi = TestTaxi(i + 1)
        taxi_thread = threading.Thread(target=taxi.run)
        taxi_thread.daemon = True
        taxi_thread.start()
        taxis.append(taxi)
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        for taxi in taxis:
            taxi.stop()

if __name__ == "__main__":
    num_taxis = 3  # Número de taxis a simular
    run_multiple_taxis(num_taxis)