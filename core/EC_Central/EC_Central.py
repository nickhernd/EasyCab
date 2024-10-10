import socket
import threading
import mysql.connector
from kafka import KafkaProducer, KafkaConsumer
from common.kafka_utils import send_kafka_message, receive_kafka_message
from common.map_utils import update_map, get_current_map
from common.socket_protocol import create_message, parse_message

class ECCentral:
    def __init__(self, host, port, db_config, kafka_config):
        self.host = host
        self.port = port
        self.db_config = db_config
        self.kafka_producer = KafkaProducer(**kafka_config)
        self.kafka_consumer = KafkaConsumer('taxi_updates', **kafka_config)
        self.map = [[' ' for _ in range(20)] for _ in range(20)]
        self.lock = threading.Lock()
        self.taxis = {}  # Dictionary to store taxi information

    def start(self):
        db_thread = threading.Thread(target=self.db_listener)
        kafka_thread = threading.Thread(target=self.kafka_listener)
        socket_thread = threading.Thread(target=self.socket_listener)

        db_thread.start()
        kafka_thread.start()
        socket_thread.start()

    def db_listener(self):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()

        while True:
            cursor.execute("SELECT * FROM services WHERE status = 'REQUESTED'")
            for service in cursor.fetchall():
                self.process_service_request(service)

            conn.commit()

    def kafka_listener(self):
        for message in self.kafka_consumer:
            self.process_taxi_update(receive_kafka_message(message))

    def socket_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                client_thread.start()

    def handle_client(self, conn, addr):
        with conn:
            data = conn.recv(1024)
            message = parse_message(data)
            response = self.process_client_request(message)
            conn.sendall(create_message(response))

    def process_service_request(self, service):
        service_id, customer_id, start_location, end_location = service
        available_taxi = self.find_available_taxi(start_location)
        if available_taxi:
            self.assign_taxi_to_service(available_taxi, service_id, start_location, end_location)
        else:
            self.queue_service_request(service_id)

    def find_available_taxi(self, location):
        # Find the nearest available taxi
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
        # Update database
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        cursor.execute("UPDATE services SET status = 'IN_PROGRESS', taxi_id = %s WHERE id = %s", 
                       (taxi_id, service_id))
        conn.commit()
        conn.close()

        # Send command to taxi
        send_kafka_message(self.kafka_producer, 'taxi_commands', {
            'taxi_id': taxi_id,
            'type': 'PICKUP',
            'location': start_location,
            'destination': end_location
        })

        # Update taxi status
        self.taxis[taxi_id]['status'] = 'BUSY'

    def queue_service_request(self, service_id):
        # Implement logic to queue the service request for later processing
        pass

    def process_taxi_update(self, update):
        taxi_id = update['taxi_id']
        position = update['position']
        status = update['status']

        with self.lock:
            self.taxis[taxi_id] = {'position': position, 'status': status}
            self.map = update_map(self.map, update)

        self.send_map_update()

    def send_map_update(self):
        current_map = get_current_map(self.map)
        send_kafka_message(self.kafka_producer, 'map_updates', {
            'map': current_map,
            'timestamp': time.time()
        })

    def process_client_request(self, request):
        if request['type'] == 'SERVICE_REQUEST':
            return self.handle_service_request(request)
        elif request['type'] == 'MAP_REQUEST':
            return {'type': 'MAP_UPDATE', 'map': get_current_map(self.map)}
        else:
            return {'type': 'ERROR', 'message': 'Unknown request type'}

    def handle_service_request(self, request):
        customer_id = request['customer_id']
        destination = request['destination']
        
        # Insert new service request into database
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO services (customer_id, end_location, status) VALUES (%s, %s, 'REQUESTED')",
                       (customer_id, destination))
        service_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Try to process the service request immediately
        self.process_service_request((service_id, customer_id, None, destination))

        return {'type': 'SERVICE_RESPONSE', 'service_id': service_id, 'status': 'REQUESTED'}

    @staticmethod
    def calculate_distance(pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

if __name__ == "__main__":
    db_config = {
        'host': 'localhost',
        'user': 'your_username',
        'password': 'your_password',
        'database': 'easycab'
    }
    kafka_config = {
        'bootstrap_servers': ['localhost:9092']
    }
    central = ECCentral('localhost', 8000, db_config, kafka_config)
    central.start()