#!/usr/bin/env python3
import os
import sys
import subprocess
import socket
import json
from typing import Dict, List
import time

class EasyCabDeployer:
    def __init__(self):
        self.config = self.load_config()
        self.current_ip = self.get_current_ip()
        self.role = self.determine_role()
        
    def load_config(self) -> Dict:
        """Carga la configuración desde config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Error: config.json no encontrado")
            sys.exit(1)
    
    def get_current_ip(self) -> str:
        """Obtiene la IP de la máquina actual"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def determine_role(self) -> str:
        """Determina el rol basado en la IP actual"""
        for role, config in self.config['nodes'].items():
            if config['ip'] == self.current_ip:
                return role
        return 'unknown'

    def check_docker(self) -> bool:
        """Verifica si Docker está instalado y funcionando"""
        try:
            subprocess.run(['docker', '--version'], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def install_docker(self):
        """Instala Docker si no está presente"""
        if os.name == 'nt':  # Windows
            print("Por favor, instala Docker Desktop manualmente en Windows")
            sys.exit(1)
        else:  # Linux
            commands = [
                'curl -fsSL https://get.docker.com -o get-docker.sh',
                'sudo sh get-docker.sh',
                'sudo usermod -aG docker $USER'
            ]
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)

    def check_connectivity(self) -> bool:
        """Verifica la conectividad con todos los nodos"""
        for node, config in self.config['nodes'].items():
            ip = config['ip']
            if ip != self.current_ip:
                print(f"Verificando conectividad con {node} ({ip})...")
                cmd = 'ping -n 3' if os.name == 'nt' else 'ping -c 3'
                try:
                    subprocess.run(f'{cmd} {ip}', shell=True, check=True)
                except subprocess.CalledProcessError:
                    print(f"Error: No se puede conectar con {node}")
                    return False
        return True

    def deploy_services(self):
        """Despliega los servicios según el rol"""
        if not self.role:
            print("Error: No se pudo determinar el rol de esta máquina")
            return

        compose_file = f'docker-compose.{self.role}.yml'
        if not os.path.exists(compose_file):
            print(f"Error: No se encontró {compose_file}")
            return

        commands = [
            f'docker-compose -f {compose_file} down',
            'docker system prune -f',
            f'docker-compose -f {compose_file} build',
            f'docker-compose -f {compose_file} up -d'
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error ejecutando: {cmd}")
                print(e)
                return False

        return True

    def verify_deployment(self) -> bool:
        """Verifica que los servicios están funcionando correctamente"""
        time.sleep(5)  # Esperar a que los servicios inicien
        
        def check_port(port: int) -> bool:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0

        ports_to_check = self.config['nodes'][self.role]['ports']
        for port in ports_to_check:
            if not check_port(port):
                print(f"Error: Puerto {port} no está abierto")
                return False
                
        print("Verificación de puertos completada con éxito")
        return True

    def run(self):
        """Ejecuta el proceso de despliegue completo"""
        print(f"Iniciando despliegue en {self.role} ({self.current_ip})")
        
        if not self.check_docker():
            print("Docker no encontrado, instalando...")
            self.install_docker()
        
        if not self.check_connectivity():
            print("Error: Problemas de conectividad")
            return False
            
        if not self.deploy_services():
            print("Error: Fallo en el despliegue de servicios")
            return False
            
        if not self.verify_deployment():
            print("Error: Fallo en la verificación del despliegue")
            return False
            
        print(f"Despliegue completado con éxito en {self.role}")
        return True

if __name__ == "__main__":
    deployer = EasyCabDeployer()
    deployer.run()