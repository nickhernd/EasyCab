from confluent_kafka import Producer, Consumer, KafkaError
import json
import time
import os
import random

class ECCustomer:
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self.kafka_broker = os.environ.get('KAFKA_BROKER', 'kafka:9092')
        print(f"Customer {customer_id} connecting to Kafka at {self.kafka_broker}")
        
        # Configuración del productor
        producer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'debug': 'all'
        }
        self.producer = Producer(producer_conf)

        # Configuración del consumidor
        consumer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': f'customer_{customer_id}',
            'auto.offset.reset': 'earliest',
            'debug': 'all'
        }
        self.consumer = Consumer(consumer_conf)
        self.consumer.subscribe(['centralresponses'])

    def request_taxi(self, destination):
        request = {
            'customer_id': self.customer_id,
            'destination': destination,
            'timestamp': time.time()
        }
        
        print(f"Sending request for destination {destination}")
        try:
            self.producer.produce('customerrequests', 
                                json.dumps(request).encode('utf-8'))
            self.producer.flush()
            print(f"Request sent successfully")
            return True
        except Exception as e:
            print(f"Error sending request: {e}")
            return False

    def wait_for_response(self, timeout=10):
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                print("Timeout waiting for response")
                return None

            msg = self.consumer.poll(1.0)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Consumer error: {msg.error()}")
                continue

            try:
                response = json.loads(msg.value().decode('utf-8'))
                print(f"Received response: {response}")
                return response
            except json.JSONDecodeError:
                print(f"Received invalid JSON response")
            except Exception as e:
                print(f"Error processing response: {e}")

    def run(self):
        destinations = ['A', 'B', 'C', 'D', 'E']
        
        while True:
            try:
                # Elegir un destino aleatorio
                destination = random.choice(destinations)
                
                # Enviar solicitud
                if self.request_taxi(destination):
                    # Esperar respuesta
                    response = self.wait_for_response()
                    if response:
                        print(f"Got response for destination {destination}: {response}")
                    else:
                        print(f"No response received for destination {destination}")
                
                # Esperar antes de la siguiente solicitud
                time.sleep(4)  # Esperar 4 segundos entre solicitudes

            except KeyboardInterrupt:
                print("Customer service stopping...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

if __name__ == "__main__":
    customer_id = os.environ.get('CUSTOMER_ID', '1')
    customer = ECCustomer(customer_id)
    customer.run()