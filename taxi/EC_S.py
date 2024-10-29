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
        
        self.incidents = [
            "Obstáculo detectado",
            "Semáforo en rojo",
            "Peatón cruzando",
            "Vehículo cercano",
        ]
        self.current_incident = 0
        self.last_report_time = time.time()
        self.incident_duration = 0
        self.incident_count = 0

    def publish_status(self):
        message = create_message('sensor_status', {
            'taxi_id': self.taxi_id,
            'status': self.status,
            'reason': self.reason,
            'incident_count': self.incident_count,
            'current_duration': self.incident_duration if self.status == "KO" else 0
        })
        self.kafka.publish(TOPICS['SENSOR_DATA'], message)

    def toggle_status(self):
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
        incident = self.incidents[self.current_incident]
        self.current_incident = (self.current_incident + 1) % len(self.incidents)
        return incident

    def simulate_random_incidents(self):
        while self.running:
            time.sleep(random.uniform(30, 120))  # Entre 30s y 2min
            if random.random() < 0.3:  # 30% de probabilidad
                self.toggle_status()
                if self.status == "KO":
                    threading.Timer(
                        random.uniform(5, 15),
                        self.toggle_status
                    ).start()

    def keyboard_control(self):
        random_incidents_active = False
        random_thread = None

        while self.running:
            cmd = input("t: Toggle (OK/KO), r: Toggle random incidents, q: Quit\n").lower()
            
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
                    print("Incidencias aleatorias activadas")
                else:
                    print("Incidencias aleatorias desactivadas")
            elif cmd == 'q':
                self.running = False
                break

    def status_reporter(self):
        while self.running:
            self.publish_status()
            time.sleep(1)

    def run(self):
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
        self.running = False
        self.kafka.close()
        logger.info("Sensor detenido")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python EC_S.py <taxi_id> <kafka_ip> <kafka_port>")
        sys.exit(1)

    taxi_id = int(sys.argv[1])
    kafka_ip = sys.argv[2]
    kafka_port = int(sys.argv[3])

    kafka_url = f"{kafka_ip}:{kafka_port}"
    sensor = TaxiSensor(taxi_id, kafka_url)
    sensor.run()
