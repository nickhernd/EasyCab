import socket
import threading
import logging
from confluent_kafka import Producer, Consumer
from kafka_utils import send_kafka_message, receive_kafka_message, create_kafka_producer, create_kafka_consumer
from socket_protocol import create_message, parse_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECDE:
    def __init__(self, central_host, central_port, kafka_config, taxi_id):
        self.central_host = central_host
        self.central_port = central_port
        self.kafka_producer = create_kafka_producer(kafka_config['bootstrap.servers'])
        self.kafka_consumer = create_kafka_consumer(kafka_config['bootstrap.servers'], 'taxi_commands', f'taxi-{taxi_id}')
        self.taxi_id = taxi_id
        self.position = [1, 1]  # Starting position
        self.status = 'AVAILABLE'

    def move_to(self, destination):
        self.position = destination
        self.send_position_update()
        logger.info(f"Moved to {destination}")

    def send_position_update(self):
        try:
            send_kafka_message(self.kafka_producer, 'taxi_updates', {
                'taxi_id': self.taxi_id,
                'position': self.position,
                'status': self.status
            })
            logger.info(f"Position update sent: {self.position}, Status: {self.status}")
        except Exception as e:
            logger.error(f"Error sending position update: {str(e)}")

    def handle_sensor_input(self, sensor_data):
        if sensor_data == 's':
            logger.info("Red light detected. Stopping.")
            self.status = 'STOPPED'
        elif sensor_data == 'p':
            logger.info("Pedestrian detected. Stopping.")
            self.status = 'STOPPED'
        elif sensor_data == 'x':
            logger.info("Flat tire detected. Stopping.")
            self.status = 'OFFLINE'
        self.send_position_update()

    def listen_for_commands(self):
        try:
            while True:
                msg = self.kafka_consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                command = receive_kafka_message(msg)
                if command['type'] == 'MOVE':
                    self.move_to(command['destination'])
                elif command['type'] == 'STOP':
                    self.status = 'STOPPED'
                    logger.info("Stopped by command")
                elif command['type'] == 'RESUME':
                    self.status = 'AVAILABLE'
                    logger.info("Resumed by command")
                self.send_position_update()
        except Exception as e:
            logger.error(f"Error in command listener: {str(e)}")

    def listen_for_sensors(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', 8010))
                s.listen()
                logger.info("Listening for sensor inputs on port 8010")
                while True:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024)
                        self.handle_sensor_input(data.decode())
                        conn.sendall("Received".encode('utf-8'))
        except Exception as e:
            logger.error(f"Error in sensor listener: {str(e)}")

    def start(self):
        command_thread = threading.Thread(target=self.listen_for_commands)
        sensor_thread = threading.Thread(target=self.listen_for_sensors)
        command_thread.start()
        sensor_thread.start()
        logger.info(f"ECDE started for taxi {self.taxi_id}")

    def close(self):
        self.kafka_consumer.close()
        self.kafka_producer.flush()

if __name__ == "__main__":
    kafka_config = {
        'bootstrap.servers': 'localhost:9092'
    }
    de = ECDE('localhost', 8000, kafka_config, 'taxi1')
    try:
        de.start()
    except KeyboardInterrupt:
        logger.info("Shutting down ECDE...")
    finally:
        de.close()
