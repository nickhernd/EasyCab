import socket
import logging
import sys
import time
import threading
import tkinter as tk
from confluent_kafka import Producer
from kafka_utils import send_kafka_message, create_kafka_producer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECS:
    def __init__(self, kafka_config, topic, de_host, de_port):
        self.kafka_producer = create_kafka_producer(kafka_config['bootstrap.servers'])
        self.topic = topic
        self.status = 'OK'
        self.de_host = de_host
        self.de_port = de_port
        self.root = None
        self.status_label = None

    def send_sensor_data(self):
        try:
            while True:
                status = input("Ingrese el estado del sensor (o: OK, s: Semáforo, p: Peatón, x: Avería): ")
                if status in ['o', 's', 'p', 'x']:
                    self.status = status
                    print(f"Enviando estado del sensor: {self.status}")
                    send_kafka_message(self.kafka_producer, self.topic, {
                        'type': 'SENSOR_UPDATE',
                        'status': self.status
                    })
                    self.send_to_de(self.status)
                    time.sleep(1)
                else:
                    print("Entrada no válida. Intente de nuevo.")
        except Exception as e:
            logger.error(f"Error in sensor communication: {str(e)}")

    def send_to_de(self, status):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.de_host, self.de_port))
                s.sendall(status.encode('utf-8'))
                response = s.recv(1024)
                logger.info(f"Response from DE: {response.decode('utf-8')}")
        except Exception as e:
            logger.error(f"Error sending data to DE: {str(e)}")

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("EC_S Sensor Simulator")
        
        tk.Button(self.root, text="Red Light (s)", command=lambda: self.update_status('s')).pack()
        tk.Button(self.root, text="Pedestrian (p)", command=lambda: self.update_status('p')).pack()
        tk.Button(self.root, text="Flat Tire (x)", command=lambda: self.update_status('x')).pack()
        tk.Button(self.root, text="OK (o)", command=lambda: self.update_status('o')).pack()
        
        self.status_label = tk.Label(self.root, text=f"Current Status: {self.status}")
        self.status_label.pack()

        self.root.mainloop()

    def update_status(self, new_status):
        self.status = new_status
        if self.status_label:
            self.status_label.config(text=f"Current Status: {self.status}")
        logger.info(f"Status updated to: {self.status}")

    def start(self):
        sender_thread = threading.Thread(target=self.send_sensor_data)
        sender_thread.start()
        self.create_gui()
        logger.info("ECS started")

    def close(self):
        if self.root:
            self.root.quit()
        self.kafka_producer.flush()

if __name__ == "__main__":
    kafka_config = {
        'bootstrap.servers': 'localhost:9092'
    }
    de_host = 'localhost'  # o la IP correcta del host de DE
    de_port = 8010  
    sensors = ECS(kafka_config, 'sensor_updates', de_host, de_port)
    try:
        sensors.start()
    except KeyboardInterrupt:
        print("Sensor simulation terminated.")
    finally:
        sensors.close()
