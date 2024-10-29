import sys
import os
import socket
import json
import time
import logging
from typing import List, Optional

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Customer:
    def __init__(self, customer_id: str, kafka_ip: str, kafka_port: int):
        self.customer_id = customer_id
        self.kafka_url = f"{kafka_ip}:{kafka_port}"
        self.central_socket = None
        self.pending_services: List[str] = []
        self.current_service: Optional[str] = None
        self.assigned_taxi: Optional[int] = None
        
        # Cargar servicios
        self.load_services()

    def connect_to_central(self, central_ip: str, central_port: int) -> bool:
        """Intentar conectar al servidor central."""
        try:
            logger.info(f"Conectando a central {central_ip}:{central_port}...")
            self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.central_socket.connect((central_ip, central_port))
            
            # Autenticación
            auth_data = {'type': 'customer', 'customer_id': self.customer_id}
            self.send_message(self.central_socket, auth_data)
            
            # Recibir respuesta de autenticación
            response = self.receive_message(self.central_socket)
            if response.get('status') == 'OK':
                logger.info("Conexión con central establecida y autenticada.")
                return True
            else:
                logger.error("Autenticación fallida con central.")
                self.central_socket.close()
                self.central_socket = None
                return False
        except Exception as e:
            logger.error(f"Error conectando con central: {e}")
            self.central_socket = None
            return False

    def load_services(self) -> bool:
        """Cargar servicios desde el archivo JSON."""
        try:
            logger.info("Cargando servicios del archivo...")
            with open('data/EC_Requests.json', 'r') as f:
                data = json.load(f)
                self.pending_services = [req['destination'] for req in data['Requests']]
            logger.info(f"Servicios cargados: {self.pending_services}")
            return True
        except Exception as e:
            logger.error(f"Error al cargar servicios: {e}")
            return False

    def request_service(self, destination: str) -> bool:
        """Solicitar un servicio de taxi al servidor central."""
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
                logger.info(f"Servicio aceptado: Taxi {self.assigned_taxi} asignado para destino {destination}.")
                return True
            else:
                logger.warning(f"Servicio rechazado: {response.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Error solicitando servicio: {e}")
            return False

    def send_message(self, socket, message: dict):
        """Enviar mensaje en formato JSON a través de un socket."""
        try:
            socket.send(json.dumps(message).encode())
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")

    def receive_message(self, socket, buffer_size=1024) -> dict:
        """Recibir mensaje JSON desde un socket."""
        try:
            return json.loads(socket.recv(buffer_size).decode())
        except Exception as e:
            logger.error(f"Error recibiendo mensaje: {e}")
            return {}

    def run(self, central_ip: str, central_port: int):
        """Ejecutar el cliente y procesar cada solicitud de servicio."""
        if not self.connect_to_central(central_ip, central_port):
            logger.error("No se pudo conectar con la central.")
            return
        
        for destination in self.pending_services:
            logger.info(f"Solicitando servicio para el destino: {destination}")
            success = self.request_service(destination)
            time.sleep(4)  # Esperar 4 segundos entre servicios
            if not success:
                logger.warning(f"Reintentando servicio para el destino {destination} después de 4 segundos")
                time.sleep(4)
                self.request_service(destination)

        logger.info("Todos los servicios han sido procesados.")
        self.cleanup()

    def cleanup(self):
        """Cerrar la conexión con el servidor central al finalizar."""
        if self.central_socket:
            try:
                self.central_socket.close()
            except Exception as e:
                logger.error(f"Error cerrando el socket: {e}")
        logger.info("Cliente finalizado.")

if __name__ == "__main__":
    # Se espera que los argumentos se pasen en el siguiente orden: central_ip, central_port, kafka_ip, kafka_port, customer_id
    if len(sys.argv) != 6:
        print("Uso: python EC_Customer.py <central_ip> <central_port> <kafka_ip> <kafka_port> <customer_id>")
        sys.exit(1)

    central_ip = sys.argv[1]
    central_port = int(sys.argv[2])
    kafka_ip = sys.argv[3]
    kafka_port = int(sys.argv[4])
    customer_id = sys.argv[5]

    customer = Customer(customer_id, kafka_ip, kafka_port)
    customer.run(central_ip, central_port)
