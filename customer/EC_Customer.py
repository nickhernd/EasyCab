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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Customer:
    def __init__(self, customer_id: str, kafka_url: str):
        self.customer_id = customer_id
        self.pending_services: List[str] = []
        self.current_service: Optional[str] = None
        self.assigned_taxi: Optional[int] = None
        self.service_status = None
        
        # Control
        self.running = True
        self.lock = threading.Lock()
        
        # Kafka
        self.kafka = KafkaClient(kafka_url, f"customer_{customer_id}")
        self.setup_kafka()
        
        # UI
        self.display_lock = threading.Lock()
        
        # Cargar servicios
        self.load_services()

    def setup_kafka(self):
        """Configurar conexiones Kafka"""
        # Suscribirse a actualizaciones de servicio
        self.kafka.subscribe(
            TOPICS['SERVICE_UPDATES'],
            self.handle_service_update,
            f"customer_{self.customer_id}_service"
        )
        
        # Suscribirse a posiciones de taxis
        self.kafka.subscribe(
            TOPICS['TAXI_POSITIONS'],
            self.handle_taxi_position,
            f"customer_{self.customer_id}_positions"
        )

    def load_services(self) -> bool:
        """Cargar servicios desde archivo JSON"""
        try:
            logger.info("Intentando cargar servicios...")
            with open('data/EC_Requests.json', 'r') as f:
                data = json.load(f)
                self.pending_services = [req['Id'] for req in data['Requests']]
            logger.info(f"Cargados {len(self.pending_services)} servicios: {self.pending_services}")
            return True
        except Exception as e:
            logger.error(f"Error cargando servicios: {e}, {str(e)}")
            return False

    def request_service(self, destination: str) -> bool:
        """Solicitar un servicio de taxi"""
        try:
            logger.info(f"Intentando solicitar servicio a {destination}")
            request = {
                'type': 'service_request',
                'customer_id': self.customer_id,
                'destination': destination,
                'timestamp': time.time()
            }
            
            logger.debug(f"Enviando solicitud: {request}")
            self.send_to_central(request)
            
            # Esperar respuesta con timeout
            self.central_socket.settimeout(5.0)
            try:
                response = json.loads(self.central_socket.recv(1024).decode())
                logger.debug(f"Respuesta recibida: {response}")
                
                if response.get('status') == 'OK':
                    self.current_service = response.get('service_id')
                    taxi_id = response.get('taxi_id')
                    self.display_message(f"Servicio aceptado - Taxi {taxi_id} asignado")
                    return True
                else:
                    self.display_message(f"Servicio rechazado: {response.get('message')}")
                    return False
            except socket.timeout:
                logger.error("Timeout esperando respuesta de la central")
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
            
            if update_type == 'service_accepted':
                self.handle_service_accepted(payload)
            elif update_type == 'service_completed':
                self.handle_service_completed(service_id)
            elif update_type == 'service_cancelled':
                self.handle_service_cancelled(service_id)
            elif update_type == 'taxi_status':
                self.handle_taxi_status_update(payload)

    def handle_service_accepted(self, data: Dict):
        """Procesar aceptación de servicio"""
        with self.lock:
            self.current_service = data['service_id']
            self.assigned_taxi = data['taxi_id']
            self.service_status = 'ACCEPTED'
            self.display_message(f"Servicio aceptado - Taxi {self.assigned_taxi}")

    def handle_service_completed(self, service_id: str):
        """Procesar finalización de servicio"""
        if service_id == self.current_service:
            self.display_message(f"Servicio {service_id} completado")
            self.current_service = None
            self.assigned_taxi = None
            self.service_status = None
            
            # Programar siguiente servicio
            threading.Timer(4.0, self.request_next_service).start()

    def handle_taxi_position(self, message: Dict):
        """Procesar actualización de posición del taxi asignado"""
        payload = message.get('payload', {})
        taxi_id = payload.get('taxi_id')
        
        if taxi_id == self.assigned_taxi:
            position = payload.get('position')
            self.update_taxi_position(position)

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
            if self.assigned_taxi:
                print(f"Posición del taxi: {getattr(self, 'taxi_position', 'Desconocida')}")
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
            self.cleanup()

    def display_loop(self):
        """Actualizar display periódicamente"""
        while self.running:
            self.update_display()
            time.sleep(1)

    def cleanup(self):
        """Limpieza al cerrar"""
        self.running = False
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