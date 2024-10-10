import socket
import threading
from kafka import KafkaProducer
from kafka_utils import send_kafka_message
from socket_protocol import create_message, parse_message

class ECCustomer:
    def __init__(self, central_host, central_port, kafka_config, customer_id):
        self.central_host = central_host
        self.central_port = central_port
        self.kafka_producer = KafkaProducer(**kafka_config)
        self.customer_id = customer_id

    def request_service(self, destination):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.central_host, self.central_port))
            message = create_message({
                'type': 'service_request',
                'customer_id': self.customer_id,
                'destination': destination
            })
            s.sendall(message)
            data = s.recv(1024)
            response = parse_message(data)
            return response

    def send_location_update(self, location):
        send_kafka_message(self.kafka_producer, 'customer_updates', {
            'customer_id': self.customer_id,
            'location': location
        })

    def start(self):
        while True:
            destination = input("Enter destination (or 'q' to quit): ")
            if destination.lower() == 'q':
                break
            response = self.request_service(destination)
            print(f"Service request response: {response}")

if __name__ == "__main__":
    kafka_config = {
        'bootstrap_servers': ['localhost:9092']
    }
    customer = ECCustomer('localhost', 8000, kafka_config, 'customer1')
    customer.start()