#!/usr/bin/env python3
import socket
import json
import subprocess
import sys
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def test_network_connectivity(config):
    print("=== Prueba de conectividad de red ===")
    for node_name, node in config['nodes'].items():
        ip = node['ip']
        print(f"\nProbando conexión a {node_name} ({ip})...")
        
        # Ping test
        ping_cmd = 'ping -n 1' if os.name == 'nt' else 'ping -c 1'
        try:
            subprocess.run(f'{ping_cmd} {ip}', shell=True, check=True, capture_output=True)
            print(f"✓ Ping a {node_name} exitoso")
        except subprocess.CalledProcessError:
            print(f"✗ No se puede hacer ping a {node_name}")
            continue

        # Puerto test
        for port in node['ports']:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            if result == 0:
                print(f"✓ Puerto {port} abierto en {node_name}")
            else:
                print(f"✗ Puerto {port} cerrado en {node_name}")
            sock.close()

def test_kafka_connectivity(config):
    print("\n=== Prueba de conectividad Kafka ===")
    kafka_ip = config['nodes']['kafka']['ip']
    kafka_port = 9092
    
    try:
        from kafka import KafkaProducer, KafkaConsumer
        
        # Prueba del productor
        producer = KafkaProducer(
            bootstrap_servers=f'{kafka_ip}:{kafka_port}',
            api_version=(0, 10, 1)
        )
        print("✓ Conexión del productor Kafka exitosa")
        
        # Prueba del consumidor
        consumer = KafkaConsumer(
            bootstrap_servers=f'{kafka_ip}:{kafka_port}',
            api_version=(0, 10, 1)
        )
        print("✓ Conexión del consumidor Kafka exitosa")
        
    except Exception as e:
        print(f"✗ Error en la conexión Kafka: {str(e)}")

def main():
    print("Iniciando pruebas de conectividad...")
    try:
        config = load_config()
        test_network_connectivity(config)
        test_kafka_connectivity(config)
    except Exception as e:
        print(f"Error durante las pruebas: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()