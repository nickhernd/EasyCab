#!/usr/bin/env python3
from deploy_base import BaseDeployer
import subprocess
import os
import platform

class CentralDeployer(BaseDeployer):
    def validate_environment(self):
        required_ports = [50051]  # Puerto para Central
        if not self.check_ports(required_ports):
            return False
            
        # Verificar que estamos en Linux
        if platform.system() != 'Linux':
            print("Error: Este script debe ejecutarse en Linux")
            return False
            
        return True

    def deploy(self):
        print(f"Desplegando servicio Central en {self.current_ip}")
        
        # Configurar variables de entorno
        os.environ['CENTRAL_HOST'] = self.current_ip
        os.environ['CENTRAL_PORT'] = '50051'
        os.environ['KAFKA_HOST'] = self.config['nodes']['kafka']['ip']
        
        try:
            # Detener servicios previos
            self.stop_services()
            
            # Desplegar servicio
            commands = [
                'docker-compose -f docker-compose.central.yml build',
                'docker-compose -f docker-compose.central.yml up -d'
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
                
            print("Despliegue de Central completado")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error en el despliegue: {e}")
            return False

if __name__ == "__main__":
    deployer = CentralDeployer()
    if deployer.validate_environment():
        deployer.deploy()