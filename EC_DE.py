from confluent_kafka import Producer, Consumer, KafkaError
import json
import time
import os
import socket
import threading

class ECDE:
    def __init__(self, taxi_id):
        self.taxi_id = taxi_id
        self.position = [1, 1]  # Posición inicial [x, y]
        self.state = "IDLE"  # Estados: IDLE, MOVING, STOPPED
        self.destination = None
        
        # Configuración de Kafka
        self.kafka_broker = os.environ.get('KAFKA_BROKER', 'kafka:9092')
        print(f"Taxi {taxi_id} connecting to Kafka at {self.kafka_broker}")
        
        # Configuración del productor
        producer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'debug': 'all'
        }
        self.producer = Producer(producer_conf)

        # Configuración del consumidor
        consumer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': f'taxi_{taxi_id}',
            'auto.offset.reset': 'earliest',
            'debug': 'all'
        }
        self.consumer = Consumer(consumer_conf)
        self.consumer.subscribe(['taxi_instructions'])

    def send_status(self):
        status = {
            'taxi_id': self.taxi_id,
            'position': self.position,
            'state': self.state,
            'timestamp': time.time()
        }
        try:
            self.producer.produce('taxi_status', 
                                json.dumps(status).encode('utf-8'))
            self.producer.flush()
            print(f"Status sent: {status}")
        except Exception as e:
            print(f"Error sending status: {e}")

    def move_towards_destination(self):
        if self.state != "MOVING" or not self.destination:
            return False

        moved = False
        # Movimiento en X
        if self.position[0] < self.destination[0]:
            self.position[0] += 1
            moved = True
        elif self.position[0] > self.destination[0]:
            self.position[0] -= 1
            moved = True

        # Movimiento en Y
        if self.position[1] < self.destination[1]:
            self.position[1] += 1
            moved = True
        elif self.position[1] > self.destination[1]:
            self.position[1] -= 1
            moved = True

        # Si llegamos al destino
        if self.position == self.destination:
            self.state = "IDLE"
            self.destination = None
            print(f"Taxi {self.taxi_id} reached destination")

        return moved

    def process_instruction(self, instruction):
        print(f"Processing instruction: {instruction}")
        try:
            if instruction.get('taxi_id') != self.taxi_id:
                return

            if instruction.get('type') == 'MOVE':
                self.destination = instruction.get('destination')
                self.state = "MOVING"
                print(f"Moving to destination: {self.destination}")
            elif instruction.get('type') == 'STOP':
                self.state = "STOPPED"
                print("Stopping taxi")
            elif instruction.get('type') == 'RESUME':
                if self.destination:
                    self.state = "MOVING"
                    print("Resuming movement")
                
        except Exception as e:
            print(f"Error processing instruction: {e}")

    def run(self):
        print(f"Taxi {self.taxi_id} starting...")
        last_status_time = 0
        status_interval = 1.0  # Enviar estado cada segundo

        while True:
            try:
                # Procesar mensajes de Kafka
                msg = self.consumer.poll(0.1)
                if msg is not None:
                    if msg.error():
                        if msg.error().code() != KafkaError._PARTITION_EOF:
                            print(f"Consumer error: {msg.error()}")
                    else:
                        try:
                            instruction = json.loads(msg.value().decode('utf-8'))
                            self.process_instruction(instruction)
                        except json.JSONDecodeError:
                            print("Received invalid JSON instruction")
                        except Exception as e:
                            print(f"Error processing message: {e}")

                # Actualizar posición si está en movimiento
                if self.move_towards_destination():
                    print(f"Taxi {self.taxi_id} moved to {self.position}")

                # Enviar estado periódicamente
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    self.send_status()
                    last_status_time = current_time

                time.sleep(0.1)  # Pequeña pausa para no saturar el CPU

            except KeyboardInterrupt:
                print(f"Taxi {self.taxi_id} stopping...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

if __name__ == "__main__":
    taxi_id = os.environ.get('TAXI_ID', '1')
    taxi = ECDE(taxi_id)
    taxi.run()