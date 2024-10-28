import sys
import os
import socket
import json
import threading
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.kafka_utils import KafkaClient, TOPICS, create_message

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
        self.lock = threading.Lock()

    def add_location(self, loc_id: str, x: int, y: int) -> bool:
        """Añadir localización al mapa"""
        with self.lock:
            if not (0 <= x < self.size and 0 <= y < self.size):
                return False
            
            location = Location(loc_id, x, y)
            self.locations[loc_id] = location
            self.grid[y][x] = ('location', loc_id)
            return True

    def add_taxi(self, taxi_id: int, x: int, y: int, state: str) -> bool:
        """Añadir o actualizar taxi en el mapa"""
        with self.lock:
            if not (0 <= x < self.size and 0 <= y < self.size):
                return False
                
            # Limpiar posición anterior si existe
            if taxi_id in self.taxis:
                old_x, old_y = self.taxis[taxi_id]
                self.grid[old_y][old_x] = None
                
            self.taxis[taxi_id] = (x, y)
            self.grid[y][x] = ('taxi', taxi_id, state)
            return True

    def remove_taxi(self, taxi_id: int) -> None:
        """Eliminar taxi del mapa"""
        with self.lock:
            if taxi_id in self.taxis:
                x, y = self.taxis[taxi_id]
                self.grid[y][x] = None
                del self.taxis[taxi_id]

    def get_location_coordinates(self, loc_id: str) -> Optional[Tuple[int, int]]:
        """Obtener coordenadas de una localización"""
        if loc_id in self.locations:
            loc = self.locations[loc_id]
            return (loc.x, loc.y)
        return None

    def get_state(self) -> List[List]:
        """Obtener estado actual del mapa"""
        with self.lock:
            return [row[:] for row in self.grid]

    def update_taxi_position(self, taxi_id: int, new_pos: Tuple[int, int], state: str) -> bool:
        """Actualizar posición de un taxi"""
        with self.lock:
            if not (0 <= new_pos[0] < self.size and 0 <= new_pos[1] < self.size):
                return False
                
            if taxi_id in self.taxis:
                old_x, old_y = self.taxis[taxi_id]
                self.grid[old_y][old_x] = None
                
            x, y = new_pos
            self.taxis[taxi_id] = new_pos
            self.grid[y][x] = ('taxi', taxi_id, state)
            return True
        
class CentralServer:
    def __init__(self, host='0.0.0.0', port=50051):
        self.host = host
        self.port = port
        self.running = True
        
        # Inicializar estructuras
        self.map_manager = MapManager()
        self.taxis: Dict[int, Taxi] = {}
        self.services: Dict[str, dict] = {}
        
        # Kafka
        self.kafka = KafkaClient(f"{host}:9092", "central_server")
        
        # Locks para sincronización
        self.taxi_lock = threading.Lock()
        self.service_lock = threading.Lock()
        
        # Socket servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        
        # Cargar localizaciones
        self.load_locations()
        
        logger.info(f"Central Server iniciado en {self.host}:{self.port}")

    def load_locations(self):
        """Cargar localizaciones desde archivo"""
        try:
            with open('data/EC_locations.json', 'r') as f:
                data = json.load(f)
                for loc in data['locations']:
                    loc_id = loc['Id']
                    x, y = map(int, loc['POS'].split(','))
                    if self.map_manager.add_location(loc_id, x, y):
                        logger.info(f"Localización {loc_id} añadida en ({x}, {y})")
            logger.info("Localizaciones cargadas correctamente")
        except Exception as e:
            logger.error(f"Error cargando localizaciones: {e}")

    def handle_client(self, client_socket: socket.socket, address: str):
        """Manejar conexión de cliente"""
        try:
            while self.running:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break
                    
                    message = json.loads(data)
                    msg_type = message.get('type')
                    
                    if msg_type == 'taxi':
                        self.handle_taxi_message(client_socket, message, address)
                    elif msg_type == 'customer':
                        self.handle_customer_message(client_socket, message, address)
                    elif msg_type == 'service_request':
                        self.handle_service_request(message, client_socket)
                    else:
                        logger.warning(f"Tipo de mensaje desconocido: {msg_type}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Error decodificando JSON: {e}")
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    break
                    
        finally:
            self.handle_client_disconnection(client_socket, address)

    def handle_taxi_message(self, client_socket: socket.socket, message: Dict, address: str):
        """Procesar mensajes de taxi"""
        taxi_id = message.get('taxi_id')
        msg_type = message.get('type')
        
        if msg_type == 'taxi':  # Registro inicial
            with self.taxi_lock:
                taxi = Taxi(
                    id=taxi_id,
                    state=TAXI_STATES['AVAILABLE'],
                    position=(1, 1),
                    client_socket=client_socket
                )
                self.taxis[taxi_id] = taxi
                self.map_manager.add_taxi(taxi_id, 1, 1, 'AVAILABLE')
                
                response = {'status': 'OK', 'message': 'Taxi registered'}
                client_socket.send(json.dumps(response).encode())
                logger.info(f"Taxi {taxi_id} registrado desde {address}")
                
                # Publicar estado en Kafka
                self.kafka.publish(TOPICS['TAXI_STATUS'], {
                    'taxi_id': taxi_id,
                    'state': 'AVAILABLE',
                    'position': (1, 1)
                })
                
        elif msg_type == 'position_update':
            position = tuple(message.get('position', [1, 1]))
            self.update_taxi_position(taxi_id, position)

    def handle_service_request(self, request: Dict, client_socket: socket.socket):
        """Procesar solicitud de servicio"""
        customer_id = request.get('customer_id')
        destination = request.get('destination')
        
        # Buscar taxi disponible
        taxi_id = self.find_available_taxi()
        
        if taxi_id is not None:
            service_id = f"SRV_{len(self.services) + 1}"
            
            with self.service_lock:
                self.services[service_id] = {
                    'id': service_id,
                    'customer_id': customer_id,
                    'taxi_id': taxi_id,
                    'destination': destination,
                    'state': SERVICE_STATES['ACCEPTED']
                }
            
            self.assign_service_to_taxi(taxi_id, service_id, destination)
            
            response = {
                'status': 'OK',
                'service_id': service_id,
                'taxi_id': taxi_id
            }
            logger.info(f"Servicio {service_id} asignado al taxi {taxi_id}")
        else:
            response = {
                'status': 'ERROR',
                'message': 'No hay taxis disponibles'
            }
            logger.warning("No hay taxis disponibles")
        
        client_socket.send(json.dumps(response).encode())

    def assign_service_to_taxi(self, taxi_id: int, service_id: str, destination: str):
        """Asignar servicio a un taxi"""
        with self.taxi_lock:
            if taxi_id in self.taxis:
                taxi = self.taxis[taxi_id]
                taxi.state = TAXI_STATES['BUSY']
                taxi.current_service = service_id
                
                # Obtener coordenadas del destino
                coords = self.map_manager.get_location_coordinates(destination)
                if coords:
                    taxi.destination = coords
                
                # Notificar al taxi
                message = {
                    'type': 'new_service',
                    'service_id': service_id,
                    'destination': destination,
                    'coordinates': coords
                }
                taxi.client_socket.send(json.dumps(message).encode())
                
                # Publicar en Kafka
                self.kafka.publish(TOPICS['SERVICE_UPDATES'], {
                    'service_id': service_id,
                    'taxi_id': taxi_id,
                    'state': 'ACCEPTED'
                })

    def update_taxi_position(self, taxi_id: int, position: Tuple[int, int]):
        """Actualizar posición de un taxi"""
        with self.taxi_lock:
            if taxi_id in self.taxis:
                taxi = self.taxis[taxi_id]
                if self.map_manager.update_taxi_position(taxi_id, position, taxi.state):
                    taxi.position = position
                    self.broadcast_map_update()
                    
                    # Publicar en Kafka
                    self.kafka.publish(TOPICS['TAXI_POSITIONS'], {
                        'taxi_id': taxi_id,
                        'position': position,
                        'state': taxi.state
                    })

    def broadcast_map_update(self):
        """Enviar actualización del mapa a todos los taxis"""
        map_state = self.map_manager.get_state()
        update = {
            'type': 'map_update',
            'map': map_state
        }
        
        with self.taxi_lock:
            for taxi in self.taxis.values():
                try:
                    taxi.client_socket.send(json.dumps(update).encode())
                except Exception as e:
                    logger.error(f"Error enviando mapa a taxi {taxi.id}: {e}")

    def find_available_taxi(self) -> Optional[int]:
        """Encontrar un taxi disponible"""
        with self.taxi_lock:
            for taxi_id, taxi in self.taxis.items():
                if taxi.state == TAXI_STATES['AVAILABLE']:
                    return taxi_id
        return None

    def handle_client_disconnection(self, client_socket: socket.socket, address: str):
        """Manejar desconexión de cliente"""
        with self.taxi_lock:
            for taxi_id, taxi in list(self.taxis.items()):
                if taxi.client_socket == client_socket:
                    logger.info(f"Taxi {taxi_id} desconectado")
                    self.map_manager.remove_taxi(taxi_id)
                    del self.taxis[taxi_id]
                    break
        client_socket.close()
        logger.info(f"Conexión cerrada con {address}")

    def run(self):
        """Iniciar el servidor central"""
        logger.info("Iniciando servidor central...")
        try:
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"Nueva conexión desde {address}")
                    threading.Thread(target=self.handle_client,
                                  args=(client_socket, address)).start()
                except Exception as e:
                    logger.error(f"Error aceptando conexión: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Apagando servidor...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpieza al cerrar"""
        self.running = False
        with self.taxi_lock:
            for taxi in self.taxis.values():
                try:
                    taxi.client_socket.close()
                except:
                    pass
        self.server_socket.close()
        self.kafka.close()

if __name__ == "__main__":
    server = CentralServer()
    server.run()