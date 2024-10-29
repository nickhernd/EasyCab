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
        with open('config.env', 'r') as f:
            return json.load(f)

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
        subprocess.run(['docker-compose', 'down'], check=True)
        
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