import socket
import json
import time
import logging
import sys
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaxiSensor:
    def __init__(self, port: int):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.status = "OK"

    def connect(self):
        """Conectar con el Digital Engine"""
        try:
            self.socket.connect(('localhost', self.port))
            logger.info("Sensor conectado al Digital Engine")
            return True
        except Exception as e:
            logger.error(f"Error conectando con Digital Engine: {e}")
            return False

    def send_status(self):
        """Enviar estado actual al Digital Engine"""
        message = {
            'status': self.status,
            'timestamp': time.time()
        }
        if self.status == 'KO':
            message['reason'] = 'Obstáculo detectado'
            
        try:
            self.socket.send(json.dumps(message).encode())
        except Exception as e:
            logger.error(f"Error enviando estado: {e}")
            self.running = False

    def toggle_status(self):
        """Cambiar estado del sensor"""
        self.status = 'KO' if self.status == 'OK' else 'OK'
        logger.info(f"Estado del sensor cambiado a: {self.status}")

    def keyboard_control(self):
        """Escuchar entrada de teclado para cambiar estado"""
        logger.info("Presiona 't' para cambiar el estado del sensor, 'q' para salir")
        while self.running:
            try:
                key = input().lower()
                if key == 't':
                    self.toggle_status()
                elif key == 'q':
                    self.running = False
            except:
                break

    def run(self):
        """Ejecutar el sensor"""
        if not self.connect():
            return

        # Iniciar thread para control por teclado
        keyboard_thread = threading.Thread(target=self.keyboard_control)
        keyboard_thread.daemon = True
        keyboard_thread.start()

        # Bucle principal
        try:
            while self.running:
                self.send_status()
                time.sleep(1)
        finally:
            self.socket.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Puerto del Digital Engine")
    args = parser.parse_args()

    sensor = TaxiSensor(args.port)
    sensor.run()