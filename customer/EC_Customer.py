import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import json
import time
import logging
import threading
from typing import List, Optional
from common.config import CENTRAL_HOST, CENTRAL_PORT, SERVICE_STATES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Customer:
    def __init__(self, customer_id: str, services_file: str):
        self.customer_id = customer_id
        self.services_file = services_file
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.pending_services: List[str] = []  # Lista de destinos pendientes
        self.current_service: Optional[str] = None
        self.running = True
        self.lock = threading.Lock()

    def load_services(self) -> bool:
        """Cargar servicios desde archivo JSON"""
        try:
            logger.info(f"Intentando cargar servicios desde: {self.services_file}")
            
            # Verificar que el archivo existe
            if not os.path.exists(self.services_file):
                logger.error(f"El archivo {self.services_file} no existe")
                return False
                
            # Leer el contenido del archivo
            with open(self.services_file, 'r') as f:
                content = f.read()
                logger.debug(f"Contenido del archivo: {content[:100]}...")  # Log primeros 100 caracteres
                
                # Intentar parsear el JSON
                data = json.loads(content)
                
                # Verificar la estructura del JSON
                if 'Requests' not in data:
                    logger.error("El archivo JSON no contiene la clave 'Requests'")
                    return False
                    
                self.pending_services = [req['Id'] for req in data['Requests']]
                logger.info(f"Cargados {len(self.pending_services)} servicios: {self.pending_services}")
                return True
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {e}")
            logger.error(f"Error en la posición: {e.pos}")
            logger.error(f"Línea del error: {e.lineno}, Columna: {e.colno}")
            return False
        except Exception as e:
            logger.error(f"Error cargando servicios: {e}")
            return False

    def connect_to_central(self) -> bool:
        """Conectar con el servidor central"""
        try:
            self.socket.connect((CENTRAL_HOST, CENTRAL_PORT))
            
            # Enviar identificación
            auth_data = {
                'type': 'customer',
                'customer_id': self.customer_id
            }
            self.socket.send(json.dumps(auth_data).encode())
            logger.info("Conectado al servidor central")
            return True
            
        except Exception as e:
            logger.error(f"Error conectando al servidor central: {e}")
            return False

    def request_service(self, destination: str) -> bool:
        """Solicitar un servicio de taxi"""
        try:
            request = {
                'type': 'service_request',
                'customer_id': self.customer_id,
                'destination': destination,
                'timestamp': time.time()
            }
            
            # Enviar solicitud
            self.socket.send(json.dumps(request).encode())
            
            # Esperar respuesta
            response = json.loads(self.socket.recv(1024).decode())
            
            if response.get('status') == 'OK':
                self.current_service = response.get('service_id')
                logger.info(f"Servicio {self.current_service} aceptado - Taxi asignado: {response.get('taxi_id')}")
                return True
            else:
                logger.warning(f"Servicio rechazado: {response.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error solicitando servicio: {e}")
            return False

    def handle_central_messages(self):
        """Manejar mensajes del servidor central"""
        try:
            while self.running:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                message = json.loads(data)
                self.process_message(message)
                
        except Exception as e:
            logger.error(f"Error en comunicación con central: {e}")
            self.running = False

    def process_message(self, message: dict):
        """Procesar mensajes recibidos"""
        msg_type = message.get('type')
        
        if msg_type == 'service_completed':
            with self.lock:
                service_id = message.get('service_id')
                if service_id == self.current_service:
                    logger.info(f"Servicio {service_id} completado")
                    self.current_service = None
                    
                    # Programar siguiente servicio después de 4 segundos
                    threading.Timer(4.0, self.request_next_service).start()

        elif msg_type == 'taxi_update':
            # Actualización sobre el taxi asignado
            logger.info(f"Actualización del taxi: {message.get('status')}")

    def request_next_service(self):
        """Solicitar siguiente servicio de la lista"""
        with self.lock:
            if not self.pending_services:
                logger.info("No hay más servicios pendientes")
                return
                
            destination = self.pending_services.pop(0)
            logger.info(f"Solicitando nuevo servicio a {destination}")
            
            if not self.request_service(destination):
                # Si falla, esperar y reintentar
                self.pending_services.insert(0, destination)
                threading.Timer(5.0, self.request_next_service).start()

    def run(self):
        """Iniciar el cliente"""
        if not self.load_services():
            logger.error("No se pudieron cargar los servicios")
            return

        if not self.connect_to_central():
            logger.error("No se pudo conectar al servidor central")
            return

        # Iniciar thread para recibir mensajes
        threading.Thread(target=self.handle_central_messages).start()

        # Solicitar primer servicio
        self.request_next_service()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deteniendo cliente...")
        finally:
            self.stop()

    def stop(self):
        """Detener el cliente"""
        self.running = False
        if self.socket:
            self.socket.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("customer_id", help="ID del cliente")
    parser.add_argument("services_file", help="Archivo con lista de servicios")
    args = parser.parse_args()

    customer = Customer(args.customer_id, args.services_file)
    customer.run()