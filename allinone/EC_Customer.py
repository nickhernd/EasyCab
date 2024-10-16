import os
import socket
import threading
import logging
import time
import json
from confluent_kafka import Producer
from kafka_utils import send_kafka_message, create_kafka_producer
from socket_protocol import create_message, parse_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECCustomer:
    def __init__(self, central_host, central_port, kafka_config, customer_id):
        self.central_host = central_host
        self.central_port = central_port
        self.kafka_producer = create_kafka_producer(kafka_config['bootstrap.servers'])
        self.customer_id = customer_id
        self.location = None
        self.services = self.load_services()

    def load_services(self):
        try:
            with open('customer_requests.txt', 'r') as f:
                return [line.strip() for line in f]
        except Exception as e:
            logger.error(f"Error loading services: {str(e)}")
            return []

    def request_service(self, destination):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.central_host, self.central_port))
                message = create_message({
                    'type': 'SERVICE_REQUEST',
                    'customer_id': self.customer_id,
                    'destination': destination,
                    'current_location': self.location
                })
                s.sendall(message)
                data = s.recv(1024)
                response = parse_message(data)
                
                print(f"Cliente {self.customer_id} ha solicitado un servicio a {destination}")
                
                if response['status'] == 'ASSIGNED':
                    print(f"Servicio asignado al taxi {response['taxi_id']}")
                elif response['status'] == 'QUEUED':
                    print("Servicio en cola, esperando taxi disponible")
                
                return response
        except Exception as e:
            logger.error(f"Error requesting service: {str(e)}")
            return None

    def send_location_update(self, location):
        try:
            self.location = location
            send_kafka_message(self.kafka_producer, 'customer_updates', {
                'customer_id': self.customer_id,
                'location': location
            })
            logger.info(f"Location updated: {location}")
        except Exception as e:
            logger.error(f"Error sending location update: {str(e)}")

    def start(self):
        logger.info(f"Customer {self.customer_id} started")
        for service in self.services:
            try:
                self.send_location_update(service)  
                response = self.request_service(service)
                if response:
                    logger.info(f"Service request response: {response}")
                    if response['status'] == 'ASSIGNED':
                        logger.info(f"Taxi {response['taxi_id']} assigned. Waiting for pickup.")
                    elif response['status'] == 'QUEUED':
                        logger.info("Service request queued. Waiting for assignment.")
                else:
                    logger.warning("No response received from server.")
                time.sleep(4)  
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")

        logger.info(f"Customer {self.customer_id} finished all services")

    def close(self):
        self.kafka_producer.flush()

if __name__ == "__main__":
    kafka_config = {
        'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    }
    customer = ECCustomer('ec_central', 8000, kafka_config, 'customer1')
    try:
        customer.start()
    except KeyboardInterrupt:
        logger.info("Shutting down ECCustomer...")
    finally:
        customer.close()