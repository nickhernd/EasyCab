# EC_Central/src/main.py
import socket
import sys
import threading
import json
from typing import List, Dict, Tuple
import logging
from dataclasses import dataclass
from kafka import KafkaProducer, KafkaConsumer
import numpy as np

@dataclass
class Taxi:
    id: int
    position: Tuple[int, int]
    state: str  # 'GREEN' for moving, 'RED' for stopped
    destination: Tuple[int, int] = None
    token: str = None

class MapManager:
    def __init__(self, size: int = 20):
        self.size = size
        self.map = np.full((size, size), None)
        self.locations = {}  # Dictionary to store locations from config file
        self.taxis: Dict[int, Taxi] = {}
        
    def load_locations(self, filename: str):
        """Load locations from config file"""
        try:
            with open(filename, 'r') as f:
                for line in f:
                    loc_id, x, y = line.strip().split()
                    self.locations[loc_id] = (int(x), int(y))
                    self.map[int(x)][int(y)] = f'LOC_{loc_id}'
        except Exception as e:
            logging.error(f"Error loading locations: {e}")

    def update_taxi_position(self, taxi_id: int, new_position: Tuple[int, int], state: str):
        """Update taxi position on map"""
        if taxi_id in self.taxis:
            old_pos = self.taxis[taxi_id].position
            if old_pos:
                self.map[old_pos[0]][old_pos[1]] = None
            
            self.taxis[taxi_id].position = new_position
            self.taxis[taxi_id].state = state
            self.map[new_position[0]][new_position[1]] = f'TAXI_{taxi_id}_{state}'
            return True
        return False

    def get_map_state(self) -> str:
        """Return current map state as string"""
        return json.dumps({
            'map': self.map.tolist(),
            'locations': self.locations,
            'taxis': {k: {'position': v.position, 'state': v.state} 
                     for k, v in self.taxis.items()}
        })

class ECCentral:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, kafka_server: str = 'localhost:9092'):
        self.host = host
        self.port = port
        self.map_manager = MapManager()
        
        # Configuración de Kafka
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_server],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # Inicializar socket servidor
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def start(self):
        """Iniciar el servidor"""
        logging.info(f"EC_Central iniciado en {self.host}:{self.port}")
        
        # Cargar ubicaciones del archivo de configuración
        self.map_manager.load_locations('config/locations.txt')
        
        # Iniciar thread para escuchar mensajes Kafka
        kafka_thread = threading.Thread(target=self.listen_kafka_messages)
        kafka_thread.daemon = True
        kafka_thread.start()
        
        # Aceptar conexiones de clientes
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logging.error(f"Error accepting connection: {e}")

    def handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Manejar conexiones de clientes"""
        logging.info(f"Nueva conexión desde {address}")
        
        try:
            while True:
                # Recibir mensaje del cliente
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                response = self.process_message(message)
                
                # Enviar respuesta
                client_socket.send(json.dumps(response).encode('utf-8'))
                
                # Actualizar mapa para todos los clientes
                self.broadcast_map_state()
                
        except Exception as e:
            logging.error(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            logging.info(f"Conexión cerrada con {address}")

    def process_message(self, message: Dict) -> Dict:
        """Procesar mensajes recibidos"""
        msg_type = message.get('type')
        
        if msg_type == 'AUTH':
            return self.handle_auth(message)
        elif msg_type == 'POSITION':
            return self.handle_position_update(message)
        elif msg_type == 'SERVICE_REQUEST':
            return self.handle_service_request(message)
        else:
            return {'status': 'ERROR', 'message': 'Unknown message type'}

    def handle_auth(self, message: Dict) -> Dict:
        """Manejar autenticación de taxis"""
        taxi_id = message.get('taxi_id')
        if taxi_id not in self.map_manager.taxis:
            # Crear nuevo taxi en posición inicial (1,1)
            self.map_manager.taxis[taxi_id] = Taxi(
                id=taxi_id,
                position=(1, 1),
                state='RED'
            )
            # Generar token (en una implementación real, usar JWT)
            token = f"token_{taxi_id}"
            self.map_manager.taxis[taxi_id].token = token
            
            return {'status': 'OK', 'token': token}
        return {'status': 'ERROR', 'message': 'Taxi already registered'}

    def handle_position_update(self, message: Dict) -> Dict:
        """Manejar actualizaciones de posición de taxis"""
        taxi_id = message.get('taxi_id')
        token = message.get('token')
        position = message.get('position')
        state = message.get('state')
        
        # Verificar token
        if not self.verify_token(taxi_id, token):
            return {'status': 'ERROR', 'message': 'Invalid token'}
            
        if self.map_manager.update_taxi_position(taxi_id, position, state):
            return {'status': 'OK', 'map': self.map_manager.get_map_state()}
        return {'status': 'ERROR', 'message': 'Could not update position'}

    def handle_service_request(self, message: Dict) -> Dict:
        """Manejar solicitudes de servicio"""
        destination = message.get('destination')
        if destination in self.map_manager.locations:
            # Encontrar taxi disponible más cercano
            available_taxi = self.find_available_taxi(self.map_manager.locations[destination])
            if available_taxi:
                # Asignar servicio al taxi
                return {'status': 'OK', 'taxi_id': available_taxi.id}
        return {'status': 'ERROR', 'message': 'No taxis available'}

    def verify_token(self, taxi_id: int, token: str) -> bool:
        """Verificar token de taxi"""
        if taxi_id in self.map_manager.taxis:
            return self.map_manager.taxis[taxi_id].token == token
        return False

    def find_available_taxi(self, destination: Tuple[int, int]) -> Taxi:
        """Encontrar taxi disponible más cercano"""
        available_taxis = [taxi for taxi in self.map_manager.taxis.values() 
                         if taxi.state == 'RED']
        if available_taxis:
            # En una implementación real, calcular distancias y seleccionar el más cercano
            return available_taxis[0]
        return None

    def broadcast_map_state(self):
        """Transmitir estado del mapa a través de Kafka"""
        try:
            self.producer.send('map_updates', self.map_manager.get_map_state())
        except Exception as e:
            logging.error(f"Error broadcasting map state: {e}")

    def listen_kafka_messages(self):
        """Escuchar mensajes de Kafka"""
        consumer = KafkaConsumer(
            'taxi_events',
            bootstrap_servers=['localhost:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        for message in consumer:
            try:
                self.process_kafka_message(message.value)
            except Exception as e:
                logging.error(f"Error processing Kafka message: {e}")

    def process_kafka_message(self, message: Dict):
        """Procesar mensajes de Kafka"""
        # Implementar lógica para procesar mensajes de Kafka
        pass

if __name__ == "__main__":
    # Verificar número correcto de argumentos
    if len(sys.argv) != 3:
        print("Uso: python main.py <puerto_escucha> <ip:puerto_kafka>")
        print("Ejemplo: python main.py 5000 localhost:9092")
        sys.exit(1)

    try:
        # Obtener argumentos posicionales
        port = int(sys.argv[1])
        kafka_server = sys.argv[2]

        # Iniciar el servidor
        server = ECCentral(port=port, kafka_server=kafka_server)
        server.start()
    except ValueError:
        print("Error: El puerto debe ser un número entero")
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")
        sys.exit(1)