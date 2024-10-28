import sys
import os
import socket
import json
import threading
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

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

class CentralServer:
    def __init__(self, host='0.0.0.0', port=50051):
        self.host = host
        self.port = port
        self.running = True
        
        # Estructuras de datos
        self.locations: Dict[str, Location] = {}
        self.taxis: Dict[int, Taxi] = {}
        self.services: Dict[str, Dict] = {}
        self.map = [[None for _ in range(20)] for _ in range(20)]
        
        # Locks para sincronización
        self.map_lock = threading.Lock()
        self.taxi_lock = threading.Lock()
        self.service_lock = threading.Lock()
        
        # Inicializar servidor
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
                    self.add_location(loc_id, x, y)
            logger.info("Localizaciones cargadas correctamente")
        except Exception as e:
            logger.error(f"Error cargando localizaciones: {e}")

    def add_location(self, loc_id: str, x: int, y: int):
        """Añadir una localización al mapa"""
        with self.map_lock:
            location = Location(loc_id, x, y)
            self.locations[loc_id] = location
            self.map[y][x] = ('location', loc_id)
            logger.info(f"Localización {loc_id} añadida en ({x}, {y})")

    def handle_client(self, client_socket: socket.socket, address: str):
        """Manejar conexión de cliente"""
        try:
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                        
                    message = data.decode()
                    logger.debug(f"Mensaje recibido de {address}: {message}")
                    
                    try:
                        json_data = json.loads(message)
                        client_type = json_data.get('type')
                        
                        if client_type == 'taxi':
                            self.handle_taxi_message(client_socket, json_data, address)
                        elif client_type == 'customer':
                            self.handle_customer_message(client_socket, json_data, address)
                        else:
                            logger.warning(f"Tipo de cliente desconocido: {client_type}")
                            response = {'status': 'error', 'message': 'Unknown client type'}
                            client_socket.send(json.dumps(response).encode())
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decodificando JSON: {e}, mensaje: {message}")
                        response = {'status': 'error', 'message': 'Invalid JSON format'}
                        client_socket.send(json.dumps(response).encode())
                        
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error en conexión con {address}: {e}")
        finally:
            self.handle_client_disconnection(client_socket, address)

    def handle_client_disconnection(self, client_socket: socket.socket, address: str):
        """Manejar desconexión de cliente"""
        # Buscar si es un taxi
        with self.taxi_lock:
            for taxi_id, taxi in list(self.taxis.items()):
                if taxi.client_socket == client_socket:
                    logger.info(f"Taxi {taxi_id} desconectado")
                    self.remove_taxi(taxi_id)
                    break
        
        client_socket.close()
        logger.info(f"Conexión cerrada con {address}")

    def handle_taxi_message(self, client_socket: socket.socket, data: Dict, address: str):
        """Procesar mensajes de taxi"""
        msg_type = data.get('type')
        taxi_id = data.get('taxi_id')
        
        if msg_type == 'taxi':
            # Autenticación inicial
            with self.taxi_lock:
                if taxi_id not in self.taxis:
                    taxi = Taxi(
                        id=taxi_id,
                        state=TAXI_STATES['AVAILABLE'],
                        position=(1, 1),
                        client_socket=client_socket
                    )
                    self.taxis[taxi_id] = taxi
                    self.update_map_taxi(taxi)
                    response = {'status': 'OK', 'message': 'Taxi registered'}
                else:
                    response = {'status': 'error', 'message': 'Taxi ID already exists'}
                
                client_socket.send(json.dumps(response).encode())
        
        elif msg_type == 'position_update':
            # Actualización de posición
            new_pos = tuple(data.get('position', [1, 1]))
            with self.taxi_lock:
                if taxi_id in self.taxis:
                    taxi = self.taxis[taxi_id]
                    self.update_taxi_position(taxi_id, new_pos)
                    self.broadcast_map_update()

    def handle_customer_message(self, client_socket: socket.socket, data: Dict, address: str):
        """Procesar mensajes de cliente"""
        msg_type = data.get('type')
        
        if msg_type == 'service_request':
            destination = data.get('destination')
            customer_id = data.get('customer_id')
            
            # Buscar taxi disponible
            taxi_id = self.find_available_taxi()
            
            if taxi_id is not None:
                # Crear servicio
                service_id = f"SRV_{len(self.services) + 1}"
                with self.service_lock:
                    self.services[service_id] = {
                        'id': service_id,
                        'customer_id': customer_id,
                        'taxi_id': taxi_id,
                        'destination': destination,
                        'state': SERVICE_STATES['ACCEPTED']
                    }
                
                # Notificar al taxi
                self.assign_service_to_taxi(taxi_id, service_id, destination)
                
                # Responder al cliente
                response = {
                    'status': 'OK',
                    'service_id': service_id,
                    'taxi_id': taxi_id
                }
            else:
                response = {
                    'status': 'error',
                    'message': 'No hay taxis disponibles'
                }
            
            client_socket.send(json.dumps(response).encode())

    def find_available_taxi(self) -> Optional[int]:
        """Encontrar un taxi disponible"""
        with self.taxi_lock:
            for taxi_id, taxi in self.taxis.items():
                if taxi.state == TAXI_STATES['AVAILABLE']:
                    return taxi_id
        return None

    def assign_service_to_taxi(self, taxi_id: int, service_id: str, destination: str):
        """Asignar servicio a un taxi"""
        with self.taxi_lock:
            if taxi_id in self.taxis:
                taxi = self.taxis[taxi_id]
                taxi.state = TAXI_STATES['BUSY']
                taxi.current_service = service_id
                
                # Obtener coordenadas del destino
                if destination in self.locations:
                    dest_loc = self.locations[destination]
                    taxi.destination = (dest_loc.x, dest_loc.y)
                
                # Notificar al taxi
                message = {
                    'type': 'new_service',
                    'service_id': service_id,
                    'destination': destination
                }
                taxi.client_socket.send(json.dumps(message).encode())

    def update_taxi_position(self, taxi_id: int, new_pos: Tuple[int, int]):
        """Actualizar posición de un taxi"""
        with self.map_lock:
            if taxi_id in self.taxis:
                taxi = self.taxis[taxi_id]
                old_pos = taxi.position
                
                # Limpiar posición anterior
                x, y = old_pos
                if self.map[y][x] and self.map[y][x][0] == 'taxi':
                    self.map[y][x] = None
                
                # Actualizar nueva posición
                new_x, new_y = new_pos
                taxi.position = new_pos
                self.map[new_y][new_x] = ('taxi', taxi_id)

    def update_map_taxi(self, taxi: Taxi):
        """Actualizar taxi en el mapa"""
        with self.map_lock:
            x, y = taxi.position
            self.map[y][x] = ('taxi', taxi.id)

    def remove_taxi(self, taxi_id: int):
        """Eliminar un taxi del sistema"""
        with self.taxi_lock, self.map_lock:
            if taxi_id in self.taxis:
                taxi = self.taxis[taxi_id]
                x, y = taxi.position
                self.map[y][x] = None
                del self.taxis[taxi_id]

    def broadcast_map_update(self):
        """Enviar actualización del mapa a todos los taxis"""
        map_state = self.get_map_state()
        update = {
            'type': 'map_update',
            'map': map_state
        }
        
        with self.taxi_lock:
            for taxi in self.taxis.values():
                try:
                    taxi.client_socket.send(json.dumps(update).encode())
                except:
                    pass

    def get_map_state(self) -> List[List]:
        """Obtener estado actual del mapa"""
        with self.map_lock:
            return [row[:] for row in self.map]

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
        """Limpieza al cerrar el servidor"""
        self.running = False
        
        # Cerrar conexiones de taxis
        with self.taxi_lock:
            for taxi in self.taxis.values():
                if taxi.client_socket:
                    try:
                        taxi.client_socket.close()
                    except:
                        pass
        
        # Cerrar socket del servidor
        self.server_socket.close()

if __name__ == "__main__":
    server = CentralServer()
    server.run()