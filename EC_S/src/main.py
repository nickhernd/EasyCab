# EC_S/src/main.py
import sys
import socket
import time
import tkinter as tk
from tkinter import ttk
import threading

class SensorSystem:
    def __init__(self, de_ip: str, de_port: int):
        self.de_ip = de_ip
        self.de_port = de_port
        self.running = True
        self.current_status = "OK"
        self.socket = None
        self.connected = False

        # Inicializar la interfaz gráfica
        self.setup_gui()
        
        # Iniciar la conexión con Digital Engine
        self.connect_to_de()

    def setup_gui(self):
        """Configurar interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title("EC_S (Sensor System)")
        self.root.geometry("400x300")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Estado de conexión
        self.connection_label = ttk.Label(main_frame, text="Estado: Desconectado")
        self.connection_label.grid(row=0, column=0, columnspan=2, pady=5)

        # Estado actual del sensor
        self.status_label = ttk.Label(main_frame, text="Estado actual: OK")
        self.status_label.grid(row=1, column=0, columnspan=2, pady=5)

        # Botones de control
        ttk.Label(main_frame, text="Control de Sensores:").grid(row=2, column=0, columnspan=2, pady=10)
        
        # Botón para simular obstáculo
        self.obstacle_button = ttk.Button(
            main_frame,
            text="Simular Obstáculo (KO)",
            command=self.toggle_obstacle
        )
        self.obstacle_button.grid(row=3, column=0, columnspan=2, pady=5)

        # Log de eventos
        ttk.Label(main_frame, text="Log de eventos:").grid(row=4, column=0, columnspan=2, pady=5)
        
        # Frame para el log con scrollbar
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_frame, height=10, width=40)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Teclas de atajo
        self.root.bind('<space>', lambda e: self.toggle_obstacle())

    def log_event(self, message: str):
        """Agregar mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"{timestamp}: {message}\n")
        self.log_text.see(tk.END)

    def connect_to_de(self):
        """Conectar con Digital Engine"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.de_ip, self.de_port))
            self.connected = True
            self.connection_label.config(text="Estado: Conectado a Digital Engine")
            self.log_event(f"Conectado a Digital Engine en {self.de_ip}:{self.de_port}")
            
            # Iniciar thread para envío continuo de datos
            self.sender_thread = threading.Thread(target=self.send_sensor_data)
            self.sender_thread.daemon = True
            self.sender_thread.start()
        except Exception as e:
            self.log_event(f"Error de conexión: {e}")
            self.connection_label.config(text="Estado: Error de conexión")
            self.root.after(5000, self.connect_to_de)  # Reintentar cada 5 segundos

    def toggle_obstacle(self):
        """Cambiar estado del sensor entre OK y KO"""
        if self.current_status == "OK":
            self.current_status = "KO"
            self.status_label.config(text="Estado actual: KO (Obstáculo detectado)")
            self.obstacle_button.config(text="Resolver Obstáculo (OK)")
            self.log_event("Obstáculo detectado - Enviando KO")
        else:
            self.current_status = "OK"
            self.status_label.config(text="Estado actual: OK (Vía libre)")
            self.obstacle_button.config(text="Simular Obstáculo (KO)")
            self.log_event("Obstáculo resuelto - Enviando OK")

    def send_sensor_data(self):
        """Thread para envío continuo de datos de sensores"""
        while self.running:
            if self.connected:
                try:
                    self.socket.send(self.current_status.encode('utf-8'))
                    time.sleep(1)  # Enviar actualización cada segundo
                except Exception as e:
                    self.log_event(f"Error enviando datos: {e}")
                    self.connected = False
                    self.connection_label.config(text="Estado: Desconectado")
                    self.socket.close()
                    self.root.after(0, self.connect_to_de)
                    break

    def run(self):
        """Iniciar el sistema de sensores"""
        self.log_event("Sistema de sensores iniciado")
        self.log_event("Presiona ESPACIO o el botón para simular obstáculos")
        self.root.mainloop()
        self.running = False

    def cleanup(self):
        """Limpieza al cerrar"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python main.py <ip_digital_engine> <puerto_digital_engine>")
        print("Ejemplo: python main.py 127.0.0.1 5001")
        sys.exit(1)

    try:
        de_ip = sys.argv[1]
        de_port = int(sys.argv[2])

        sensor = SensorSystem(de_ip, de_port)
        
        # Manejar cierre limpio
        def on_closing():
            sensor.cleanup()
            sensor.root.destroy()
        
        sensor.root.protocol("WM_DELETE_WINDOW", on_closing)
        sensor.run()

    except ValueError:
        print("Error: El puerto debe ser un número entero")
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar el sistema de sensores: {e}")
        sys.exit(1)