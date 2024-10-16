import json
import socket
import threading
import logging
import time
import heapq
from confluent_kafka import Producer, Consumer
from kafka_utils import send_kafka_message, receive_kafka_message, create_kafka_producer, create_kafka_consumer
from socket_protocol import create_message, parse_message
from map_utils import calculate_distance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECDE:
    def __init__(self, central_host, central_port, kafka_config, taxi_id, sensor_port):
        self.central_host = central_host
        self.central_port = central_port
        self.kafka_producer = create_kafka_producer(kafka_config['bootstrap.servers'])
        self.kafka_consumer = create_kafka_consumer(kafka_config['bootstrap.servers'], 'taxi_commands', f'taxi-{taxi_id}')
        self.taxi_id = taxi_id
        self.position = [1, 1]
        self.status = 'AVAILABLE'
        self.destination = None
        self.map_size = 20
        self.path = []
        self.sensor_port = sensor_port
        self.sensor_status = 'OK'

    def handle_command(self, command):
        if command['type'] == 'STOP':
            self.stop()
        elif command['type'] == 'RESUME':
            self.resume()
        elif command['type'] == 'GOTO':
            self.move_to(command['destination'])
        elif command['type'] == 'RETURN_TO_BASE':
            self.return_to_base()

    def stop(self):
        self.status = 'STOPPED'
        print(f"Taxi {self.taxi_id} se ha detenido")

    def resume(self):
        self.status = 'AVAILABLE'
        print(f"Taxi {self.taxi_id} ha reanudado el servicio")

    def return_to_base(self):
        self.move_to([1, 1])

    def kafka_listener(self):
        while True:
            msg = self.kafka_consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            
            command = json.loads(msg.value().decode('utf-8'))
            if command['taxi_id'] == self.taxi_id:
                self.handle_command(command)

    def authenticate(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.central_host, self.central_port))
                message = create_message({
                    'type': 'TAXI_AUTH',
                    'taxi_id': self.taxi_id
                })
                s.sendall(message)
                data = s.recv(1024)
                response = parse_message(data)
                if response['type'] == 'AUTH_SUCCESS':
                    logger.info(f"Taxi {self.taxi_id} authenticated successfully")
                    return True
                else:
                    logger.error(f"Authentication failed for Taxi {self.taxi_id}")
                    return False
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
        
    def find_path(self, start, end):
        def heuristic(a, b):
            return calculate_distance(a, b, self.map_size)

        def get_neighbors(pos):
            x, y = pos
            neighbors = [
                ((x+1) % self.map_size, y),
                ((x-1) % self.map_size, y),
                (x, (y+1) % self.map_size),
                (x, (y-1) % self.map_size),
                ((x+1) % self.map_size, (y+1) % self.map_size),
                ((x-1) % self.map_size, (y-1) % self.map_size),
                ((x+1) % self.map_size, (y-1) % self.map_size),
                ((x-1) % self.map_size, (y+1) % self.map_size)
            ]
            return neighbors

        heap = [(0, start)]
        came_from = {}
        cost_so_far = {start: 0}

        while heap:
            current = heapq.heappop(heap)[1]

            if current == end:
                break

            for next in get_neighbors(current):
                new_cost = cost_so_far[current] + 1
                if next not in cost_so_far or new_cost < cost_so_far[next]:
                    cost_so_far[next] = new_cost
                    priority = new_cost + heuristic(end, next)
                    heapq.heappush(heap, (priority, next))
                    came_from[next] = current

        path = []
        current = end
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path

    def move_to(self, destination):
        self.destination = destination
        self.path = self.find_path(tuple(self.position), tuple(destination))
        self.status = 'BUSY'
        self.move_along_path()
        
        print(f"Taxi {self.taxi_id} se está moviendo hacia {destination}")
        
        for position in self.path:
            self.position = list(position)
            self.send_position_update()
            print(f"Taxi {self.taxi_id} ahora está en la posición {self.position}")
            time.sleep(1)  # Simula el movimiento del taxi

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

    def move_along_path(self):
        while self.path and self.sensor_status == 'OK':
            next_pos = self.path.pop(0)
            self.position = list(next_pos)
            self.send_position_update()
            time.sleep(1)  # Move every second
        if self.sensor_status != 'OK':
            logger.info(f"Stopped due to sensor status: {self.sensor_status}")
        elif not self.path:
            logger.info(f"Arrived at destination {self.destination}")
            self.destination = None
            self.status = 'AVAILABLE'
            self.send_position_update()

    def handle_sensor_input(self, sensor_data):
        if sensor_data == 's':
            logger.info("Red light detected. Stopping.")
            self.sensor_status = 'STOPPED'
        elif sensor_data == 'p':
            logger.info("Pedestrian detected. Stopping.")
            self.sensor_status = 'STOPPED'
        elif sensor_data == 'x':
            logger.info("Flat tire detected. Stopping.")
            self.sensor_status = 'OUT_OF_SERVICE'
        elif sensor_data == 'o':
            logger.info("Sensor status OK. Resuming if necessary.")
            self.sensor_status = 'OK'
            if self.path:
                self.move_along_path()
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
                if command['type'] == 'PICKUP':
                    self.move_to(command['location'])
                    self.move_to(command['destination'])
                elif command['type'] == 'STOP':
                    self.status = 'STOPPED'
                    logger.info("Stopped by command")
                elif command['type'] == 'RESUME':
                    self.status = 'AVAILABLE'
                    logger.info("Resumed by command")
                    if self.path:
                        self.move_along_path()
                elif command['type'] == 'MOVE':
                    self.move_to(command['destination'])
                self.send_position_update()
        except Exception as e:
            logger.error(f"Error in command listener: {str(e)}")

    def listen_for_sensors(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', self.sensor_port))
                s.listen()
                logger.info(f"Listening for sensor inputs on port {self.sensor_port}")
                while True:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024)
                        self.handle_sensor_input(data.decode())
                        conn.sendall("Received".encode('utf-8'))
        except Exception as e:
            logger.error(f"Error in sensor listener: {str(e)}")

    def start(self):
        if not self.authenticate():
            return
        command_thread = threading.Thread(target=self.listen_for_commands)
        sensor_thread = threading.Thread(target=self.listen_for_sensors)
        command_thread.start()
        sensor_thread.start()
        logger.info(f"ECDE started for taxi {self.taxi_id}")

    def close(self):
        self.kafka_consumer.close()
        self.kafka_producer.flush()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 6:
        print("Usage: python EC_DE.py <central_host> <central_port> <kafka_bootstrap_servers> <taxi_id> <sensor_port>")
        sys.exit(1)

    central_host = sys.argv[1]
    central_port = int(sys.argv[2])
    kafka_bootstrap_servers = sys.argv[3]
    taxi_id = sys.argv[4]
    sensor_port = int(sys.argv[5])

    kafka_config = {
        'bootstrap.servers': kafka_bootstrap_servers
    }
    de = ECDE(central_host, central_port, kafka_config, taxi_id, sensor_port)
    try:
        de.start()
    except KeyboardInterrupt:
        logger.info("Shutting down ECDE...")
    finally:
        de.close()