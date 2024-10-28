import argparse
import json
import os
import sys
import logging
import socket
import time
import threading
from typing import Dict
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('easycab.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EasyCabGUI:
    def __init__(self, launcher):
        self.launcher = launcher
        self.window = tk.Tk()
        self.window.title("EasyCab Launcher")
        self.window.geometry("600x400")
        self.create_widgets()

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configuración IP
        ttk.Label(main_frame, text="Configuración de Red").grid(row=0, column=0, columnspan=2, pady=10)
        
        ttk.Label(main_frame, text="IP Central:").grid(row=1, column=0)
        self.central_ip = ttk.Entry(main_frame)
        self.central_ip.insert(0, self.launcher.config['central_ip'])
        self.central_ip.grid(row=1, column=1)

        ttk.Label(main_frame, text="IP Kafka:").grid(row=2, column=0)
        self.kafka_ip = ttk.Entry(main_frame)
        self.kafka_ip.insert(0, self.launcher.config['kafka_ip'])
        self.kafka_ip.grid(row=2, column=1)

        # Tipo de nodo
        ttk.Label(main_frame, text="Tipo de Nodo:").grid(row=3, column=0, pady=10)
        self.node_type = ttk.Combobox(main_frame, values=['central', 'taxi', 'customer'])
        self.node_type.grid(row=3, column=1)
        self.node_type.set('central')

        # ID para taxi/customer
        ttk.Label(main_frame, text="ID (para taxi/customer):").grid(row=4, column=0)
        self.node_id = ttk.Entry(main_frame)
        self.node_id.insert(0, "1")
        self.node_id.grid(row=4, column=1)

        # Botones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Verificar Conexión", 
                  command=self.check_connectivity).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Iniciar", 
                  command=self.start_node).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Detener", 
                  command=self.stop_node).grid(row=0, column=2, padx=5)

        # Log viewer
        ttk.Label(main_frame, text="Logs:").grid(row=6, column=0, columnspan=2)
        self.log_text = tk.Text(main_frame, height=10, width=60)
        self.log_text.grid(row=7, column=0, columnspan=2)
        
        # Scrollbar para logs
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=7, column=2, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def update_log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def check_connectivity(self):
        central_ip = self.central_ip.get()
        kafka_ip = self.kafka_ip.get()
        
        self.update_log("Verificando conectividad...")
        
        # Verificar Central
        try:
            socket.create_connection((central_ip, 50051), timeout=2)
            self.update_log(f"✅ Central alcanzable en {central_ip}:50051")
        except:
            self.update_log(f"❌ No se puede alcanzar Central en {central_ip}:50051")

        # Verificar Kafka
        try:
            socket.create_connection((kafka_ip, 9092), timeout=2)
            self.update_log(f"✅ Kafka alcanzable en {kafka_ip}:9092")
        except:
            self.update_log(f"❌ No se puede alcanzar Kafka en {kafka_ip}:9092")

    def start_node(self):
        node_type = self.node_type.get()
        node_id = self.node_id.get()
        
        # Guardar configuración
        self.launcher.config['central_ip'] = self.central_ip.get()
        self.launcher.config['kafka_ip'] = self.kafka_ip.get()
        self.launcher.save_config()

        # Configurar variables de entorno
        os.environ['CENTRAL_HOST'] = self.launcher.config['central_ip']
        os.environ['KAFKA_HOST'] = self.launcher.config['kafka_ip']

        try:
            if node_type == 'central':
                threading.Thread(target=self.launcher.start_central,
                              args=(self.update_log,)).start()
            elif node_type == 'taxi':
                threading.Thread(target=self.launcher.start_taxi,
                              args=(node_id, self.update_log)).start()
            else:
                threading.Thread(target=self.launcher.start_customer,
                              args=(node_id, self.update_log)).start()
                
            self.update_log(f"Iniciando {node_type}...")
            
        except Exception as e:
            self.update_log(f"Error iniciando nodo: {e}")
            messagebox.showerror("Error", f"Error iniciando nodo: {e}")

    def stop_node(self):
        self.launcher.stop_node()
        self.update_log("Deteniendo nodo...")

    def run(self):
        self.window.mainloop()

class EasyCabLauncher:
    def __init__(self):
        self.config = self.load_config()
        self.process = None
        
    def load_config(self) -> Dict:
        config_file = 'easycab_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        return {
            'central_ip': 'localhost',
            'kafka_ip': 'localhost',
            'central_port': 50051,
            'kafka_port': 9092
        }
        
    def save_config(self):
        with open('easycab_config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

    def start_central(self, log_callback):
        try:
            from central.EC_Central import CentralServer
            server = CentralServer()
            log_callback("Servidor central iniciado")
            server.run()
        except Exception as e:
            log_callback(f"Error iniciando central: {e}")

    def start_taxi(self, taxi_id, log_callback):
        try:
            from taxi.EC_DE import DigitalEngine
            from taxi.EC_S import TaxiSensor
            
            # Iniciar Digital Engine
            taxi = DigitalEngine(int(taxi_id), 5000 + int(taxi_id))
            log_callback(f"Digital Engine del taxi {taxi_id} iniciado")
            
            # Iniciar Sensor
            sensor = TaxiSensor(5000 + int(taxi_id))
            log_callback(f"Sensor del taxi {taxi_id} iniciado")
            
            threading.Thread(target=sensor.run).start()
            taxi.start()
            
        except Exception as e:
            log_callback(f"Error iniciando taxi: {e}")

    def start_customer(self, customer_id, log_callback):
        try:
            from customer.EC_Customer import Customer
            customer = Customer(customer_id, 'data/EC_Requests.json')
            log_callback(f"Cliente {customer_id} iniciado")
            customer.run()
        except Exception as e:
            log_callback(f"Error iniciando cliente: {e}")

    def stop_node(self):
        if self.process:
            self.process.terminate()
            self.process = None

def main():
    launcher = EasyCabLauncher()
    
    if len(sys.argv) > 1:
        # Modo línea de comandos
        parser = argparse.ArgumentParser(description='EasyCab Launcher')
        parser.add_argument('node_type', choices=['central', 'taxi', 'customer'])
        parser.add_argument('--central-ip', help='IP del servidor central')
        parser.add_argument('--kafka-ip', help='IP del servidor Kafka')
        parser.add_argument('--id', help='ID para taxi o customer')
        args = parser.parse_args()

        if args.central_ip:
            launcher.config['central_ip'] = args.central_ip
        if args.kafka_ip:
            launcher.config['kafka_ip'] = args.kafka_ip
        launcher.save_config()

        if args.node_type == 'central':
            launcher.start_central(print)
        elif args.node_type == 'taxi':
            launcher.start_taxi(args.id or '1', print)
        else:
            launcher.start_customer(args.id or 'customer1', print)
    else:
        # Modo GUI
        gui = EasyCabGUI(launcher)
        gui.run()

if __name__ == "__main__":
    main()