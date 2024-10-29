#!/usr/bin/env python3
from deploy_base import BaseDeployer
import subprocess
import os
import platform

class TaxiDeployer(BaseDeployer):
    def validate_environment(self):
        required_ports = [50052]  # Puerto para Taxi
        if not self.check_ports(required_ports):
            return False
            
            
        return True

    def deploy(self):
        print(f"Desplegando servicios Taxi en {self.current_ip}")
        
        # Configurar variables de entorno
        os.environ['TAXI_HOST'] = self.current_ip
        os.environ['TAXI_PORT'] = '50052'
        os.environ['KAFKA_HOST'] = self.config['nodes']['kafka']['ip']
        os.environ['CENTRAL_HOST'] = self.config['nodes']['central']['ip']
        
        try:
            # Detener servicios previos
            self.stop_services()
            
            # Desplegar servicios
            commands = [
                'docker-compose -f docker-compose.taxi.yml build',
                'docker-compose -f docker-compose.taxi.yml up -d'
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
                
            print("Despliegue de Taxi completado")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error en el despliegue: {e}")
            return False

if __name__ == "__main__":
    deployer = TaxiDeployer()
    if deployer.validate_environment():
        deployer.deploy()