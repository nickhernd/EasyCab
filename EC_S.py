import socket
import json
import time
import random
import threading
import os

class ECSensors:
    def __init__(self, taxi_id):
        self.taxi_id = taxi_id
        self.digital_engine_host = os.environ.get('DIGITAL_ENGINE_HOST', 'localhost')
        self.digital_engine_port = int(os.environ.get('DIGITAL_ENGINE_PORT', 5000))
        self.is_running = True
        
        # Estado de los sensores
        self.sensors = {
            'lidar': {'status': 'OK', 'range': 100},
            'camera': {'status': 'OK', 'visibility': 100},
            'proximity': {'status': 'OK', 'distance': 100},
            'speed': {'status': 'OK', 'value': 0},
            'obstacle_detector': {'status': 'OK', 'detected': False}
        }
        
        # Tipos de obstáculos que pueden ser detectados
        self.obstacle_types = [
            'pedestrian',
            'traffic_light',
            'vehicle',
            'construction',
            'road_block'
        ]
        
        # Conexión con Digital Engine
        self.connect_to_digital_engine()

    def connect_to_digital_engine(self):
        """Establece conexión con el Digital Engine"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.digital_engine_host, self.digital_engine_port))
            print(f"Connected to Digital Engine at {self.digital_engine_host}:{self.digital_engine_port}")
        except Exception as e:
            print(f"Error connecting to Digital Engine: {e}")
            raise

    def simulate_sensor_reading(self):
        """Simula lecturas de los sensores"""
        # Simular cambios aleatorios en los sensores
        for sensor in self.sensors.values():
            if random.random() < 0.05:  # 5% de probabilidad de variación
                sensor['status'] = random.choice(['OK', 'WARNING'])

        # Simular detección de obstáculos
        if random.random() < 0.1:  # 10% de probabilidad de obstáculo
            self.sensors['obstacle_detector']['detected'] = True
            obstacle = {
                'type': random.choice(self.obstacle_types),
                'distance': random.uniform(1, 20),
                'severity': random.choice(['LOW', 'MEDIUM', 'HIGH'])
            }
            return ('OBSTACLE', obstacle)
        
        self.sensors['obstacle_detector']['detected'] = False
        return ('OK', None)

    def send_sensor_data(self, status, obstacle=None):
        """Envía datos de los sensores al Digital Engine"""
        data = {
            'taxi_id': self.taxi_id,
            'timestamp': time.time(),
            'sensors': self.sensors,
            'status': status
        }
        
        if obstacle:
            data['obstacle'] = obstacle
        
        try:
            self.socket.send(json.dumps(data).encode('utf-8'))
            print(f"Sent sensor data: {data}")
        except Exception as e:
            print(f"Error sending sensor data: {e}")
            self.reconnect()

    def reconnect(self):
        """Intenta reconectarse al Digital Engine"""
        try:
            self.socket.close()
        except:
            pass
        
        retries = 3
        for i in range(retries):
            try:
                time.sleep(2)
                self.connect_to_digital_engine()
                print("Reconnected to Digital Engine")
                return
            except Exception as e:
                print(f"Reconnection attempt {i+1} failed: {e}")
        
        print("Failed to reconnect after multiple attempts")
        self.is_running = False

    def simulate_emergency(self):
        """Simula una situación de emergencia"""
        emergency_types = ['system_failure', 'sensor_malfunction', 'emergency_stop']
        return {
            'type': random.choice(emergency_types),
            'severity': 'HIGH',
            'requires_immediate_stop': True
        }

    def manual_control(self):
        """Permite control manual para simular eventos"""
        while self.is_running:
            command = input("Enter command (o=obstacle, e=emergency, q=quit): ").lower()
            if command == 'o':
                self.send_sensor_data('OBSTACLE', {
                    'type': random.choice(self.obstacle_types),
                    'distance': random.uniform(1, 20),
                    'severity': 'HIGH'
                })
            elif command == 'e':
                self.send_sensor_data('EMERGENCY', self.simulate_emergency())
            elif command == 'q':
                self.is_running = False

    def run(self):
        """Bucle principal del sistema de sensores"""
        # Iniciar thread para control manual
        control_thread = threading.Thread(target=self.manual_control)
        control_thread.daemon = True
        control_thread.start()

        print(f"Sensor system running for taxi {self.taxi_id}")
        while self.is_running:
            try:
                status, obstacle = self.simulate_sensor_reading()
                self.send_sensor_data(status, obstacle)
                time.sleep(1)  # Actualizar cada segundo
            except Exception as e:
                print(f"Error in sensor system: {e}")
                time.sleep(1)

if __name__ == "__main__":
    taxi_id = os.environ.get('TAXI_ID', '1')
    sensors = ECSensors(taxi_id)
    try:
        sensors.run()
    except KeyboardInterrupt:
        print("Shutting down sensor system...")
        sensors.is_running = False