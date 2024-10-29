#!/usr/bin/env python3
from deploy_base import BaseDeployer
import subprocess
import os

class KafkaDeployer(BaseDeployer):
    def validate_environment(self):
        required_ports = [2181, 9092]  # Zookeeper y Kafka
        if not self.check_ports(required_ports):
            return False
            
        # Verificar que estamos en Windows
        if os.name != 'nt':
            print("Error: Este script debe ejecutarse en Windows")
            return False
            
        return True

    def deploy(self):
        print(f"Desplegando servicios Kafka en {self.current_ip}")
        
        # Configurar variables de entorno
        os.environ['KAFKA_HOST'] = self.current_ip
        os.environ['KAFKA_PORT'] = '9092'
        
        try:
            # Detener servicios previos
            self.stop_services()
            
            # Desplegar servicios
            commands = [
                'docker-compose -f docker-compose.kafka.yml build',
                'docker-compose -f docker-compose.kafka.yml up -d'
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, check=True)
                
            print("Despliegue de Kafka completado")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error en el despliegue: {e}")
            return False

if __name__ == "__main__":
    deployer = KafkaDeployer()
    if deployer.validate_environment():
        deployer.deploy()