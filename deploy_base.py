#!/usr/bin/env python3
import os
import socket
import subprocess
import json
from abc import ABC, abstractmethod

class BaseDeployer(ABC):
    def __init__(self):
        self.current_ip = self.get_current_ip()
        self.config = self.load_config()
        
    def get_current_ip(self):
        """Obtiene la IP de la máquina actual"""
        try:
            # Prioriza la interfaz en la red 192.168.56.x
            interfaces = socket.getaddrinfo(socket.gethostname(), None)
            for info in interfaces:
                if info[4][0].startswith('192.168.56.'):
                    return info[4][0]
            return socket.gethostbyname(socket.gethostname())
        except:
            return '127.0.0.1'

    def load_config(self):
        """Carga la configuración desde config.env"""
        config_file = 'config.env'
        
        if not os.path.exists(config_file):
            print(f"Error: No se encuentra el archivo {config_file}")
            print("Creando archivo de configuración por defecto...")
            self.create_default_config()
            
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: El archivo {config_file} no tiene un formato JSON válido")
            print("Creando archivo de configuración por defecto...")
            self.create_default_config()
            with open(config_file, 'r') as f:
                return json.load(f)

    def create_default_config(self):
        """Crea un archivo de configuración por defecto"""
        default_config = {
            "nodes": {
                "kafka": {
                    "ip": "192.168.56.123",
                    "ports": [2181, 9092],
                    "services": ["zookeeper", "kafka", "customer"]
                },
                "central": {
                    "ip": "192.168.56.114",
                    "ports": [50051],
                    "services": ["central"]
                },
                "taxi": {
                    "ip": "10.0.2.19",
                    "ports": [50052],
                    "services": ["taxi", "sensors"]
                }
            },
            "kafka": {
                "bootstrap_servers": "192.168.56.123:9092",
                "topics": {
                    "taxi_positions": "taxi_positions",
                    "customer_requests": "customer_requests",
                    "taxi_status": "taxi_status"
                }
            }
        }
        
        with open('config.env', 'w') as f:
            json.dump(default_config, f, indent=4)
        print("Archivo de configuración creado correctamente")

    def check_docker(self):
        """Verifica si Docker está instalado"""
        try:
            subprocess.run(['docker', '--version'], check=True, stdout=subprocess.PIPE)
            return True
        except:
            return False

    @abstractmethod
    def validate_environment(self):
        """Valida el entorno específico para cada rol"""
        pass

    @abstractmethod
    def deploy(self):
        """Implementa el despliegue específico"""
        pass

    def stop_services(self):
        """Para todos los servicios Docker"""
        try:
            subprocess.run(['docker-compose', 'down'], check=True)
        except subprocess.CalledProcessError:
            print("Advertencia: No se pudieron detener los servicios anteriores")
        
    def check_ports(self, ports):
        """Verifica que los puertos necesarios estén disponibles"""
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                print(f"Error: Puerto {port} ya está en uso")
                return False
        return True