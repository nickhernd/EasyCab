import socket
import os
import sys
import threading
from flask import app, jsonify, Flask
import mysql.connector
import time
import logging
import json
import cmd
from confluent_kafka import Producer, Consumer
from kafka_utils import send_kafka_message, receive_kafka_message, create_kafka_producer, create_kafka_consumer
from map_utils import update_map, get_current_map, create_empty_map, calculate_distance
from socket_protocol import create_message, parse_message
from confluent_kafka.admin import AdminClient, NewTopic

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/status')
def status():
    return jsonify({"status": "OK", "message": "EC_Central is running"})

class CentralCommandLine(cmd.Cmd):
    def __init__(self, central):
        super().__init__()
        self.central = central
        self.prompt = 'CENTRAL> '

    def do_stop(self, arg):
        """Parar un taxi: stop <taxi_id>"""
        taxi_id = arg.strip()
        self.central.stop_taxi(taxi_id)

    def do_resume(self, arg):
        """Reanudar un taxi: resume <taxi_id>"""
        taxi_id = arg.strip()
        self.central.resume_taxi(taxi_id)

    def do_goto(self, arg):
        """Enviar un taxi a un destino: goto <taxi_id> <destino>"""
        args = arg.split()
        if len(args) != 2:
            print("Uso: goto <taxi_id> <destino>")
            return
        taxi_id, destination = args
        self.central.send_taxi_to_destination(taxi_id, destination)

    def do_return(self, arg):
        """Hacer que un taxi vuelva a la base: return <taxi_id>"""
        taxi_id = arg.strip()
        self.central.return_taxi_to_base(taxi_id)

    def do_quit(self, arg):
        """Salir del programa"""
        print("Saliendo...")
        return True

class ECCentral:
    def __init__(self, host, port, db_config, kafka_config):
        self.host = host
        self.port = port
        self.db_config = db_config
        self.kafka_producer = create_kafka_producer(kafka_config['bootstrap.servers'])
        self.kafka_consumer = create_kafka_consumer(kafka_config['bootstrap.servers'], ['taxi_updates', 'customer_updates'])
        self.map = create_empty_map(20)
        self.lock = threading.Lock()
        self.taxis = {}
        self.clients = {}
        self.service_queue = []
        self.load_map_config()
        self.city_map = self.load_city_map()
        self.create_kafka_topics()

    def stop_taxi(self, taxi_id):
        command = {
            'type': 'STOP',
            'taxi_id': taxi_id
        }
        self.send_command_to_taxi(command)
        print(f"Orden de parada enviada al taxi {taxi_id}")

    def resume_taxi(self, taxi_id):
        command = {
            'type': 'RESUME',
            'taxi_id': taxi_id
        }
        self.send_command_to_taxi(command)
        print(f"Orden de reanudación enviada al taxi {taxi_id}")

    def send_taxi_to_destination(self, taxi_id, destination):
        command = {
            'type': 'GOTO',
            'taxi_id': taxi_id,
            'destination': destination
        }
        self.send_command_to_taxi(command)
        print(f"Orden de ir al destino {destination} enviada al taxi {taxi_id}")

    def return_taxi_to_base(self, taxi_id):
        command = {
            'type': 'RETURN_TO_BASE',
            'taxi_id': taxi_id,
            'destination': [1, 1]
        }
        self.send_command_to_taxi(command)
        print(f"Orden de volver a la base enviada al taxi {taxi_id}")

    def send_command_to_taxi(self, command):
        # Enviar el comando a través de Kafka
        send_kafka_message(self.kafka_producer, 'taxi_commands', command)

    def run_command_line(self):
        CentralCommandLine(self).cmdloop()

    def load_city_map(self):
        with open('city_map.txt', 'r') as f:
            for line in f:
                loc_id, x, y = line.strip().split()
                self.db_cursor.execute("INSERT INTO locations (id, position_x, position_y) VALUES (?, ?, ?)", (loc_id, int(x), int(y)))
        self.db_connection.commit()

    def load_taxis(self):
        with open('taxis.txt', 'r') as f:
            for line in f:
                taxi_id = line.strip()
                self.db_cursor.execute("INSERT INTO taxis (id, status, position_x, position_y) VALUES (?, 'AVAILABLE', 1, 1)", (taxi_id,))
        self.db_connection.commit()
    
    def create_kafka_topics(self):
        admin_client = AdminClient({'bootstrap.servers': self.kafka_config['bootstrap.servers']})
        topics = ['taxi_updates', 'customer_updates', 'map_updates']
        new_topics = [NewTopic(topic, num_partitions=1, replication_factor=1) for topic in topics]
        fs = admin_client.create_topics(new_topics)
        for topic, f in fs.items():
            try:
                f.result() 
                logger.info(f"Topic {topic} created")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"Topic {topic} already exists")
                else:
                    logger.error(f"Failed to create topic {topic}: {e}")
    
    def process_service_request(self, service):
        try:
            service_id, customer_id, start_location, end_location = service[:4]
            
            start_coords = self.city_map.get(start_location, (1, 1))  
            end_coords = self.city_map.get(end_location, (1, 1))  

            available_taxi = self.find_available_taxi(start_coords)
            if available_taxi:
                self.assign_taxi_to_service(available_taxi, service_id, start_coords, end_coords)
                return {'type': 'SERVICE_RESPONSE', 'service_id': service_id, 'status': 'IN_PROGRESS', 'taxi_id': available_taxi}
            else:
                self.queue_service_request(service_id)
                return {'type': 'SERVICE_RESPONSE', 'service_id': service_id, 'status': 'QUEUED'}
        except Exception as e:
            logger.error(f"Error processing service request: {str(e)}")
            return {'type': 'ERROR', 'message': str(e)}

    def load_map_config(self):
        try:
            with open('city_map.txt', 'r') as f:
                for line in f:
                    loc_id, x, y = line.strip().split()
                    x, y = int(x), int(y)
                    if 0 <= x < len(self.map[0]) and 0 <= y < len(self.map):
                        self.map[y][x] = loc_id
                    else:
                        logger.warning(f"Coordinates out of range: {x}, {y}")
            logger.info("Map configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading map configuration: {str(e)}")

    def start(self):
        try:
            db_thread = threading.Thread(target=self.db_listener)
            kafka_thread = threading.Thread(target=self.kafka_listener)
            socket_thread = threading.Thread(target=self.socket_listener)

            db_thread.start()
            kafka_thread.start()
            socket_thread.start()
            
            cmd_thread = threading.Thread(target=self.run_command_line)
            cmd_thread.start()
        except Exception as e:
            logger.error(f"Error starting ECCentral: {str(e)}")

    def db_listener(self):
        while True:
            try:
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM services WHERE status = 'REQUESTED'")
                for service in cursor.fetchall():
                    self.process_service_request(service)

                conn.commit()
                time.sleep(1)
            except mysql.connector.Error as err:
                logger.error(f"Database error: {err}")
                time.sleep(5)  # Espera antes de intentar reconectar
            except Exception as e:
                logger.error(f"Error in db_listener: {str(e)}")
                time.sleep(5)  # Espera antes de intentar reconectar

    def kafka_listener(self):
        try:
            while True:
                msg = self.kafka_consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                data = receive_kafka_message(msg)
                if msg.topic() == 'taxi_updates':
                    self.process_taxi_update(data)
                elif msg.topic() == 'customer_updates':
                    self.process_customer_update(data)
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
            service_id, customer_id, start_location, end_location = service[:4]
        
            available_taxi = self.find_available_taxi(start_location)
            if available_taxi:
                self.assign_taxi_to_service(available_taxi, service_id, start_location, end_location)
                return {'type': 'SERVICE_RESPONSE', 'service_id': service_id, 'status': 'IN_PROGRESS', 'taxi_id': available_taxi}
            else:
                self.queue_service_request(service_id)
                return {'type': 'SERVICE_RESPONSE', 'service_id': service_id, 'status': 'QUEUED'}
        except Exception as e:
            logger.error(f"Error processing service request: {str(e)}")
            return {'type': 'ERROR', 'message': str(e)}

    def find_available_taxi(self, location):
        nearest_taxi = None
        min_distance = float('inf')
        for taxi_id, taxi_info in self.taxis.items():
            if taxi_info['status'] == 'AVAILABLE':
                distance = calculate_distance(taxi_info['position'], location, 20)  # 20 is map size
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
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("UPDATE services SET status = %s WHERE id = %s", ('QUEUED', service_id))
            conn.commit()
            conn.close()
    
            self.service_queue.append(service_id)
    
            threading.Timer(60.0, self.check_service_queue).start()
        except Exception as e:
            logger.error(f"Error queueing service request: {str(e)}")

    def check_service_queue(self):
        if self.service_queue:
            service_id = self.service_queue.pop(0)
            self.process_service_request((service_id,))

    def process_taxi_update(self, update):
        try:
            taxi_id = update['taxi_id']
            position = update['position']
            status = update['status']

            with self.lock:
                self.taxis[taxi_id] = {'position': position, 'status': status}
                self.map = update_map(self.map, update)
            
            print(f"Taxi {update['taxi_id']} se ha movido a la posición {update['position']} con estado {update['status']}")

            self.send_map_update()
        except Exception as e:
            logger.error(f"Error processing taxi update: {str(e)}")

    def process_customer_update(self, update):
        try:
            customer_id = update['customer_id']
            location = update['location']

            with self.lock:
                self.clients[customer_id] = {'location': location}
                self.map = update_map(self.map, {'customer_id': customer_id, 'position': location})

            print(f"Cliente {update['customer_id']} ha solicitado un servicio a {update['destination']}")

            self.send_map_update()
        except Exception as e:
            logger.error(f"Error processing customer update: {str(e)}")

    def send_map_update(self):
        try:
            current_map = get_current_map(self.map)
            message = {
                'map': current_map,
                'timestamp': time.time()
            }
            send_kafka_message(self.kafka_producer, 'map_updates', message)
            logger.info(f"Sent map update: {message}")
        except Exception as e:
            logger.error(f"Error sending map update: {str(e)}")

    def process_client_request(self, request):
        try:
            if request['type'] == 'SERVICE_REQUEST':
                return self.handle_service_request(request)
            elif request['type'] == 'MAP_REQUEST':
                return {'type': 'MAP_UPDATE', 'map': get_current_map(self.map)}
            elif request['type'] == 'TAXI_COMMAND':
                return self.handle_taxi_command(request)
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
                           (customer_id, json.dumps(destination)))
            service_id = cursor.lastrowid
            conn.commit()
            conn.close()

            response = self.process_service_request((service_id, customer_id, self.clients[customer_id]['location'], destination))
            return response
        except Exception as e:
            logger.error(f"Error handling service request: {str(e)}")
            return {'type': 'ERROR', 'message': str(e)}

    def handle_taxi_command(self, request):
        try:
            taxi_id = request['taxi_id']
            command = request['command']
            
            if command == 'STOP':
                self.taxis[taxi_id]['status'] = 'STOPPED'
                send_kafka_message(self.kafka_producer, 'taxi_commands', {
                    'taxi_id': taxi_id,
                    'type': 'STOP'
                })
            elif command == 'RESUME':
                self.taxis[taxi_id]['status'] = 'AVAILABLE'
                send_kafka_message(self.kafka_producer, 'taxi_commands', {
                    'taxi_id': taxi_id,
                    'type': 'RESUME'
                })
            elif command == 'GO_TO':
                destination = request['destination']
                send_kafka_message(self.kafka_producer, 'taxi_commands', {
                    'taxi_id': taxi_id,
                    'type': 'MOVE',
                    'destination': destination
                })
            elif command == 'RETURN_TO_BASE':
                send_kafka_message(self.kafka_producer, 'taxi_commands', {
                    'taxi_id': taxi_id,
                    'type': 'MOVE',
                    'destination': [1, 1]
                })
            
            return {'type': 'COMMAND_RESPONSE', 'status': 'SUCCESS'}
        except Exception as e:
            logger.error(f"Error handling taxi command: {str(e)}")
            return {'type': 'ERROR', 'message': str(e)}

    def close(self):
        self.kafka_consumer.close()
        self.kafka_producer.flush()

    def check_database_connection(self):
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            logger.info(f"Connected to database. Tables: {tables}")
            conn.close()
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
        
    def ensure_topics_exist(bootstrap_servers, topics, max_retries=5, retry_interval=5):
        admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})

        for _ in range(max_retries):
            try:
                existing_topics = admin_client.list_topics(timeout=5).topics
                missing_topics = [topic for topic in topics if topic not in existing_topics]

                if not missing_topics:
                    print("All required topics exist.")
                    return True

                print(f"Missing topics: {missing_topics}. Attempting to create...")
                new_topics = [NewTopic(topic, num_partitions=1, replication_factor=1) for topic in missing_topics]
                admin_client.create_topics(new_topics)
                print("Topics created successfully.")
                return True
            except Exception as e:
                print(f"Error ensuring topics exist: {e}")
                time.sleep(retry_interval)

        print("Failed to ensure topics exist after maximum retries.")
        return False


if __name__ == "__main__":
    kafka_bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    
    if not ECCentral.ensure_topics_exist(kafka_bootstrap_servers, ['taxi_updates', 'customer_updates', 'map_updates']):
        print("Failed to ensure Kafka topics exist. Exiting.")
        sys.exit(1)

    db_config = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', 'JAHEDE11'),
        'database': os.environ.get('MYSQL_DATABASE', 'easycab')
    }
    kafka_config = {
        'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    }
    central = ECCentral('0.0.0.0', 8000, db_config, kafka_config)
    
    # Inicia ECCentral en un hilo separado
    central_thread = threading.Thread(target=central.start)
    central_thread.start()
    
    # Inicia Flask
    app.run(host='0.0.0.0', port=8000)
    
    try:
        central_thread.join()
    except KeyboardInterrupt:
        print("Shutting down ECCentral...")
    finally:
        central.close()