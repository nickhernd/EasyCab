import subprocess
import time
import os
import signal
import sys

class LocalDeployer:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_central(self):
        """Inicia el servidor central"""
        cmd = [
            "python", "EC_Central.py",
            "8000", "localhost:9092",
            "localhost", "root", "password"
        ]
        self.processes['central'] = subprocess.Popen(cmd)
        time.sleep(2)  # Esperar a que inicie
        
    def start_taxi(self, taxi_id, port):
        """Inicia un taxi y sus sensores"""
        # Digital Engine
        de_cmd = [
            "python", "EC_DE.py",
            str(port), "localhost:9092",
            str(port+1), str(taxi_id)
        ]
        self.processes[f'taxi_{taxi_id}_de'] = subprocess.Popen(de_cmd)
        
        # Sensores
        sensor_cmd = [
            "python", "EC_S.py",
            f"localhost:{port+1}"
        ]
        self.processes[f'taxi_{taxi_id}_sensor'] = subprocess.Popen(sensor_cmd)
        
    def start_customer(self, customer_id):
        """Inicia un cliente"""
        cmd = [
            "python", "EC_Customer.py",
            "localhost:9092", str(customer_id)
        ]
        self.processes[f'customer_{customer_id}'] = subprocess.Popen(cmd)
        
    def start_gui(self):
        """Inicia la interfaz gráfica"""
        cmd = ["python", "EC_gui.py"]
        self.processes['gui'] = subprocess.Popen(cmd)
        
    def deploy(self, num_taxis=2, num_customers=2):
        """Despliega todo el sistema"""
        try:
            print("Iniciando despliegue local...")
            
            # Iniciar central
            print("Iniciando Central...")
            self.start_central()
            
            # Iniciar taxis
            base_port = 5000
            for i in range(num_taxis):
                print(f"Iniciando Taxi {i+1}...")
                self.start_taxi(i+1, base_port + (i*2))
                time.sleep(1)
            
            # Iniciar clientes
            for i in range(num_customers):
                print(f"Iniciando Cliente {i+1}...")
                self.start_customer(i+1)
                time.sleep(1)
            
            # Iniciar GUI
            print("Iniciando GUI...")
            self.start_gui()
            
            print("\nSistema desplegado completamente")
            print("\nPresiona Ctrl+C para detener todo el sistema")
            
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.shutdown()
            
    def shutdown(self):
        """Detiene todos los procesos"""
        print("\nDeteniendo el sistema...")
        for name, process in self.processes.items():
            print(f"Deteniendo {name}...")
            process.terminate()
        
        time.sleep(2)
        for name, process in self.processes.items():
            if process.poll() is None:
                process.kill()
        
        self.running = False

if __name__ == "__main__":
    deployer = LocalDeployer()
    deployer.deploy()