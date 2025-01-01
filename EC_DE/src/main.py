# EC_DE/src/main.py
import sys
import socket
import json
import threading
import tkinter as tk
from tkinter import ttk
import time
from kafka import KafkaConsumer, KafkaProducer

class DigitalEngine:
    def __init__(self, central_ip: str, central_port: int, taxi_id: int):
        self.central_ip = central_ip
        self.central_port = central_port
        self.taxi_id = taxi_id
        self.token = None
        self.position = (1, 1)  # Posición inicial
        self.state = "RED"  # RED=parado, GREEN=en movimiento
        self.destination = None
        self.running = True
        self.sensor_data = "OK"
        
        # Conectar con Central
        self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.central_socket.connect((central_ip, central_port))
            print(f"Conectado a Central en {central_ip}:{central_port}")
        except Exception as e:
            print(f"Error conectando a Central: {e}")
            sys.exit(1)

        # Inicializar la interfaz gráfica
        self.setup_gui()
        
        # Inicializar threads
        self.start_threads()

    def setup_gui(self):
        """Configurar interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title(f"Digital Engine - Taxi {self.taxi_id}")
        self.root.geometry("600x400")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Estado del taxi
        ttk.Label(main_frame, text="Estado del Taxi:").grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(main_frame, text="Iniciando...")
        self.status_label.grid(row=0, column=1, sticky=tk.W)

        # Posición actual
        ttk.Label(main_frame, text="Posición:").grid(row=1, column=0, sticky=tk.W)
        self.position_label = ttk.Label(main_frame, text="(1,1)")
        self.position_label.grid(row=1, column=1, sticky=tk.W)

        # Estado del sensor
        ttk.Label(main_frame, text="Sensor:").grid(row=2, column=0, sticky=tk.W)
        self.sensor_label = ttk.Label(main_frame, text="OK")
        self.sensor_label.grid(row=2, column=1, sticky=tk.W)

        # Log de eventos
        ttk.Label(main_frame, text="Log de eventos:").grid(row=3, column=0, sticky=tk.W)
        self.log_text = tk.Text(main_frame, height=10, width=50)
        self.log_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Scrollbar para el log
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=4, column=2, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set

    def log_event(self, message: str):
        """Agregar mensaje al log"""
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')}: {message}\n")
        self.log_text.see(tk.END)

    def start_threads(self):
        """Iniciar threads para comunicación"""
        # Thread para recibir mensajes de Central
        self.central_thread = threading.Thread(target=self.receive_central_messages)
        self.central_thread.daemon = True
        self.central_thread.start()

        # Thread para recibir datos de sensores
        self.sensor_thread = threading.Thread(target=self.receive_sensor_data)
        self.sensor_thread.daemon = True
        self.sensor_thread.start()

        # Thread para movimiento del taxi
        self.movement_thread = threading.Thread(target=self.movement_loop)
        self.movement_thread.daemon = True
        self.movement_thread.start()

    def authenticate(self):
        """Autenticar con Central"""
        auth_message = {
            "type": "AUTH",
            "taxi_id": self.taxi_id
        }
        self.send_to_central(auth_message)
        response = self.receive_from_central()
        
        if response.get("status") == "OK":
            self.token = response.get("token")
            self.log_event("Autenticación exitosa")
            return True
        else:
            self.log_event("Error en autenticación")
            return False

    def send_to_central(self, message: dict):
        """Enviar mensaje a Central"""
        try:
            self.central_socket.send(json.dumps(message).encode('utf-8'))
        except Exception as e:
            self.log_event(f"Error enviando mensaje a Central: {e}")

    def receive_from_central(self) -> dict:
        """Recibir mensaje de Central"""
        try:
            data = self.central_socket.recv(4096)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.log_event(f"Error recibiendo mensaje de Central: {e}")
            return {}

    def receive_central_messages(self):
        """Thread para recibir mensajes de Central"""
        while self.running:
            try:
                response = self.receive_from_central()
                if response:
                    self.process_central_message(response)
            except Exception as e:
                self.log_event(f"Error en comunicación con Central: {e}")
                time.sleep(1)

    def process_central_message(self, message: dict):
        """Procesar mensajes recibidos de Central"""
        message_type = message.get("type")
        
        if message_type == "MOVE":
            self.destination = tuple(message.get("destination"))
            self.state = "GREEN"
            self.log_event(f"Nuevo destino: {self.destination}")
        elif message_type == "STOP":
            self.state = "RED"
            self.log_event("Taxi detenido por Central")
        elif message_type == "RESUME":
            self.state = "GREEN"
            self.log_event("Taxi reanudado por Central")

    def receive_sensor_data(self):
        """Thread para recibir datos de sensores"""
        sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sensor_socket.bind(('0.0.0.0', 0))  # Puerto aleatorio
        sensor_socket.listen(1)
        
        self.log_event(f"Esperando conexión de sensores en puerto {sensor_socket.getsockname()[1]}")
        
        while self.running:
            try:
                client_socket, _ = sensor_socket.accept()
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    self.sensor_data = data.decode('utf-8')
                    self.update_sensor_status()
            except Exception as e:
                self.log_event(f"Error en comunicación con sensores: {e}")
                time.sleep(1)

    def update_sensor_status(self):
        """Actualizar estado del sensor en la GUI"""
        self.sensor_label.config(text=self.sensor_data)
        if self.sensor_data == "KO":
            self.state = "RED"
            self.log_event("Taxi detenido por sensor")

    def movement_loop(self):
        """Thread para el movimiento del taxi"""
        while self.running:
            if self.state == "GREEN" and self.destination and self.sensor_data == "OK":
                new_pos = self.calculate_next_position()
                if new_pos != self.position:
                    self.position = new_pos
                    self.update_position()
                    self.send_position_update()
            time.sleep(1)

    def calculate_next_position(self) -> tuple:
        """Calcular siguiente posición hacia el destino"""
        if not self.destination:
            return self.position
            
        x, y = self.position
        dest_x, dest_y = self.destination

        # Mover un paso hacia el destino
        if x < dest_x:
            x += 1
        elif x > dest_x:
            x -= 1
            
        if y < dest_y:
            y += 1
        elif y > dest_y:
            y -= 1

        # Considerar el mapa esférico (20x20)
        x = (x - 1) % 20 + 1
        y = (y - 1) % 20 + 1
        
        return (x, y)

    def update_position(self):
        """Actualizar posición en la GUI"""
        self.position_label.config(text=str(self.position))
        self.log_event(f"Nueva posición: {self.position}")

    def send_position_update(self):
        """Enviar actualización de posición a Central"""
        update_message = {
            "type": "POSITION",
            "taxi_id": self.taxi_id,
            "token": self.token,
            "position": self.position,
            "state": self.state
        }
        self.send_to_central(update_message)

    def run(self):
        """Iniciar el Digital Engine"""
        if self.authenticate():
            self.log_event("Digital Engine iniciado")
            self.status_label.config(text=f"Operativo - Token: {self.token}")
            self.root.mainloop()
        else:
            self.log_event("No se pudo autenticar con Central")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python main.py <ip_central> <puerto_central> <id_taxi>")
        print("Ejemplo: python main.py 127.0.0.1 5000 1")
        sys.exit(1)

    try:
        central_ip = sys.argv[1]
        central_port = int(sys.argv[2])
        taxi_id = int(sys.argv[3])

        digital_engine = DigitalEngine(central_ip, central_port, taxi_id)
        digital_engine.run()
    except ValueError:
        print("Error: El puerto y el ID del taxi deben ser números enteros")
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar Digital Engine: {e}")
        sys.exit(1)