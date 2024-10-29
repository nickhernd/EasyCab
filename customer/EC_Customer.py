import socket
import sys
import os
import json
import threading
import time
import logging
from typing import List, Dict, Optional

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Customer:
    def __init__(self, customer_id: str, kafka_url: str):
        self.customer_id = customer_id
        self.pending_services: List[str] = []
        self.current_service: Optional[str] = None
        self.assigned_taxi: Optional[int] = None
        self.service_status = None
        self.taxi_position = "Unknown"
        self.central_socket = None
        
        self.running = True
        self.lock = threading.Lock()
        
        # Conexión Kafka
        self.kafka_url = kafka_url
        self.setup_kafka()
        
        # Cargar servicios
        self.load_services()

    def connect_to_central(self, host: str, port: int, retries: int = 3) -> bool:
        """Intentar conexión con Central Server con reintentos."""
        for attempt in range(retries):
            try:
                logger.info(f"Intentando conectar con central {host}:{port} (Intento {attempt+1}/{retries})")
                self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.central_socket.connect((host, port))
                
                # Autenticación
                auth_data = {'type': 'customer', 'customer_id': self.customer_id}
                self.send_message(self.central_socket, auth_data)
                
                # Recibir respuesta
                response = self.receive_message(self.central_socket)
                if response.get('status') == 'OK':
                    logger.info("Conexión exitosa con central")
                    return True
                logger.error(f"Error en la conexión: {response}")
            except Exception as e:
                logger.error(f"Fallo en intento {attempt+1}: {e}")
                time.sleep(1)
        
        # Si falla, cerrar el socket
        if self.central_socket:
            self.central_socket.close()
        self.central_socket = None
        return False

    def setup_kafka(self):
        """Configurar Kafka - Suscripciones a temas."""
        # Aquí se configurará la conexión con Kafka y suscripciones si es necesario.
        logger.info(f"Kafka configurado en {self.kafka_url} para cliente {self.customer_id}")

    def load_services(self) -> bool:
        """Cargar servicios desde archivo JSON."""
        try:
            logger.info("Cargando servicios...")
            with open('data/EC_Requests.json', 'r') as f:
                data = json.load(f)
                self.pending_services = [req['Id'] for req in data['Requests']]
            logger.info(f"Servicios cargados: {self.pending_services}")
            return True
        except Exception as e:
            logger.error(f"Error cargando servicios: {e}")
            return False

    def request_service(self, destination: str) -> bool:
        """Solicitar un servicio de taxi."""
        if not self.central_socket:
            logger.error("Conexión con central no establecida. No se puede solicitar el servicio.")
            return False

        try:
            request = {
                'type': 'service_request',
                'customer_id': self.customer_id,
                'destination': destination
            }
            self.send_message(self.central_socket, request)
            response = self.receive_message(self.central_socket)
            
            if response.get('status') == 'OK':
                self.current_service = response.get('service_id')
                self.assigned_taxi = response.get('taxi_id')
                logger.info(f"Servicio aceptado - Taxi {self.assigned_taxi} asignado")
                return True
            else:
                logger.info(f"Servicio rechazado: {response.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Error solicitando servicio: {e}")
            return False

    def send_message(self, socket, message: dict):
        """Enviar mensaje codificado en JSON a un socket."""
        try:
            socket.send(json.dumps(message).encode())
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")

    def receive_message(self, socket, buffer_size=1024) -> dict:
        """Recibir mensaje JSON de un socket."""
        try:
            return json.loads(socket.recv(buffer_size).decode())
        except Exception as e:
            logger.error(f"Error recibiendo mensaje: {e}")
            return {}

    def request_next_service(self):
        """Solicitar el siguiente servicio en la cola de espera."""
        with self.lock:
            if not self.pending_services:
                logger.info("No hay más servicios pendientes")
                return
            
            destination = self.pending_services.pop(0)
            logger.info(f"Solicitando servicio a {destination}")
            if not self.request_service(destination):
                self.pending_services.insert(0, destination)
                threading.Timer(5.0, self.request_next_service).start()

    def run(self, central_ip: str, central_port: int):
        """Ejecutar el cliente."""
        # Intentar conexión con central
        if not self.connect_to_central(central_ip, central_port):
            logger.error("No se pudo conectar con la central")
            return
        
        # Iniciar solicitud de servicios
        self.request_next_service()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()

    def cleanup(self):
        """Limpiar recursos al salir."""
        self.running = False
        if self.central_socket:
            try:
                self.central_socket.close()
            except Exception as e:
                logger.error(f"Error cerrando el socket: {e}")
            finally:
                self.central_socket = None
        logger.info("Cliente finalizado")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='EC_Customer: Cliente de EasyCab')
    
    parser.add_argument('central_ip', help='IP del servidor central')
    parser.add_argument('central_port', type=int, help='Puerto del servidor central')
    parser.add_argument('kafka_ip', help='IP del broker Kafka')
    parser.add_argument('kafka_port', type=int, help='Puerto del broker Kafka')
    parser.add_argument('customer_id', help='ID del cliente')
    
    args = parser.parse_args()
    
    kafka_url = f"{args.kafka_ip}:{args.kafka_port}"
    customer = Customer(args.customer_id, kafka_url)
    customer.run(args.central_ip, args.central_port)
