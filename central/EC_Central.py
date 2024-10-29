import os
import socket
import json
import threading
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import mysql.connector
from mysql.connector import Error

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Estados
TAXI_STATES = {
    'AVAILABLE': 'AVAILABLE',
    'BUSY': 'BUSY',
    'STOPPED': 'STOPPED',
    'OFFLINE': 'OFFLINE'
}

SERVICE_STATES = {
    'PENDING': 'PENDING',
    'ACCEPTED': 'ACCEPTED',
    'IN_PROGRESS': 'IN_PROGRESS',
    'COMPLETED': 'COMPLETED',
    'REJECTED': 'REJECTED'
}

@dataclass
class Location:
    id: str
    x: int
    y: int

@dataclass
class Taxi:
    id: int
    state: str
    position: Tuple[int, int]
    destination: Optional[Tuple[int, int]] = None
    current_service: Optional[str] = None
    client_socket: Optional[socket.socket] = None

class MapManager:
    def __init__(self, size: int = 20):
        self.size = size
        self.grid = [[None for _ in range(size)] for _ in range(size)]
        self.locations: Dict[str, Location] = {}
        self.taxis: Dict[int, Tuple[int, int]] = {}

    def add_location(self, loc_id: str, x: int, y: int) -> bool:
        if not (0 <= x < self.size and 0 <= y < self.size):
            return False
        location = Location(loc_id, x, y)
        self.locations[loc_id] = location
        self.grid[y][x] = ('location', loc_id)
        return True

    def add_taxi(self, taxi_id: int, x: int, y: int, state: str) -> bool:
        if not (0 <= x < self.size and 0 <= y < self.size):
            return False
        if taxi_id in self.taxis:
            old_x, old_y = self.taxis[taxi_id]
            self.grid[old_y][old_x] = None
        self.taxis[taxi_id] = (x, y)
        self.grid[y][x] = ('taxi', taxi_id, state)
        return True

    def remove_taxi(self, taxi_id: int) -> None:
        if taxi_id in self.taxis:
            x, y = self.taxis[taxi_id]
            self.grid[y][x] = None
            del self.taxis[taxi_id]

    def get_state(self) -> List[List]:
        return [row[:] for row in self.grid]

class DatabaseHandler:
    def __init__(self, db_host: str, db_port: int, db_user: str, db_password: str, db_name: str):
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            logger.info("Conexión a MySQL establecida correctamente")
        except Error as e:
            logger.error(f"Error conectando a MySQL: {e}")
            raise

    def disconnect(self):
        if self.connection:
            self.connection.close()

class CentralServer:
    def __init__(self, host: str, port: int, kafka_host: str, kafka_port: int, db_host: str, db_port: int, db_user: str, db_password: str, db_name: str):
        self.host = host
        self.port = port
        self.kafka_host = kafka_host
        self.kafka_port = kafka_port
        self.running = True
        self.map_manager = MapManager()
        self.taxis: Dict[int, dict] = {}
        self.services: Dict[str, dict] = {}
        self.db_handler = DatabaseHandler(db_host, db_port, db_user, db_password, db_name)
        self.taxi_lock = threading.Lock()
        self.service_lock = threading.Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.load_locations()
        logger.info(f"Central Server iniciado en {self.host}:{self.port}")

    def load_locations(self):
        try:
            with open('data/EC_locations.json', 'r') as f:
                data = json.load(f)
                for loc in data['locations']:
                    loc_id = loc['Id']
                    x, y = map(int, loc['POS'].split(','))
                    self.map_manager.add_location(loc_id, x, y)
            logger.info("Localizaciones cargadas correctamente")
        except Exception as e:
            logger.error(f"Error cargando localizaciones: {e}")

    def handle_client(self, client_socket: socket.socket, address: str):
        try:
            logger.info(f"Manejando nueva conexión desde {address}")
            while self.running:
                data = client_socket.recv(1024).decode()
                if not data:
                    logger.info(f"Conexión cerrada por {address}")
                    break
                message = json.loads(data)
                client_type = message.get('type')
                if client_type == 'taxi':
                    self.handle_taxi_registration(client_socket, message)
                elif client_type == 'customer':
                    self.handle_customer_registration(client_socket, message)
                elif client_type == 'service_request':
                    self.handle_service_request(message, client_socket)
                else:
                    logger.warning(f"Tipo de cliente desconocido: {client_type}")
        except Exception as e:
            logger.error(f"Error en conexión con {address}: {e}")
        finally:
            client_socket.close()

    def handle_taxi_registration(self, client_socket: socket.socket, message: dict):
        taxi_id = message.get('taxi_id')
        with self.taxi_lock:
            self.taxis[taxi_id] = {
                'socket': client_socket,
                'state': 'AVAILABLE',
                'current_service': None
            }
            self.map_manager.add_taxi(taxi_id, 1, 1, 'AVAILABLE')
        response = {'status': 'OK', 'message': 'Taxi registered'}
        client_socket.send(json.dumps(response).encode())
        logger.info(f"Taxi {taxi_id} registrado correctamente")

    def handle_customer_registration(self, client_socket: socket.socket, message: dict):
        response = {'status': 'OK', 'message': 'Cliente conectado'}
        client_socket.send(json.dumps(response).encode())
        logger.info("Cliente conectado")

    def handle_service_request(self, request: dict, client_socket: socket.socket):
        customer_id = request.get('customer_id')
        destination = request.get('destination')
        taxi_id = self.find_available_taxi()
        if taxi_id:
            service_id = f"SRV_{len(self.services) + 1}"
            with self.service_lock:
                self.services[service_id] = {
                    'id': service_id,
                    'customer_id': customer_id,
                    'taxi_id': taxi_id,
                    'destination': destination,
                    'state': 'ACCEPTED'
                }
                self.assign_service_to_taxi(taxi_id, service_id, destination)
                response = {'status': 'OK', 'service_id': service_id, 'taxi_id': taxi_id}
                logger.info(f"Servicio {service_id} asignado al taxi {taxi_id}")
        else:
            response = {'status': 'ERROR', 'message': 'No hay taxis disponibles'}
        client_socket.send(json.dumps(response).encode())

    def find_available_taxi(self) -> Optional[int]:
        with self.taxi_lock:
            for taxi_id, taxi in self.taxis.items():
                if taxi['state'] == 'AVAILABLE':
                    return taxi_id
        return None

    def assign_service_to_taxi(self, taxi_id: int, service_id: str, destination: str):
        with self.taxi_lock:
            taxi = self.taxis[taxi_id]
            taxi['state'] = 'BUSY'
            taxi['current_service'] = service_id
            dest_loc = self.map_manager.locations.get(destination)
            if dest_loc:
                taxi_destination = (dest_loc.x, dest_loc.y)
            message = {
                'type': 'new_service',
                'service_id': service_id,
                'destination': destination
            }
            taxi['socket'].send(json.dumps(message).encode())

    def broadcast_map_update(self):
        map_state = self.map_manager.get_state()
        update = {'type': 'map_update', 'map': map_state}
        with self.taxi_lock:
            for taxi in self.taxis.values():
                try:
                    taxi['socket'].send(json.dumps(update).encode())
                except:
                    pass

    def run(self):
        logger.info("Iniciando servidor central...")
        try:
            while self.running:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            logger.info("Apagando servidor...")
        finally:
            self.cleanup()

    def cleanup(self):
        self.running = False
        self.db_handler.disconnect()
        self.server_socket.close()
        with self.taxi_lock:
            for taxi in self.taxis.values():
                if taxi['socket']:
                    taxi['socket'].close()

if __name__ == "__main__":
    # Los argumentos deben ser pasados en orden: host, puerto, kafka_host, kafka_port, db_host, db_port, db_user, db_password, db_name
    import sys
    if len(sys.argv) != 10:
        print("Uso: python EC_Central.py <host> <port> <kafka_host> <kafka_port> <db_host> <db_port> <db_user> <db_password> <db_name>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    kafka_host = sys.argv[3]
    kafka_port = int(sys.argv[4])
    db_host = sys.argv[5]
    db_port = int(sys.argv[6])
    db_user = sys.argv[7]
    db_password = sys.argv[8]
    db_name = sys.argv[9]

    server = CentralServer(host, port, kafka_host, kafka_port, db_host, db_port, db_user, db_password, db_name)
    server.run()
