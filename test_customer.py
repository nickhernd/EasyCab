from confluent_kafka import Producer
import json
import time
import random

def send_customer_request():
    producer = Producer({'bootstrap.servers': 'localhost:9092'})
    
    # Lista de destinos posibles
    destinations = ['A', 'B', 'C', 'D', 'E']
    
    # Leer destinos del archivo si existe
    try:
        with open('customer_requests.txt', 'r') as f:
            destinations = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Usando destinos por defecto")

    print("Enviando solicitudes de cliente. Presiona Ctrl+C para detener.")
    
    customer_id = 1
    try:
        while True:
            destination = random.choice(destinations)
            request = {
                'customer_id': f'C{customer_id}',
                'pickup_position': [random.randint(0, 19), random.randint(0, 19)],
                'destination': destination,
                'timestamp': time.time()
            }
            
            producer.produce('customerrequests', json.dumps(request).encode('utf-8'))
            producer.flush()
            print(f"Solicitud enviada: Cliente {customer_id} -> Destino {destination}")
            
            customer_id += 1
            time.sleep(4)  # Esperar 4 segundos entre solicitudes
            
    except KeyboardInterrupt:
        print("\nDeteniendo envío de solicitudes")

if __name__ == "__main__":
    send_customer_request()