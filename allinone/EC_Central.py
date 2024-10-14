import socket
import threading
import mysql.connector
import time
import logging
from confluent_kafka import Producer, Consumer
from kafka_utils import send_kafka_message, receive_kafka_message, create_kafka_producer, create_kafka_consumer
from map_utils import update_map, get_current_map
from socket_protocol import create_message, parse_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECCentral:
    def __init__(self, host, port, db_config, kafka_config):
        self.host = host
        self.port = port
        self.db_config = db_config
        self.kafka_producer = create_kafka_producer(kafka_config['bootstrap.servers'])
        self.kafka_consumer = create_kafka_consumer(kafka_config['bootstrap.servers'], 'taxi_updates')
        self.map = [[' ' for _ in range(20)] for _ in range(20)]
        self.lock = threading.Lock()
        self.taxis = {}  

    def start(self):
        try:
            db_thread = threading.Thread(target=self.db_listener)
            kafka_thread = threading.Thread(target=self.kafka_listener)
            socket_thread = threading.Thread(target=self.socket_listener)

            db_thread.start()
            kafka_thread.start()
            socket_thread.start()
        except Exception as e:
            logger.error(f"Error starting ECCentral: {str(e)}")

    def db_listener(self):
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            while True:
                cursor.execute("SELECT * FROM services WHERE status = 'REQUESTED'")
                for service in cursor.fetchall():
                    self.process_service_request(service)

                conn.commit()
                time.sleep(1)  
        except Exception as e:
            logger.error(f"Error in db_listener: {str(e)}")

    def kafka_listener(self):
        try:
            while True:
                msg = self.kafka_consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                self.process_taxi_update(receive_kafka_message(msg))
        except Exception as e:
            logger.error(f"Error in kafka_listener: {str(e)}")

    def socket_listener(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host, self.port))
                s.listen()
                while True:
                    conn, addr = s.accept()
                    client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                    client_thread.start()
        except Exception as e:
            logger.error(f"Error in socket_listener: {str(e)}")

    def handle_client(self, conn, addr):
        try:
            with conn:
                data = conn.recv(1024)
                message = parse_message(data)
                response = self.process_client_request(message)
                conn.sendall(create_message(response))
        except Exception as e:
            logger.error(f"Error handling client {addr}: {str(e)}")

    def process_service_request(self, service):
        try:
            service_id, customer_id, start_location, end_location = service
            available_taxi = self.find_available_taxi(start_location)
            if available_taxi:
                self.assign_taxi_to_service(available_taxi, service_id, start_location, end_location)
            else:
                self.queue_service_request(service_id)
        except Exception as e:
            logger.error(f"Error processing service request: {str(e)}")

    def find_available_taxi(self, location):
        nearest_taxi = None
        min_distance = float('inf')
        for taxi_id, taxi_info in self.taxis.items():
            if taxi_info['status'] == 'AVAILABLE':
                distance = self.calculate_distance(taxi_info['position'], location)
                if distance < min_distance:
                    min_distance = distance
                    nearest_taxi = taxi_id
        return nearest_taxi

    def assign_taxi_to_service(self, taxi_id, service_id, start_location, end_location):
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("UPDATE services SET status = 'IN_PROGRESS', taxi_id = %s WHERE id = %s", 
                           (taxi_id, service_id))
            conn.commit()
            conn.close()

            send_kafka_message(self.kafka_producer, 'taxi_commands', {
                'taxi_id': taxi_id,
                'type': 'PICKUP',
                'location': start_location,
                'destination': end_location
            })

            self.taxis[taxi_id]['status'] = 'BUSY'
        except Exception as e:
            logger.error(f"Error assigning taxi to service: {str(e)}")

    def queue_service_request(self, service_id):
        logger.info(f"Service request {service_id} queued for later processing")
        # Implement actual queuing logic here

    def process_taxi_update(self, update):
        try:
            taxi_id = update['taxi_id']
            position = update['position']
            status = update['status']

            with self.lock:
                self.taxis[taxi_id] = {'position': position, 'status': status}
                self.map = update_map(self.map, update)

            self.send_map_update()
        except Exception as e:
            logger.error(f"Error processing taxi update: {str(e)}")

    def send_map_update(self):
        try:
            current_map = get_current_map(self.map)
            send_kafka_message(self.kafka_producer, 'map_updates', {
                'map': current_map,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error sending map update: {str(e)}")

    def process_client_request(self, request):
        try:
            if request['type'] == 'SERVICE_REQUEST':
                return self.handle_service_request(request)
            elif request['type'] == 'MAP_REQUEST':
                return {'type': 'MAP_UPDATE', 'map': get_current_map(self.map)}
            else:
                return {'type': 'ERROR', 'message': 'Unknown request type'}
        except Exception as e:
            logger.error(f"Error processing client request: {str(e)}")
            return {'type': 'ERROR', 'message': str(e)}

    def handle_service_request(self, request):
        try:
            customer_id = request['customer_id']
            destination = request['destination']
            
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO services (customer_id, end_location, status) VALUES (%s, %s, 'REQUESTED')",
                           (customer_id, destination))
            service_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.process_service_request((service_id, customer_id, None, destination))

            return {'type': 'SERVICE_RESPONSE', 'service_id': service_id, 'status': 'REQUESTED'}
        except Exception as e:
            logger.error(f"Error handling service request: {str(e)}")
            return {'type': 'ERROR', 'message': str(e)}

    @staticmethod
    def calculate_distance(pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def close(self):
        self.kafka_consumer.close()
        self.kafka_producer.flush()

if __name__ == "__main__":
    db_config = {
        'host': 'localhost',
        'user': 'nickhernd',
        'password': 'JAHEDE11',
        'database': 'easycab'
    }
    kafka_config = {
        'bootstrap.servers': 'localhost:9092'
    }
    central = ECCentral('localhost', 8000, db_config, kafka_config)
    try:
        central.start()
    except KeyboardInterrupt:
        logger.info("Shutting down ECCentral...")
    finally:
        central.close()
