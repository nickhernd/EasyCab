import argparse
import json
import os
import sys
import logging
from typing import Dict
import socket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EasyCabLauncher:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Cargar o crear configuración"""
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
        """Guardar configuración actual"""
        with open('easycab_config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

    def setup_node(self):
        """Configurar nodo según tipo"""
        parser = argparse.ArgumentParser(description='EasyCab Launcher')
        parser.add_argument('node_type', choices=['central', 'taxi', 'customer'],
                          help='Tipo de nodo (central/taxi/customer)')
        parser.add_argument('--central-ip', help='IP del servidor central')
        parser.add_argument('--kafka-ip', help='IP del servidor Kafka')
        parser.add_argument('--id', help='ID para taxi o customer')
        
        args = parser.parse_args()
        
        # Actualizar configuración si se proporcionan IPs
        if args.central_ip:
            self.config['central_ip'] = args.central_ip
        if args.kafka_ip:
            self.config['kafka_ip'] = args.kafka_ip
            
        self.save_config()
        
        # Configurar variables de entorno
        os.environ['CENTRAL_HOST'] = self.config['central_ip']
        os.environ['KAFKA_HOST'] = self.config['kafka_ip']
        
        # Verificar conectividad
        self.check_connectivity()
        
        # Iniciar el componente correspondiente
        if args.node_type == 'central':
            self.start_central()
        elif args.node_type == 'taxi':
            self.start_taxi(args.id or '1')
        else:
            self.start_customer(args.id or 'customer1')

    def check_connectivity(self):
        """Verificar conectividad con Central y Kafka"""
        logger.info("Verificando conectividad...")
        
        def check_port(host, port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except:
                return False

        # Verificar Central
        if check_port(self.config['central_ip'], self.config['central_port']):
            logger.info(f"✅ Central alcanzable en {self.config['central_ip']}:{self.config['central_port']}")
        else:
            logger.warning(f"❌ No se puede alcanzar Central en {self.config['central_ip']}:{self.config['central_port']}")

        # Verificar Kafka
        if check_port(self.config['kafka_ip'], self.config['kafka_port']):
            logger.info(f"✅ Kafka alcanzable en {self.config['kafka_ip']}:{self.config['kafka_port']}")
        else:
            logger.warning(f"❌ No se puede alcanzar Kafka en {self.config['kafka_ip']}:{self.config['kafka_port']}")

    def start_central(self):
        """Iniciar servidor central"""
        logger.info("Iniciando servidor central...")
        try:
            from central.EC_Central import CentralServer
            server = CentralServer()
            server.run()
        except Exception as e:
            logger.error(f"Error iniciando central: {e}")

    def start_taxi(self, taxi_id):
        """Iniciar taxi"""
        logger.info(f"Iniciando taxi {taxi_id}...")
        try:
            from taxi.EC_DE import DigitalEngine
            taxi = DigitalEngine(int(taxi_id), 5000 + int(taxi_id))
            taxi.start()
        except Exception as e:
            logger.error(f"Error iniciando taxi: {e}")

    def start_customer(self, customer_id):
        """Iniciar cliente"""
        logger.info(f"Iniciando cliente {customer_id}...")
        try:
            from customer.EC_Customer import Customer
            customer = Customer(customer_id, 'data/EC_Requests.json')
            customer.run()
        except Exception as e:
            logger.error(f"Error iniciando cliente: {e}")

if __name__ == "__main__":
    launcher = EasyCabLauncher()
    launcher.setup_node()