import socket
import threading
import logging
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
        self.location = None  # Added to store current location

    def request_service(self, destination):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.central_host, self.central_port))
                message = create_message({
                    'type': 'service_request',
                    'customer_id': self.customer_id,
                    'destination': destination,
                    'current_location': self.location  # Include current location in request
                })
                s.sendall(message)
                data = s.recv(1024)
                response = parse_message(data)
                return response
        except Exception as e:
            logger.error(f"Error requesting service: {str(e)}")
            return None

    def send_location_update(self, location):
        try:
            self.location = location  # Update current location
            send_kafka_message(self.kafka_producer, 'customer_updates', {
                'customer_id': self.customer_id,
                'location': location
            })
            logger.info(f"Location updated: {location}")
        except Exception as e:
            logger.error(f"Error sending location update: {str(e)}")

    def start(self):
        logger.info("Welcome to EasyCab service. Enter 'q' to quit at any time.")
        while True:
            try:
                location = input("Enter your current location (x,y): ")
                if location.lower() == 'q':
                    break
                x, y = map(int, location.split(','))
                self.send_location_update((x, y))

                destination = input("Enter destination (x,y): ")
                if destination.lower() == 'q':
                    break
                x, y = map(int, destination.split(','))
                response = self.request_service((x, y))
                if response:
                    logger.info(f"Service request response: {response}")
                else:
                    logger.warning("No response received from server.")
            except ValueError:
                logger.error("Invalid input format. Please use 'x,y'.")
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")

        logger.info("Thank you for using EasyCab service.")

    def close(self):
        self.kafka_producer.flush()

if __name__ == "__main__":
    kafka_config = {
        'bootstrap.servers': 'localhost:9092'
    }
    customer = ECCustomer('localhost', 8000, kafka_config, 'customer1')
    try:
        customer.start()
    except KeyboardInterrupt:
        logger.info("Shutting down ECCustomer...")
    finally:
        customer.close()
