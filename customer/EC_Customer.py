import socket
import sys
import os
import json
import threading
import time
import logging
from typing import List, Dict, Optional

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.kafka_utils import KafkaClient, TOPICS, create_message

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
        self.taxi_position = None
        
        # Control
        self.running = True
        self.lock = threading.Lock()
        
        # Conexión central
        self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Kafka
        self.kafka = KafkaClient(kafka_url, f"customer_{customer_id}")
        
        # UI
        self.display_lock = threading.Lock()
        
        # Inicialización
        if not self.connect_to_central(kafka_url.split(':')[0], 50051):
            raise Exception("No se pudo conectar a la central")
            
        self.setup_kafka()
        self.load_services()
        logger.info(f"Cliente {customer_id} iniciado")

    def connect_to_central(self, host: str, port: int) -> bool:
        """Conectar con el servidor central"""
        try:
            logger.info(f"Conectando a central {host}:{port}")
            self.central_socket.connect((host, port))
            
            # Enviar autenticación
            auth_data = {
                'type': 'customer',
                'customer_id': self.customer_id
            }
            self.central_socket.send(json.dumps(auth_data).encode())
            
            # Esperar respuesta
            response = json.loads(self.central_socket.recv(1024).decode())
            if response.get('status') == 'OK':
                logger.info("Conectado a central")
                return True
                
            logger.error(f"Error en autenticación: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error conectando a central: {e}")
            return False

    def setup_kafka(self):
        """Configurar suscripciones Kafka"""
        self.kafka.subscribe(
            TOPICS['SERVICE_UPDATES'],
            self.handle_service_update,
            f"customer_{self.customer_id}_service"
        )
        
        self.kafka.subscribe(
            TOPICS['TAXI_POSITIONS'],
            self.handle_taxi_position,
            f"customer_{self.customer_id}_positions"
        )

    def load_services(self) -> bool:
        """Cargar servicios desde archivo"""
        try:
            logger.info("Cargando servicios...")
            with open('data/EC_Requests.json', 'r') as f:
                data = json.load(f)
                self.pending_services = [req['Id'] for req in data['Requests']]
            logger.info(f"Cargados {len(self.pending_services)} servicios: {self.pending_services}")
            return True
        except Exception as e:
            logger.error(f"Error cargando servicios: {e}")
            return False

    def request_service(self, destination: str) -> bool:
        """Solicitar servicio"""
        try:
            logger.info(f"Solicitando servicio a {destination}")
            request = {
                'type': 'service_request',
                'customer_id': self.customer_id,
                'destination': destination
            }
            
            self.central_socket.send(json.dumps(request).encode())
            
            # Esperar respuesta con timeout
            self.central_socket.settimeout(5.0)
            try:
                response = json.loads(self.central_socket.recv(1024).decode())
                logger.debug(f"Respuesta recibida: {response}")
                
                if response.get('status') == 'OK':
                    self.current_service = response.get('service_id')
                    self.assigned_taxi = response.get('taxi_id')
                    self.service_status = 'ACCEPTED'
                    self.display_message(f"Servicio aceptado - Taxi {self.assigned_taxi}")
                    return True
                else:
                    self.display_message(f"Servicio rechazado: {response.get('message')}")
                    return False
            except socket.timeout:
                logger.error("Timeout esperando respuesta")
                return False
                
        except Exception as e:
            logger.error(f"Error solicitando servicio: {e}")
            return False

    def handle_service_update(self, message: Dict):
        """Procesar actualización de servicio"""
        payload = message.get('payload', {})
        if payload.get('customer_id') == self.customer_id:
            update_type = payload.get('update_type')
            service_id = payload.get('service_id')
            
            if update_type == 'service_completed':
                self.handle_service_completed(service_id)
            elif update_type == 'service_cancelled':
                self.handle_service_cancelled(service_id)
            elif update_type == 'taxi_status':
                self.handle_taxi_status_update(payload)

    def handle_service_completed(self, service_id: str):
        """Procesar servicio completado"""
        if service_id == self.current_service:
            self.display_message(f"Servicio {service_id} completado")
            
            with self.lock:
                self.current_service = None
                self.assigned_taxi = None
                self.service_status = None
                self.taxi_position = None
            
            # Programar siguiente servicio
            threading.Timer(4.0, self.request_next_service).start()

    def handle_service_cancelled(self, service_id: str):
        """Procesar cancelación de servicio"""
        if service_id == self.current_service:
            self.display_message(f"Servicio {service_id} cancelado")
            self.request_next_service()

    def handle_taxi_status_update(self, data: Dict):
        """Procesar actualización de estado del taxi"""
        if data.get('taxi_id') == self.assigned_taxi:
            self.service_status = data.get('status')

    def handle_taxi_position(self, message: Dict):
        """Procesar posición del taxi"""
        payload = message.get('payload', {})
        taxi_id = payload.get('taxi_id')
        
        if taxi_id == self.assigned_taxi:
            self.taxi_position = payload.get('position')

    def request_next_service(self):
        """Solicitar siguiente servicio"""
        with self.lock:
            if not self.pending_services:
                self.display_message("No hay más servicios pendientes")
                return
            
            destination = self.pending_services.pop(0)
            self.display_message(f"Solicitando servicio a {destination}")
            
            if not self.request_service(destination):
                # Reintentar en caso de fallo
                self.pending_services.insert(0, destination)
                threading.Timer(5.0, self.request_next_service).start()

    def display_message(self, message: str):
        """Mostrar mensaje en pantalla"""
        with self.display_lock:
            print(f"\n{self.customer_id}: {message}")

    def update_display(self):
        """Actualizar interfaz"""
        with self.display_lock:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\n=== Cliente {self.customer_id} ===")
            print(f"Servicio actual: {self.current_service}")
            print(f"Estado: {self.service_status}")
            print(f"Taxi asignado: {self.assigned_taxi}")
            print(f"Servicios pendientes: {len(self.pending_services)}")
            if self.taxi_position:
                print(f"Posición del taxi: {self.taxi_position}")
            print("=" * 40)

    def run(self):
        """Iniciar cliente"""
        # Iniciar thread de display
        display_thread = threading.Thread(target=self.display_loop)
        display_thread.daemon = True
        display_thread.start()
        
        # Solicitar primer servicio
        self.request_next_service()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deteniendo cliente...")
        finally:
            self.cleanup()

    def display_loop(self):
        """Actualizar display periódicamente"""
        while self.running:
            self.update_display()
            time.sleep(1)

    def cleanup(self):
        """Limpieza al cerrar"""
        self.running = False
        if hasattr(self, 'central_socket'):
            self.central_socket.close()
        if hasattr(self, 'kafka'):
            self.kafka.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='EC_Customer: Cliente de Taxi')
    
    parser.add_argument('kafka_ip', help='IP del broker Kafka')
    parser.add_argument('kafka_port', type=int, help='Puerto del broker Kafka')
    parser.add_argument('customer_id', help='ID del cliente')
    
    args = parser.parse_args()
    
    kafka_url = f"{args.kafka_ip}:{args.kafka_port}"
    customer = Customer(args.customer_id, kafka_url)
    customer.run()