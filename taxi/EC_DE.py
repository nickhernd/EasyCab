import sys
import os
import socket
import json
import threading
import time
import logging
import subprocess
from typing import Tuple, Optional, Dict
from dataclasses import dataclass

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.kafka_utils import KafkaClient, TOPICS, create_message

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DigitalEngine:
    def __init__(self, taxi_id: int, kafka_ip: str, kafka_port: int):
        self.taxi_id = taxi_id
        self.kafka_ip = kafka_ip
        self.kafka_port = kafka_port
        self.position = (1, 1)  # Posición inicial
        self.state = 'AVAILABLE'
        self.destination: Optional[Tuple[int, int]] = None
        self.current_service: Optional[str] = None
        self.map = [[None for _ in range(20)] for _ in range(20)]
        self.sensor_status = "OK"
        
        # Control
        self.running = True
        self.paused = False
        self.lock = threading.Lock()
        
        # Kafka
        self.kafka = KafkaClient(f"{kafka_ip}:{kafka_port}", f"taxi_{taxi_id}")
        
        # Socket para central
        self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        logger.info(f"Digital Engine del taxi {taxi_id} creado")
        
    def connect_to_central(self, host: str, port: int) -> bool:
        """Conectar con el servidor central"""
        try:
            logger.info(f"Conectando a central {host}:{port}...")
            self.central_socket.connect((host, port))
            
            # Autenticación
            auth_data = {
                'type': 'taxi',
                'taxi_id': self.taxi_id
            }
            self.central_socket.send(json.dumps(auth_data).encode())
            
            # Esperar respuesta
            response = json.loads(self.central_socket.recv(1024).decode())
            if response.get('status') == 'OK':
                logger.info("Conectado a central correctamente")
                return True
            
            logger.error(f"Error en autenticación: {response}")
            return False
            
        except Exception as e:
            logger.error(f"Error conectando a central: {e}")
            return False

    def start_sensors(self) -> Optional[subprocess.Popen]:
        """Iniciar los sensores del taxi"""
        try:
            sensor_process = subprocess.Popen([
                'python',
                os.path.join('taxi', 'EC_S.py'),
                str(self.taxi_id),
                self.kafka_ip,
                str(self.kafka_port)
            ])
            logger.info(f"Sensores iniciados (PID: {sensor_process.pid})")
            return sensor_process
        except Exception as e:
            logger.error(f"Error iniciando sensores: {e}")
            return None

    def movement_controller(self):
        """Gestionar movimiento del taxi"""
        while self.running:
            if not self.paused and self.destination and self.sensor_status == "OK":
                with self.lock:
                    next_pos = self.calculate_next_position()
                    if next_pos:
                        self.position = next_pos
                        self.publish_position()
                        
                        if self.position == self.destination:
                            self.handle_arrival()
            time.sleep(1)

    def calculate_next_position(self) -> Optional[Tuple[int, int]]:
        """Calcular siguiente posición hacia el destino"""
        if not self.destination:
            return None
            
        x, y = self.position
        dest_x, dest_y = self.destination
        
        # Calcular diferencias (mapa esférico)
        dx = dest_x - x
        dy = dest_y - y
        
        if abs(dx) > 10:  # Más de la mitad del mapa
            dx = -1 * (20 - abs(dx)) if dx > 0 else (20 - abs(dx))
        if abs(dy) > 10:
            dy = -1 * (20 - abs(dy)) if dy > 0 else (20 - abs(dy))
        
        # Calcular nuevo movimiento
        new_x = x
        new_y = y
        
        if dx != 0:
            new_x = (x + (1 if dx > 0 else -1)) % 20
        if dy != 0:
            new_y = (y + (1 if dy > 0 else -1)) % 20
        
        return (new_x, new_y)

    def handle_arrival(self):
        """Procesar llegada a destino"""
        with self.lock:
            if self.current_service:
                message = create_message('service_completed', {
                    'service_id': self.current_service,
                    'taxi_id': self.taxi_id,
                    'destination': self.position
                })
                self.kafka.publish(TOPICS['SERVICE_UPDATES'], message)
                logger.info(f"Servicio {self.current_service} completado")
            
            self.current_service = None
            self.destination = None
            self.state = 'AVAILABLE'
            self.publish_status()

    def publish_position(self):
        """Publicar posición actual"""
        message = create_message('position_update', {
            'taxi_id': self.taxi_id,
            'position': self.position,
            'state': self.state,
            'service_id': self.current_service
        })
        self.kafka.publish(TOPICS['TAXI_POSITIONS'], message)

    def publish_status(self):
        """Publicar estado actual"""
        message = create_message('status_update', {
            'taxi_id': self.taxi_id,
            'state': self.state,
            'position': self.position,
            'sensor_status': self.sensor_status,
            'current_service': self.current_service
        })
        self.kafka.publish(TOPICS['TAXI_STATUS'], message)

    def display_status(self):
        """Mostrar estado en pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n=== Taxi {self.taxi_id} ===")
        print(f"Estado: {self.state}")
        print(f"Posición: {self.position}")
        print(f"Destino: {self.destination}")
        print(f"Servicio actual: {self.current_service}")
        print(f"Estado sensores: {self.sensor_status}")
        if self.map:
            print("\nMapa actual:")
            for row in self.map:
                print(" ".join(str(cell or '.') for cell in row))
        print("=" * 40)

    def display_controller(self):
        """Controlador de display"""
        while self.running:
            self.display_status()
            time.sleep(1)

    def run(self):
        """Iniciar Digital Engine"""
        logger.info("Iniciando Digital Engine...")
        
        # Iniciar sensores
        self.sensor_process = self.start_sensors()
        if not self.sensor_process:
            return
        
        # Iniciar threads
        threads = [
            threading.Thread(target=self.movement_controller),
            threading.Thread(target=self.display_controller)
        ]
        
        for thread in threads:
            thread.daemon = True
            thread.start()
        
        try:
            while self.running:
                time.sleep(1)
                self.publish_status()
        except KeyboardInterrupt:
            logger.info("Deteniendo Digital Engine...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpieza al cerrar"""
        self.running = False
        
        # Detener sensores
        if hasattr(self, 'sensor_process') and self.sensor_process:
            logger.info("Deteniendo sensores...")
            self.sensor_process.terminate()
            self.sensor_process.wait()
        
        # Cerrar conexiones
        self.kafka.close()
        self.central_socket.close()
        logger.info("Digital Engine detenido")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='EC_DE: Digital Engine')
    parser.add_argument('central_ip', help='IP del servidor central')
    parser.add_argument('central_port', type=int, help='Puerto del servidor central')
    parser.add_argument('kafka_ip', help='IP del broker Kafka')
    parser.add_argument('kafka_port', type=int, help='Puerto del broker Kafka')
    parser.add_argument('taxi_id', type=int, help='ID del taxi')
    
    args = parser.parse_args()
    
    taxi = DigitalEngine(
        taxi_id=args.taxi_id,
        kafka_ip=args.kafka_ip,
        kafka_port=args.kafka_port
    )
    
    if taxi.connect_to_central(args.central_ip, args.central_port):
        taxi.run()