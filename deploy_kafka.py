#!/usr/bin/env python3
from deploy_base import BaseDeployer
import subprocess
import os
import sys

class KafkaDeployer(BaseDeployer):
    def validate_environment(self):
        print("Validando entorno para despliegue de Kafka...")
        
        # Verificar sistema operativo
        if os.name != 'nt':
            print("Error: Este script debe ejecutarse en Windows")
            return False
        
        # Verificar Docker
        if not self.check_docker():
            print("Error: Docker no está instalado o no está en ejecución")
            print("Por favor, instale Docker Desktop y asegúrese de que está en ejecución")
            return False
            
        # Verificar puertos
        required_ports = [2181, 9092]
        if not self.check_ports(required_ports):
            return False
            
        print("Validación de entorno completada con éxito")
        return True

    def deploy(self):
        try:
            print(f"Iniciando despliegue de servicios Kafka en {self.current_ip}")
            
            # Configurar variables de entorno
            os.environ['KAFKA_HOST'] = self.current_ip
            os.environ['KAFKA_PORT'] = '9092'
            
            # Verificar que existe el archivo docker-compose.kafka.yml
            if not os.path.exists('docker-compose.kafka.yml'):
                print("Error: No se encuentra el archivo docker-compose.kafka.yml")
                return False
            
            # Detener servicios previos
            print("Deteniendo servicios previos...")
            self.stop_services()
            
            # Desplegar servicios
            print("Desplegando servicios...")
            commands = [
                'docker-compose -f docker-compose.kafka.yml build',
                'docker-compose -f docker-compose.kafka.yml up -d'
            ]
            
            for cmd in commands:
                print(f"Ejecutando: {cmd}")
                subprocess.run(cmd, shell=True, check=True)
                
            print("\nDespliegue de Kafka completado exitosamente")
            print(f"Kafka está escuchando en: {self.current_ip}:9092")
            print("Zookeeper está escuchando en: {self.current_ip}:2181")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error en el despliegue: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado: {e}")
            return False

if __name__ == "__main__":
    try:
        print("=== Iniciando despliegue de EasyCab Kafka ===")
        deployer = KafkaDeployer()
        if deployer.validate_environment():
            deployer.deploy()
    except Exception as e:
        print(f"Error crítico: {e}")
        sys.exit(1)