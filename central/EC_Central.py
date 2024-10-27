import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
import json
import logging
from typing import Dict, Optional
from common.config import CENTRAL_PORT, CENTRAL_HOST, SERVICE_STATES, TAXI_STATES
from map_manager import MapManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CentralServer:
    def __init__(self):
        self.map_manager = MapManager()
        self.taxis: Dict[int, dict] = {}  # Almacena información de taxis conectados
        self.services: Dict[str, dict] = {}  # Almacena servicios activos
        self.lock = threading.Lock()  # Para sincronización de acceso a recursos compartidos
        
        # Inicializar el servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((CENTRAL_HOST, CENTRAL_PORT))
        self.server_socket.listen(10)
        
        logger.info(f"Central Server iniciado en {CENTRAL_HOST}:{CENTRAL_PORT}")
        
        # Cargar localizaciones iniciales
        self.load_locations()

    def load_locations(self):
        """Cargar localizaciones desde el archivo JSON"""
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

    def handle_taxi_connection(self, client_socket: socket.socket, address: str):
        """Manejar la conexión de un taxi"""
        taxi_id = None
        try:
            # Recibir datos de autenticación
            data = client_socket.recv(1024).decode()
            if not data:
                return
                
            taxi_data = json.loads(data)
            taxi_id = taxi_data['taxi_id']
            
            with self.lock:
                # Registrar el taxi
                self.taxis[taxi_id] = {
                    'socket': client_socket,
                    'address': address,
                    'state': TAXI_STATES['AVAILABLE'],
                    'current_service': None
                }
                
                # Añadir taxi al mapa
                self.map_manager.add_taxi(taxi_id, 1, 1, TAXI_STATES['AVAILABLE'])
                logger.info(f"Taxi {taxi_id} conectado desde {address}")
            
            # Enviar confirmación
            client_socket.send(json.dumps({'status': 'OK'}).encode())
            
            # Bucle principal de recepción de mensajes del taxi
            while True:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                
                self.process_taxi_message(taxi_id, json.loads(data))
                
        except Exception as e:
            logger.error(f"Error en conexión de taxi: {e}")
        finally:
            if taxi_id is not None:
                self.handle_taxi_disconnection(taxi_id)
            else:
                client_socket.close()

    def handle_customer_connection(self, client_socket: socket.socket, address: str):
        """Manejar la conexión de un cliente"""
        try:
            while True:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                
                request = json.loads(data)
                if request['type'] == 'service_request':
                    self.process_service_request(request, client_socket)
                
        except Exception as e:
            logger.error(f"Error en conexión de cliente: {e}")
        finally:
            client_socket.close()

    def process_service_request(self, request: dict, client_socket: socket.socket):
        """Procesar una solicitud de servicio"""
        with self.lock:
            # Buscar taxi disponible
            available_taxi = self.find_available_taxi()
            
            if available_taxi:
                # Crear nuevo servicio
                service_id = f"SRV_{len(self.services) + 1}"
                
                # Obtener posición actual del cliente
                client_pos = request.get('current_position', None)
                
                service = {
                    'id': service_id,
                    'customer_socket': client_socket,
                    'taxi_id': available_taxi,
                    'pickup_location': client_pos,
                    'destination': request['destination'],
                    'state': SERVICE_STATES['ACCEPTED']
                }
                self.services[service_id] = service
                
                # Actualizar estado del taxi
                self.taxis[available_taxi]['state'] = TAXI_STATES['BUSY']
                self.taxis[available_taxi]['current_service'] = service_id
                
                # Enviar confirmación al cliente
                response = {
                    'status': 'OK',
                    'service_id': service_id,
                    'taxi_id': available_taxi,
                    'taxi_position': self.taxis[available_taxi].get('position', (1, 1))
                }
                client_socket.send(json.dumps(response).encode())
                
                # Enviar orden al taxi
                taxi_order = {
                    'type': 'new_service',
                    'service_id': service_id,
                    'pickup_location': client_pos,
                    'destination': request['destination']
                }
                self.taxis[available_taxi]['socket'].send(json.dumps(taxi_order).encode())
                
                logger.info(f"Servicio {service_id} asignado al taxi {available_taxi}")
            else:
                # No hay taxis disponibles
                response = {
                    'status': 'ERROR',
                    'message': 'No hay taxis disponibles'
                }
                client_socket.send(json.dumps(response).encode())
                logger.warning("Servicio rechazado: No hay taxis disponibles")

    def find_available_taxi(self) -> Optional[int]:
        """Encontrar el taxi disponible más cercano"""
        available_taxis = []
        
        for taxi_id, taxi_info in self.taxis.items():
            if taxi_info['state'] == TAXI_STATES['AVAILABLE']:
                available_taxis.append((taxi_id, taxi_info))
        
        if not available_taxis:
            return None
            
        # Si solo hay un taxi disponible, devolverlo
        if len(available_taxis) == 1:
            return available_taxis[0][0]
            
        # TODO: Implementar lógica para seleccionar el taxi más cercano
        # Por ahora, devolver el primer taxi disponible
        return available_taxis[0][0]

    def handle_taxi_disconnection(self, taxi_id: int):
        """Manejar la desconexión de un taxi"""
        with self.lock:
            if taxi_id in self.taxis:
                # Cerrar socket
                self.taxis[taxi_id]['socket'].close()
                # Eliminar taxi del mapa
                self.map_manager.remove_taxi(taxi_id)
                # Eliminar taxi del registro
                del self.taxis[taxi_id]
                logger.info(f"Taxi {taxi_id} desconectado")

    def process_taxi_message(self, taxi_id: int, message: dict):
        """Procesar mensajes recibidos de los taxis"""
        try:
            msg_type = message.get('type')
            
            if msg_type == 'position_update':
                # Actualizar posición del taxi en el mapa
                x, y = message['position']
                self.map_manager.move_taxi(taxi_id, x, y)
                
            elif msg_type == 'service_completed':
                # Procesar finalización de servicio
                service_id = message['service_id']
                if service_id in self.services:
                    service = self.services[service_id]
                    service['state'] = SERVICE_STATES['COMPLETED']
                    
                    # Notificar al cliente
                    completion_msg = {
                        'type': 'service_completed',
                        'service_id': service_id
                    }
                    service['customer_socket'].send(json.dumps(completion_msg).encode())
                    
                    # Actualizar estado del taxi
                    self.taxis[taxi_id]['state'] = TAXI_STATES['AVAILABLE']
                    self.taxis[taxi_id]['current_service'] = None
                    
                    logger.info(f"Servicio {service_id} completado por taxi {taxi_id}")
            
        except Exception as e:
            logger.error(f"Error procesando mensaje de taxi: {e}")

    def run(self):
        """Iniciar el servidor central"""
        logger.info("Iniciando servidor central...")
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                logger.info(f"Nueva conexión desde {address}")
                
                # Recibir tipo de cliente
                client_type = json.loads(client_socket.recv(1024).decode())['type']
                
                if client_type == 'taxi':
                    threading.Thread(target=self.handle_taxi_connection,
                                  args=(client_socket, address)).start()
                elif client_type == 'customer':
                    threading.Thread(target=self.handle_customer_connection,
                                  args=(client_socket, address)).start()
                
        except KeyboardInterrupt:
            logger.info("Apagando servidor central...")
        finally:
            self.server_socket.close()

if __name__ == "__main__":
    server = CentralServer()
    server.run()