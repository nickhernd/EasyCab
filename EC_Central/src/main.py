# EC_Central/src/main.py

import socket
import sys
import threading
import json
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from kafka import KafkaProducer, KafkaConsumer
import numpy as np

@dataclass
class Taxi:
    id: int
    position: Tuple[int, int]
    state: str 
    destination: Tuple[int, int] = None
    token: str = None

@dataclass
class Location:
    id: str
    position: Tuple[int, int]
    type: str = "LOCATION"

@dataclass
class MapCell:
    content: Optional[Location] = None
    color: str = "WHITE"

class MapManager:
    def __init__(self, size: int = 20):
        self.size = size
        self.map = [[MapCell() for _ in range(size)] for _ in range(size)]
        self.locations: Dict[str, Location] = {}
        self.taxis: Dict[int, Location] = {}
        self.lients: Dict[str, Location] = {}
        self.logger = logging.getLogger('EC_Central.MapManager')

    def normalize_position(self, x: int, y: int) -> Tuple[int, int]:
        """Normaliza las coordenadas para el mapa esférico"""
        return (x % self.size, y % self.size)

    def load_locations(self, filename: str):
        """Carga las ubicaciones desde el archivo de configuración"""
        try:
            with open(filename, 'r') as f:
                for line in f:
                    loc_id, x, y = line.strip().split()
                    x, y = int(x), int(y)
                    x, y = self.normalize_position(x-1, y-1)
                    location = Location(loc_id, (x, y), "LOCATION")
                    self.locations[loc_id] = location
                    self.map[x][y] = MapCell(location, "BLUE")
                self.logger.info(f"Loaded {len(self.locations)} locations")
        except Exception as e:
            self.logger.error(f"Error loading locations: {e}")
            raise

    def is_position_free(self, x: int, y: int) -> bool:
        """Verifica si una posición está libre"""
        return self.map[x][y].content is None

    def add_taxi(self, taxi_id: int, position: Tuple[int, int], state: str = "RED"):
        """Añade o actualiza la posición de un taxi"""
        x, y = self.normalize_position(position[0]-1, position[1]-1)
        
        # Si el taxi ya existe, limpia su posición anterior
        if taxi_id in self.taxis:
            old_pos = self.taxis[taxi_id].position
            self.map[old_pos[0]][old_pos[1]] = MapCell()

        # Verifica colisiones
        if not self.is_position_free(x, y):
            self.logger.warning(f"Position ({x+1},{y+1}) is occupied")
            return False

        # Añade el taxi a la nueva posición
        taxi_location = Location(str(taxi_id), (x, y), "TAXI")
        self.taxis[taxi_id] = taxi_location
        self.map[x][y] = MapCell(taxi_location, "GREEN" if state == "MOVING" else "RED")
        return True

    def add_client(self, client_id: str, position: Tuple[int, int]):
        """Añade o actualiza la posición de un cliente"""
        x, y = self.normalize_position(position[0]-1, position[1]-1)
        
        if client_id in self.clients:
            old_pos = self.clients[client_id].position
            self.map[old_pos[0]][old_pos[1]] = MapCell()

        if not self.is_position_free(x, y):
            self.logger.warning(f"Position ({x+1},{y+1}) is occupied")
            return False

        client_location = Location(client_id, (x, y), "CLIENT")
        self.clients[client_id] = client_location
        self.map[x][y] = MapCell(client_location, "YELLOW")
        return True

    def get_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Calcula la ruta más corta entre dos puntos considerando el mapa esférico"""
        start_x, start_y = self.normalize_position(start[0]-1, start[1]-1)
        end_x, end_y = self.normalize_position(end[0]-1, end[1]-1)
        path = []
        current = (start_x, start_y)

        while current != (end_x, end_y):
            next_x, next_y = current
            
            # Calcula las diferencias considerando el mapa esférico
            dx = (end_x - current[0] + self.size//2) % self.size - self.size//2
            dy = (end_y - current[1] + self.size//2) % self.size - self.size//2

            if dx != 0:
                next_x = (current[0] + (1 if dx > 0 else -1)) % self.size
            if dy != 0:
                next_y = (current[1] + (1 if dy > 0 else -1)) % self.size

            current = (next_x, next_y)
            path.append((current[0]+1, current[1]+1))  # Convertir a coordenadas 1-based

        return path

    def to_dict(self) -> dict:
        """Convierte el mapa a un diccionario para serialización"""
        return {
            'size': self.size,
            'locations': {k: {'position': (v.position[0]+1, v.position[1]+1)} 
                         for k, v in self.locations.items()},
            'taxis': {k: {'position': (v.position[0]+1, v.position[1]+1)} 
                     for k, v in self.taxis.items()},
            'clients': {k: {'position': (v.position[0]+1, v.position[1]+1)} 
                       for k, v in self.clients.items()},
            'map': [[{
                'type': cell.content.type if cell.content else None,
                'id': cell.content.id if cell.content else None,
                'color': cell.color
            } for cell in row] for row in self.map]
        }

    def get_ascii_map(self) -> str:
        """Genera una representación ASCII del mapa para debugging"""
        result = []
        for row in self.map:
            row_str = []
            for cell in row:
                if cell.content is None:
                    row_str.append('.')
                elif cell.content.type == "LOCATION":
                    row_str.append(cell.content.id)
                elif cell.content.type == "TAXI":
                    row_str.append(f"T{cell.content.id}")
                elif cell.content.type == "CLIENT":
                    row_str.append(f"C{cell.content.id}")
            result.append(' '.join(row_str))
        return '\n'.join(result)

class ECCentral:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, kafka_server: str = 'localhost:9092'):
        self.host = host
        self.port = port
        self.map_manager = MapManager()
        
        # Configuración de Kafka
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_server],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # Inicializar socket servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def start(self):
        """Iniciar el servidor"""
        logging.info(f"EC_Central iniciado en {self.host}:{self.port}")
        
        # Cargar ubicaciones del archivo de configuración
        self.map_manager.load_locations('config/locations.txt')
        
        # Iniciar thread para escuchar mensajes Kafka
        kafka_thread = threading.Thread(target=self.listen_kafka_messages)
        kafka_thread.daemon = True
        kafka_thread.start()
        
        # Aceptar conexiones de clientes
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logging.error(f"Error accepting connection: {e}")

    def handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Manejar conexiones de clientes"""
        logging.info(f"Nueva conexión desde {address}")
        
        try:
            while True:
                # Recibir mensaje del cliente
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.send(json.dumps(response).encode('utf-8'))
                
                # Actualizar mapa para todos los clientes
                self.broadcast_map_state()
                
        except Exception as e:
            logging.error(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            logging.info(f"Conexión cerrada con {address}")

    def process_message(self, message: Dict) -> Dict:
        """Procesar mensajes recibidos"""
        msg_type = message.get('type')
        
        if msg_type == 'AUTH':
            return self.handle_auth(message)
        elif msg_type == 'POSITION':
            return self.handle_position_update(message)
        elif msg_type == 'SERVICE_REQUEST':
            return self.handle_service_request(message)
        else:
            return {'status': 'ERROR', 'message': 'Unknown message type'}

    def handle_auth(self, message: Dict) -> Dict:
        """Manejar autenticación de taxis"""
        taxi_id = message.get('taxi_id')
        if taxi_id not in self.map_manager.taxis:
            # Crear nuevo taxi en posición inicial (1,1)
            self.map_manager.taxis[taxi_id] = Taxi(
                id=taxi_id,
                position=(1, 1),
                state='RED'
            )
            # Generar token (en una implementación real, usar JWT)
            token = f"token_{taxi_id}"
            self.map_manager.taxis[taxi_id].token = token
            
            return {'status': 'OK', 'token': token}
        return {'status': 'ERROR', 'message': 'Taxi already registered'}

    def handle_position_update(self, message: Dict) -> Dict:
        """Manejar actualizaciones de posición de taxis"""
        taxi_id = message.get('taxi_id')
        token = message.get('token')
        position = message.get('position')
        state = message.get('state')
        
        # Verificar token
        if not self.verify_token(taxi_id, token):
            return {'status': 'ERROR', 'message': 'Invalid token'}
            
        if self.map_manager.update_taxi_position(taxi_id, position, state):
            return {'status': 'OK', 'map': self.map_manager.get_map_state()}
        return {'status': 'ERROR', 'message': 'Could not update position'}

    def handle_service_request(self, message: Dict) -> Dict:
        """Manejar solicitudes de servicio"""
        destination = message.get('destination')
        if destination in self.map_manager.locations:
            # Encontrar taxi disponible más cercano
            available_taxi = self.find_available_taxi(self.map_manager.locations[destination])
            if available_taxi:
                # Asignar servicio al taxi
                return {'status': 'OK', 'taxi_id': available_taxi.id}
        return {'status': 'ERROR', 'message': 'No taxis available'}

    def verify_token(self, taxi_id: int, token: str) -> bool:
        """Verificar token de taxi"""
        if taxi_id in self.map_manager.taxis:
            return self.map_manager.taxis[taxi_id].token == token
        return False

    def find_available_taxi(self, destination: Tuple[int, int]) -> Taxi:
        """Encontrar taxi disponible más cercano"""
        available_taxis = [taxi for taxi in self.map_manager.taxis.values() 
                         if taxi.state == 'RED']
        if available_taxis:
            # En una implementación real, calcular distancias y seleccionar el más cercano
            return available_taxis[0]
        return None

    def broadcast_map_state(self):
        """Transmitir estado del mapa a través de Kafka"""
        try:
            self.producer.send('map_updates', self.map_manager.get_map_state())
        except Exception as e:
            logging.error(f"Error broadcasting map state: {e}")

    def listen_kafka_messages(self):
        """Escuchar mensajes de Kafka"""
        consumer = KafkaConsumer(
            'taxi_events',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        for message in consumer:
            try:
                self.process_kafka_message(message.value)
            except Exception as e:
                logging.error(f"Error processing Kafka message: {e}")

    def process_kafka_message(self, message: Dict):
        """Procesar mensajes de Kafka"""
        # Implementar lógica para procesar mensajes de Kafka
        pass

if __name__ == "__main__":
    # Verificar número correcto de argumentos
    if len(sys.argv) != 3:
        print("Uso: python main.py <puerto_escucha> <ip:puerto_kafka>")
        print("Ejemplo: python main.py 5000 localhost:9092")
        sys.exit(1)

    try:
        # Obtener argumentos posicionales
        port = int(sys.argv[1])
        kafka_server = sys.argv[2]

        # Iniciar el servidor
        server = ECCentral(port=port, kafka_server=kafka_server)
        server.start()
    except ValueError:
        print("Error: El puerto debe ser un número entero"
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")
        sys.exit(1)
