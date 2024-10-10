import socket
import threading
from kafka import KafkaProducer, KafkaConsumer
from kafka_utils import send_kafka_message, receive_kafka_message
from socket_protocol import create_message, parse_message

class ECDE:
    def __init__(self, central_host, central_port, kafka_config, taxi_id):
        self.central_host = central_host
        self.central_port = central_port
        self.kafka_producer = KafkaProducer(**kafka_config)
        self.kafka_consumer = KafkaConsumer('taxi_commands', **kafka_config)
        self.taxi_id = taxi_id
        self.position = [1, 1]  # Starting position
        self.status = 'AVAILABLE'

    def move_to(self, destination):
        # Simplified movement logic
        self.position = destination
        self.send_position_update()

    def send_position_update(self):
        send_kafka_message(self.kafka_producer, 'taxi_updates', {
            'taxi_id': self.taxi_id,
            'position': self.position,
            'status': self.status
        })

    def handle_sensor_input(self, sensor_data):
        if sensor_data == 's':
            print("Red light detected. Stopping.")
            self.status = 'STOPPED'
        elif sensor_data == 'p':
            print("Pedestrian detected. Stopping.")
            self.status = 'STOPPED'
        elif sensor_data == 'x':
            print("Flat tire detected. Stopping.")
            self.status = 'OFFLINE'
        self.send_position_update()

    def listen_for_commands(self):
        for message in self.kafka_consumer:
            command = receive_kafka_message(message)
            if command['type'] == 'MOVE':
                self.move_to(command['destination'])
            elif command['type'] == 'STOP':
                self.status = 'STOPPED'
            elif command['type'] == 'RESUME':
                self.status = 'AVAILABLE'

    def listen_for_sensors(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 8010))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    data = conn.recv(1024)
                    self.handle_sensor_input(data.decode())
                    conn.sendall("Received".encode('utf-8'))

    def start(self):
        command_thread = threading.Thread(target=self.listen_for_commands)
        sensor_thread = threading.Thread(target=self.listen_for_sensors)

        command_thread.start()
        sensor_thread.start()

if __name__ == "__main__":
    kafka_config = {
        'bootstrap_servers': ['localhost:9092']
    }
    de = ECDE('localhost', 8000, kafka_config, 'taxi1')
    de.start()