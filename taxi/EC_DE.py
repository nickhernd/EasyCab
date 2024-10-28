import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import json
import threading
import time
import logging
from typing import Tuple, Optional
from common.config import CENTRAL_HOST, CENTRAL_PORT, TAXI_STATES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DigitalEngine:
    def __init__(self, taxi_id: int, sensor_port: int):
        self.taxi_id = taxi_id
        self.sensor_port = sensor_port
        self.position = (1, 1)  # Posición inicial
        self.state = TAXI_STATES['AVAILABLE']
        self.destination: Optional[Tuple[int, int]] = None
        self.current_service: Optional[str] = None
        
        # Conexión con el servidor central
        self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Socket para sensores
        self.sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sensor_socket.bind(('localhost', sensor_port))
        self.sensor_socket.listen(1)
        
        # Control de estado
        self.running = True
        self.paused = False
        self.lock = threading.Lock()

    def connect_to_central(self) -> bool:
        """Conectar con el servidor central"""
        try:
            print("hola con el servidor")
            self.central_socket.connect((CENTRAL_HOST, CENTRAL_PORT))
            print("hola con el servidor")
            # Enviar información de autenticación
            auth_data = {
                'type': 'taxi',
                'taxi_id': self.taxi_id
            }
            self.central_socket.send(json.dumps(auth_data).encode())
            
            # Esperar confirmación
            response = json.loads(self.central_socket.recv(1024).decode())
            if response.get('status') == 'OK':
                logger.info(f"Taxi {self.taxi_id} conectado al servidor central")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error conectando al servidor central: {e}")
            return False

    def start(self):
        """Iniciar el Digital Engine"""
        if not self.connect_to_central():
            logger.error("No se pudo conectar al servidor central")
            return

        # Iniciar threads
        threading.Thread(target=self.handle_central_messages).start()
        threading.Thread(target=self.handle_sensor_connection).start()
        threading.Thread(target=self.movement_controller).start()

        logger.info(f"Digital Engine del taxi {self.taxi_id} iniciado")

    def handle_central_messages(self):
        """Manejar mensajes del servidor central"""
        try:
            while self.running:
                data = self.central_socket.recv(1024).decode()
                if not data:
                    break
                
                message = json.loads(data)
                self.process_central_message(message)
                
        except Exception as e:
            logger.error(f"Error en comunicación con central: {e}")
        finally:
            self.running = False

    def handle_sensor_connection(self):
        """Manejar conexión con los sensores"""
        try:
            while self.running:
                sensor_client, addr = self.sensor_socket.accept()
                logger.info(f"Sensor conectado desde {addr}")
                
                threading.Thread(target=self.handle_sensor_messages, 
                               args=(sensor_client,)).start()
                
        except Exception as e:
            logger.error(f"Error en conexión de sensor: {e}")
        finally:
            self.sensor_socket.close()

    def handle_sensor_messages(self, sensor_client: socket.socket):
        """Procesar mensajes de los sensores"""
        try:
            while self.running:
                data = sensor_client.recv(1024).decode()
                if not data:
                    break
                
                message = json.loads(data)
                self.process_sensor_message(message)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje de sensor: {e}")
        finally:
            sensor_client.close()

    def process_central_message(self, message: dict):
        """Procesar mensajes recibidos del servidor central"""
        msg_type = message.get('type')
        
        if msg_type == 'new_service':
            with self.lock:
                self.current_service = message['service_id']
                self.state = TAXI_STATES['BUSY']
                # Obtener coordenadas del cliente primero
                client_coords = message.get('pickup_location')
                if client_coords:
                    self.destination = tuple(client_coords)
                    logger.info(f"Dirigiéndome a recoger al cliente en {self.destination}")
                else:
                    # Si no hay coordenadas de recogida, ir directamente al destino
                    dest_coords = self.get_location_coordinates(message['destination'])
                    if dest_coords:
                        self.destination = dest_coords
                        logger.info(f"Nuevo destino establecido: {self.destination}")
                    else:
                        logger.error(f"No se pudieron obtener coordenadas para {message['destination']}")
                        self.current_service = None
                        return
                
        elif msg_type == 'pickup_complete':
            # El cliente está en el taxi, ahora ir al destino final
            with self.lock:
                dest_coords = self.get_location_coordinates(message['destination'])
                if dest_coords:
                    self.destination = dest_coords
                    logger.info(f"Cliente recogido, dirigiéndome a {self.destination}")
                
        elif msg_type == 'stop':
            with self.lock:
                self.paused = True
                self.state = TAXI_STATES['STOPPED']
                logger.info("Taxi detenido por orden central")
                
        elif msg_type == 'resume':
            with self.lock:
                self.paused = False
                self.state = TAXI_STATES['BUSY'] if self.current_service else TAXI_STATES['AVAILABLE']
                logger.info("Taxi reanudado por orden central")
        
        elif msg_type == 'return_to_base':
            with self.lock:
                self.destination = self.get_location_coordinates('BASE')
                self.current_service = None
                self.state = TAXI_STATES['AVAILABLE']
                logger.info("Retornando a la base")

    def process_sensor_message(self, message: dict):
        """Procesar mensajes de los sensores"""
        if message.get('status') == 'KO':
            with self.lock:
                self.paused = True
                self.state = TAXI_STATES['STOPPED']
                logger.warning(f"Taxi detenido por sensor: {message.get('reason')}")
                
                # Notificar a central
                self.send_to_central({
                    'type': 'sensor_alert',
                    'reason': message.get('reason')
                })
        elif message.get('status') == 'OK' and self.paused:
            with self.lock:
                self.paused = False
                self.state = TAXI_STATES['BUSY'] if self.current_service else TAXI_STATES['AVAILABLE']
                logger.info("Sensores OK, reanudando movimiento")

    def movement_controller(self):
        """Controlar el movimiento del taxi"""
        while self.running:
            if not self.paused and self.destination:
                with self.lock:
                    new_position = self.calculate_next_position()
                    if new_position:
                        self.position = new_position
                        self.send_position_update()
                        
                        # Verificar si llegamos al destino
                        if self.position == self.destination:
                            self.handle_arrival()
                
            time.sleep(1)  # Actualizar cada segundo

    def calculate_next_position(self) -> Optional[Tuple[int, int]]:
        """Calcular siguiente posición hacia el destino considerando el mapa esférico"""
        if not self.destination:
            return None
            
        x, y = self.position
        dest_x, dest_y = self.destination
        
        # Calcular la diferencia teniendo en cuenta el mapa esférico
        dx = dest_x - x
        dy = dest_y - y
        
        # Ajustar para el mapa esférico (20x20)
        if abs(dx) > 10:  # Si la distancia es mayor que la mitad del mapa
            dx = -1 * (20 - abs(dx)) if dx > 0 else (20 - abs(dx))
        if abs(dy) > 10:
            dy = -1 * (20 - abs(dy)) if dy > 0 else (20 - abs(dy))
        
        # Determinar el siguiente movimiento
        new_x = x
        new_y = y
        
        # Movimiento diagonal si es posible
        if dx != 0 and dy != 0:
            new_x = (x + (1 if dx > 0 else -1)) % 20
            new_y = (y + (1 if dy > 0 else -1)) % 20
        # Si no, movimiento horizontal o vertical
        elif dx != 0:
            new_x = (x + (1 if dx > 0 else -1)) % 20
        elif dy != 0:
            new_y = (y + (1 if dy > 0 else -1)) % 20
            
        return (new_x, new_y)

    def handle_arrival(self):
        """Manejar la llegada al destino"""
        if self.current_service:
            if self.destination == self.get_location_coordinates('BASE'):
                logger.info("Llegada a la base")
                self.current_service = None
                self.state = TAXI_STATES['AVAILABLE']
            else:
                # Notificar servicio completado
                self.send_to_central({
                    'type': 'service_completed',
                    'service_id': self.current_service,
                    'location': self.position
                })
                
                # Volver a la base después de completar el servicio
                self.destination = self.get_location_coordinates('BASE')
                self.current_service = None
                self.state = TAXI_STATES['AVAILABLE']
                logger.info("Servicio completado, retornando a base")
        else:
            logger.info(f"Llegada al destino {self.position}")
            self.destination = None

    def send_position_update(self):
        """Enviar actualización de posición a central"""
        self.send_to_central({
            'type': 'position_update',
            'position': self.position
        })

    def send_to_central(self, message: dict):
        """Enviar mensaje al servidor central"""
        try:
            self.central_socket.send(json.dumps(message).encode())
        except Exception as e:
            logger.error(f"Error enviando mensaje a central: {e}")

    def get_location_coordinates(self, location_id: str) -> Optional[Tuple[int, int]]:
        """Convertir ID de localización a coordenadas basado en un mapeo conocido"""
        location_map = {
            'A': (5, 5),
            'B': (10, 10),
            'C': (15, 15),
            'BASE': (1, 1)
        }
        return location_map.get(location_id)

    def stop(self):
        """Detener el Digital Engine"""
        self.running = False
        self.central_socket.close()
        self.sensor_socket.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("taxi_id", type=int, help="ID del taxi")
    parser.add_argument("sensor_port", type=int, help="Puerto para conexión con sensores")
    args = parser.parse_args()

    taxi = DigitalEngine(args.taxi_id, args.sensor_port)
    try:
        taxi.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo Digital Engine...")
        taxi.stop()