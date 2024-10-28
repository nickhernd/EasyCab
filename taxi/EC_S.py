import sys
import os
import json
import threading
import time
import logging
from typing import Dict
import random

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.kafka_utils import KafkaClient, TOPICS, create_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaxiSensor:
    def __init__(self, taxi_id: int, kafka_url: str):
        self.taxi_id = taxi_id
        self.status = "OK"
        self.reason = None
        self.running = True
        self.lock = threading.Lock()
        
        # Kafka
        self.kafka = KafkaClient(kafka_url, f"sensor_{taxi_id}")
        
        # Incidencias posibles
        self.incidents = [
            "Obstáculo detectado",
            "Semáforo en rojo",
            "Peatón cruzando",
            "Vehículo cercano",
            "Condiciones climáticas adversas",
            "Obras en la vía",
            "Congestión de tráfico",
            "Emergencia en la ruta"
        ]
        self.current_incident = 0
        
        # Variables de monitoreo
        self.last_report_time = time.time()
        self.incident_duration = 0
        self.incident_count = 0
        
        logger.info(f"Sensor del taxi {taxi_id} iniciado")

    def publish_status(self):
        """Publicar estado actual en Kafka"""
        message = create_message('sensor_status', {
            'taxi_id': self.taxi_id,
            'status': self.status,
            'reason': self.reason,
            'incident_count': self.incident_count,
            'current_duration': self.incident_duration if self.status == "KO" else 0
        })
        
        self.kafka.publish(TOPICS['SENSOR_DATA'], message)

    def toggle_status(self):
        """Cambiar estado del sensor"""
        with self.lock:
            current_time = time.time()
            
            if self.status == "OK":
                self.status = "KO"
                self.reason = self.get_next_incident()
                self.last_report_time = current_time
                self.incident_count += 1
                logger.warning(f"¡Incidencia detectada! {self.reason}")
            else:
                self.status = "OK"
                self.reason = None
                self.incident_duration = current_time - self.last_report_time
                logger.info(f"Incidencia resuelta. Duración: {self.incident_duration:.2f} segundos")
            
            self.publish_status()

    def get_next_incident(self) -> str:
        """Obtener siguiente incidencia"""
        incident = self.incidents[self.current_incident]
        self.current_incident = (self.current_incident + 1) % len(self.incidents)
        return incident

    def simulate_random_incidents(self):
        """Simular incidencias aleatorias"""
        while self.running:
            time.sleep(random.uniform(30, 120))  # Entre 30s y 2min
            if random.random() < 0.3:  # 30% de probabilidad
                self.toggle_status()
                if self.status == "KO":
                    # Resolver automáticamente después de un tiempo
                    threading.Timer(
                        random.uniform(5, 15),  # Entre 5s y 15s
                        self.toggle_status
                    ).start()

    def display_status(self):
        """Mostrar estado actual"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n=== Sensor del Taxi {self.taxi_id} ===")
        print(f"Estado: {self.status}")
        if self.reason:
            print(f"Razón: {self.reason}")
        print(f"Incidencias totales: {self.incident_count}")
        if self.status == "KO":
            duration = time.time() - self.last_report_time
            print(f"Duración actual: {duration:.2f}s")
        print("\nComandos:")
        print("t - Toggle estado (OK/KO)")
        print("r - Activar/desactivar incidencias aleatorias")
        print("q - Salir")
        print("=" * 40)

    def keyboard_control(self):
        """Control por teclado"""
        random_incidents_active = False
        random_thread = None

        while self.running:
            self.display_status()
            cmd = input().lower()
            
            if cmd == 't':
                self.toggle_status()
            elif cmd == 'r':
                random_incidents_active = not random_incidents_active
                if random_incidents_active:
                    random_thread = threading.Thread(
                        target=self.simulate_random_incidents
                    )
                    random_thread.daemon = True
                    random_thread.start()
                    print("Simulación de incidencias aleatorias activada")
                else:
                    print("Simulación de incidencias aleatorias desactivada")
            elif cmd == 'q':
                self.running = False
                break

    def status_reporter(self):
        """Reportar estado periódicamente"""
        while self.running:
            self.publish_status()
            time.sleep(1)

    def run(self):
        """Iniciar sensor"""
        # Iniciar threads
        reporter_thread = threading.Thread(target=self.status_reporter)
        reporter_thread.daemon = True
        reporter_thread.start()
        
        try:
            self.keyboard_control()
        except KeyboardInterrupt:
            logger.info("Sensor detenido por usuario")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpieza al cerrar"""
        self.running = False
        self.kafka.close()
        logger.info("Sensor detenido")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='EC_S: Sensor de Taxi')
    
    parser.add_argument('taxi_id', type=int, help='ID del taxi')
    parser.add_argument('kafka_ip', help='IP del broker Kafka')
    parser.add_argument('kafka_port', type=int, help='Puerto del broker Kafka')
    
    args = parser.parse_args()
    
    kafka_url = f"{args.kafka_ip}:{args.kafka_port}"
    sensor = TaxiSensor(args.taxi_id, kafka_url)
    sensor.run()