from confluent_kafka import Producer, Consumer, KafkaError
import json
import threading
import time
from flask import Flask, jsonify, request
import os
import sys
import socket
import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional
import math
from confluent_kafka import Producer, Consumer, KafkaError
import json
import threading
import time
from flask import Flask, jsonify, request
import os
import sys
from typing import Dict, Optional
from resilience_manager import ResilienceManager  # Añadir esta línea

# Inicialización de Flask
app = Flask(__name__)
central_instance = None

class LocationsManager:
    """
    Gestor de ubicaciones del sistema.
    Maneja la carga y gestión de las ubicaciones desde un archivo JSON.
    """
    def __init__(self, json_path="locations.json"):
        self.json_path = json_path
        self.locations = {}
        self.load_locations()

    def load_locations(self):
        """Carga las ubicaciones desde el archivo JSON"""
        try:
            with open(self.json_path, 'r') as file:
                data = json.load(file)
                for loc in data.get('locations', []):
                    loc_id = loc['Id']
                    x, y = map(int, loc['POS'].split(','))
                    self.locations[loc_id] = {
                        'id': loc_id,
                        'x': x,
                        'y': y
                    }
                print(f"Ubicaciones cargadas: {self.locations}")
        except FileNotFoundError:
            print(f"ADVERTENCIA: Archivo de ubicaciones no encontrado: {self.json_path}")
            print("Creando archivo de ubicaciones por defecto...")
            self.create_default_locations()
        except Exception as e:
            print(f"Error cargando ubicaciones: {e}")
            raise

    def create_default_locations(self):
        """Crea ubicaciones por defecto si no existe el archivo"""
        default_locations = {
            "locations": [
                {"Id": "A", "POS": "5,4"},
                {"Id": "B", "POS": "12,8"},
                {"Id": "C", "POS": "17,8"},
                {"Id": "D", "POS": "17,17"},
                {"Id": "E", "POS": "19,19"}
            ]
        }
        with open(self.json_path, 'w') as f:
            json.dump(default_locations, f, indent=4)
        self.load_locations()

    def get_location_coordinates(self, location_id):
        """Obtiene las coordenadas de una ubicación"""
        if location_id in self.locations:
            loc = self.locations[location_id]
            return [loc['x'], loc['y']]
        return None

    def get_all_locations(self):
        """Devuelve todas las ubicaciones"""
        return self.locations

    def exists(self, location_id):
        """Verifica si existe una ubicación"""
        return location_id in self.locations

class DatabaseManager:
    """
    Gestor de base de datos.
    Maneja todas las operaciones relacionadas con la persistencia de datos.
    """
    def __init__(self, host: str, user: str, password: str, database: str = 'easycab'):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.connection = None
        self.max_retries = 5
        self.connect_with_retry()

    def connect_with_retry(self):
        """Intenta conectar a la base de datos con reintentos"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                print(f"Intentando conectar a MySQL (intento {retry_count + 1})")
                self.connection = mysql.connector.connect(**self.config)
                print("Conexión a MySQL establecida")
                self.create_tables()
                return
            except Error as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    print(f"Error fatal conectando a MySQL después de {self.max_retries} intentos: {e}")
                    raise
                print(f"Error conectando a MySQL: {e}. Reintentando en 5 segundos...")
                time.sleep(5)

    def create_tables(self):
        """Crea las tablas necesarias en la base de datos"""
        create_tables_queries = [
            """
            CREATE TABLE IF NOT EXISTS taxis (
                id VARCHAR(20) PRIMARY KEY,
                estado VARCHAR(20) NOT NULL,
                posicion_x INT NOT NULL,
                posicion_y INT NOT NULL,
                ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_ride_id VARCHAR(20),
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS locations (
                id_location VARCHAR(20) PRIMARY KEY,
                coordenada_x INT NOT NULL,
                coordenada_y INT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS rides (
                ride_id VARCHAR(20) PRIMARY KEY,
                taxi_id VARCHAR(20),
                customer_id VARCHAR(20),
                pickup_x INT,
                pickup_y INT,
                destination_x INT,
                destination_y INT,
                estado VARCHAR(20),
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                FOREIGN KEY (taxi_id) REFERENCES taxis(id)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE
            )
            """
        ]
        
        with self.connection.cursor() as cursor:
            for query in create_tables_queries:
                cursor.execute(query)
            self.connection.commit()

    def update_taxi_status(self, taxi_id: str, estado: str, posicion: List[int], 
                          current_ride: Optional[str] = None):
        """Actualiza el estado de un taxi en la base de datos"""
        query = """
        INSERT INTO taxis (id, estado, posicion_x, posicion_y, current_ride_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        estado = VALUES(estado),
        posicion_x = VALUES(posicion_x),
        posicion_y = VALUES(posicion_y),
        current_ride_id = VALUES(current_ride_id),
        ultima_actualizacion = CURRENT_TIMESTAMP
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (taxi_id, estado, posicion[0], posicion[1], current_ride))
            self.connection.commit()

class RouteOptimizer:
    """
    Optimizador de rutas.
    Calcula las mejores rutas y asignaciones de taxis.
    """
    def __init__(self):
        self.map_size = 20

    def calculate_distance(self, point1: List[int], point2: List[int]) -> int:
        """
        Calcula la distancia Manhattan entre dos puntos considerando el mapa esférico
        """
        dx = min(abs(point1[0] - point2[0]), self.map_size - abs(point1[0] - point2[0]))
        dy = min(abs(point1[1] - point2[1]), self.map_size - abs(point1[1] - point2[1]))
        return dx + dy

    def get_next_position(self, current: List[int], target: List[int]) -> List[int]:
        """Calcula la siguiente posición hacia el objetivo en mapa esférico"""
        next_pos = current.copy()
        
        for i in range(2):
            diff = target[i] - current[i]
            if abs(diff) > self.map_size/2:
                # Si la distancia es mayor que la mitad del mapa, ir en dirección opuesta
                if diff > 0:
                    next_pos[i] = (current[i] - 1) % self.map_size
                else:
                    next_pos[i] = (current[i] + 1) % self.map_size
            else:
                # Movimiento normal
                if diff > 0:
                    next_pos[i] = (current[i] + 1) % self.map_size
                elif diff < 0:
                    next_pos[i] = (current[i] - 1) % self.map_size

        return next_pos

class ECCentral:
    """
    Clase principal del sistema central.
    Coordina todas las operaciones del sistema de taxis.
    """
    def __init__(self, listen_port: int, kafka_broker: str, db_config: dict):
        self.listen_port = listen_port
        self.map = self.load_map()
        self.kafka_broker = kafka_broker
        print(f"Iniciando sistema en puerto {listen_port}")
        print(f"Conectando a Kafka en {kafka_broker}")
        
        # Inicializar componentes
        self.db = DatabaseManager(**db_config)
        self.route_optimizer = RouteOptimizer()
        self.locations_manager = LocationsManager()
        
        # Estado del sistema
        self.taxis = {}
        self.pending_queue = []
        self.active_rides = {}
        self.ride_counter = 0
        self.is_running = True
        
        # Configuración Kafka
        self.setup_kafka()

        # Inicializar gestor de resiliencia
        self.resilience_manager = ResilienceManager()

        # Registrar callbacks de resiliencia
        self.setup_resilience_callbacks()

    def send_customer_notification(self, customer_id: str, message: str):
        """Envía una notificación a un cliente"""
        notification = {
            'customer_id': customer_id,
            'type': 'NOTIFICATION',
            'message': message,
            'timestamp': time.time()
        }
        try:
            self.producer.produce('centralresponses', json.dumps(notification).encode('utf-8'))
            self.producer.flush()
        except Exception as e:
            print(f"Error enviando notificación al cliente: {e}")

    def setup_resilience_callbacks(self):
        """Configura los callbacks para eventos de resiliencia"""

        # Callback para timeout de taxi
        def taxi_timeout(taxi_id, state):
            print(f"Taxi {taxi_id} no responde")
            if taxi_id in self.taxis:
                ride_id = self.taxis[taxi_id].get('current_ride')
                if ride_id and ride_id in self.active_rides:
                    # Notificar al cliente
                    self.send_customer_notification(
                        self.active_rides[ride_id]['customer_id'],
                        f"Taxi {taxi_id} no responde. El servicio será reasignado."
                    )
                    # Poner el viaje de nuevo en la cola
                    self.pending_queue.insert(0, {
                        'customer_id': self.active_rides[ride_id]['customer_id'],
                        'pickup_position': self.active_rides[ride_id]['pickup_position'],
                        'destination': self.active_rides[ride_id]['destination']
                    })
                    # Marcar el viaje como fallido
                    self.active_rides[ride_id]['status'] = 'FAILED'
                # Marcar taxi como inactivo en el mapa
                self.taxis[taxi_id]['state'] = 'INACTIVE'
                self.update_map()
            
            # Callback para timeout de sensor
        def sensor_timeout(sensor_id, state):
            print(f"Sensor {sensor_id} no responde")
            # Encontrar el taxi asociado
            taxi_id = sensor_id.split('_')[1]
            if taxi_id in self.taxis:
                # Parar el taxi por seguridad
                self.send_taxi_instruction(taxi_id, 'STOP', None)
                self.taxis[taxi_id]['state'] = 'STOPPED'
                self.update_map()

        # Callback para recuperación de sensor
        def sensor_recovery(sensor_id, state):
            print(f"Sensor {sensor_id} recuperado")
            taxi_id = sensor_id.split('_')[1]
            if taxi_id in self.taxis and self.taxis[taxi_id]['state'] == 'STOPPED':
                self.send_taxi_instruction(taxi_id, 'RESUME', None)

        # Callback para recuperación de taxi
        def taxi_recovery(taxi_id, state):    # Esta es la función que faltaba
            print(f"Taxi {taxi_id} recuperado")
            if taxi_id in self.taxis:
                self.taxis[taxi_id]['state'] = 'IDLE'
                self.update_map()

        # Registrar callbacks
        self.resilience_manager.register_callback('taxi', 'timeout', taxi_timeout)
        self.resilience_manager.register_callback('taxi', 'recovery', taxi_recovery)
        self.resilience_manager.register_callback('sensor', 'timeout', sensor_timeout)
        self.resilience_manager.register_callback('sensor', 'recovery', sensor_recovery)


    def setup_kafka(self):
        """Configura las conexiones Kafka"""
        producer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'client.id': 'central-producer'
        }
        self.producer = Producer(producer_conf)

        consumer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': 'central',
            'auto.offset.reset': 'earliest'
        }
        self.consumer = Consumer(consumer_conf)
        
        # Configuración de topics
        self.topics = ['customerrequests', 'centralresponses', 'taxistatus', 'taxiinstructions']
        self.ensure_topics_exist(self.topics)
        self.consumer.subscribe(['customerrequests', 'taxistatus'])

    def ensure_topics_exist(self, topics):
        """Asegura que los topics necesarios existan"""
        for topic in topics:
            try:
                print(f"Verificando topic: {topic}")
                self.producer.produce(topic, b'topic_init')
                self.producer.flush(timeout=5)
                print(f"Topic {topic} listo")
            except Exception as e:
                print(f"Error verificando topic {topic}: {e}")
        time.sleep(2)

    def load_map(self):
        """Carga el mapa inicial"""
        return [[0 for _ in range(20)] for _ in range(20)]

    def update_map(self):
        """Actualiza el mapa con las posiciones actuales"""
        new_map = self.load_map()
        
        # Añadir ubicaciones
        for loc_id, loc_info in self.locations_manager.get_all_locations().items():
            x, y = loc_info['x'], loc_info['y']
            if 0 <= x < 20 and 0 <= y < 20:
                new_map[x][y] = loc_id.upper()
        
        # Añadir taxis
        for taxi_id, info in self.taxis.items():
            pos = info.get('position', [0, 0])
            state = info.get('state', 'IDLE')
            if 0 <= pos[0] < 20 and 0 <= pos[1] < 20:
                new_map[pos[0]][pos[1]] = f"T{taxi_id}_{state}"
        
        self.map = new_map

    def generate_ride_id(self):
        """Genera un ID único para cada viaje"""
        self.ride_counter += 1
        return f"RIDE_{self.ride_counter}"

    def assign_taxi(self, customer_request):
        """Asigna un taxi a una solicitud de cliente"""
        customer_id = customer_request['customer_id']
        pickup_position = customer_request.get('pickup_position', [1, 1])
        destination_id = customer_request['destination']
        
        # Verificar destino válido
        if not self.locations_manager.exists(destination_id):
            return {
                'status': 'ERROR',
                'message': f'Destino {destination_id} no válido'
            }
        
        destination = self.locations_manager.get_location_coordinates(destination_id)
        
        # Buscar taxi más cercano
        nearest_taxi = None
        min_distance = float('inf')
        
        for taxi_id, info in self.taxis.items():
            if info['state'] == 'IDLE':
                distance = self.route_optimizer.calculate_distance(
                    info['position'], 
                    pickup_position
                )
                if distance < min_distance:
                    min_distance = distance
                    nearest_taxi = taxi_id
        
        if nearest_taxi:
            ride_id = self.generate_ride_id()
            
            # Actualizar estado del taxi
            self.taxis[nearest_taxi]['state'] = 'MOVING'
            self.taxis[nearest_taxi]['current_ride'] = ride_id
            
            # Registrar el viaje
            self.active_rides[ride_id] = {
                'customer_id': customer_id,
                'taxi_id': nearest_taxi,
                'pickup_position': pickup_position,
                'destination': destination,
                'status': 'ASSIGNED',
                'start_time': time.time()
            }
            
            # Actualizar BD
            self.db.update_taxi_status(
                nearest_taxi,
                'MOVING',
                self.taxis[nearest_taxi]['position'],
                ride_id
            )
            
            # Enviar instrucción al taxi
            self.send_taxi_instruction(nearest_taxi, 'PICKUP', pickup_position)
            
            # Actualizar mapa
            self.update_map()
            
            response = {
                'status': 'OK',
                'message': f'Taxi {nearest_taxi} asignado',
                'ride_id': ride_id,
                'estimated_pickup_time': min_distance * 2
            }
        else:
            self.pending_queue.append(customer_request)
            response = {
                'status': 'QUEUED',
                'message': 'No hay taxis disponibles, solicitud en cola',
                'queue_position': len(self.pending_queue)
            }
        
        return response

    def update_taxi_status(self, status):
        """Actualiza el estado de un taxi"""
        taxi_id = status.get('taxi_id')
        if not taxi_id:
            return
        
        # Actualizar estado en el gestor de resiliencia
        self.resilience_manager.update_component('taxi', taxi_id, status)

        old_state = self.taxis.get(taxi_id, {}).get('state')
        new_state = status.get('state')
        new_position = status.get('position', [0, 0])
        
        # Actualizar estado en memoria
        self.taxis[taxi_id] = {
            'position': new_position,
            'state': new_state,
            'last_update': time.time(),
            'current_ride': self.taxis.get(taxi_id, {}).get('current_ride')
        }

        # Actualizar en base de datos
        self.db.update_taxi_status(
            taxi_id,
            new_state,
            new_position,
            self.taxis[taxi_id].get('current_ride')
        )

        # Si el taxi cambia de MOVING a IDLE, procesar siguiente solicitud
        if old_state != 'IDLE' and new_state == 'IDLE':
            ride_id = self.taxis[taxi_id].get('current_ride')
            if ride_id and ride_id in self.active_rides:
                self.active_rides[ride_id]['status'] = 'COMPLETED'
                self.taxis[taxi_id]['current_ride'] = None

            # Procesar siguiente solicitud en cola
            if self.pending_queue:
                next_request = self.pending_queue.pop(0)
                self.process_customer_request(next_request)

        # Actualizar mapa
        self.update_map()

    def send_taxi_instruction(self, taxi_id, instruction_type, destination):
        """Envía instrucciones a un taxi"""
        instruction = {
            'taxi_id': taxi_id,
            'type': instruction_type,
            'destination': destination,
            'timestamp': time.time()
        }
        try:
            self.producer.produce('taxiinstructions', 
                                json.dumps(instruction).encode('utf-8'))
            self.producer.flush()
            print(f"Instrucción enviada a taxi {taxi_id}: {instruction}")
        except Exception as e:
            print(f"Error enviando instrucción: {e}")

    def process_customer_request(self, request):
        """Procesa una solicitud de cliente"""
        print(f"Procesando solicitud de cliente: {request}")
        response = self.assign_taxi(request)
        try:
            self.producer.produce('centralresponses', 
                                json.dumps(response).encode('utf-8'))
            self.producer.flush()
            print(f"Respuesta enviada: {response}")
        except Exception as e:
            print(f"Error enviando respuesta: {e}")

    def process_message(self, msg):
        """Procesa los mensajes recibidos"""
        try:
            data = json.loads(msg.value().decode('utf-8'))

            if msg.topic() == 'taxistatus':
                self.update_taxi_status(data)
                # Actualizar también el estado del sensor si viene en el mensaje
                if 'sensor_status' in data:
                    self.resilience_manager.update_component('sensor', f"sensor_{data['taxi_id']}", {
                        'status': data['sensor_status']
                    })

            elif msg.topic() == 'customerrequests':
                self.process_customer_request(data)
                # Registrar el cliente en el gestor de resiliencia
                self.resilience_manager.update_component('customer', data['customer_id'], {
                    'last_request': data
                })

        except json.JSONDecodeError:
            print(f"JSON inválido recibido: {msg.value().decode('utf-8')}")
        except Exception as e:
            print(f"Error procesando mensaje: {e}")

    def run(self):
        """Bucle principal del servicio"""
        print("Iniciando servicio central...")
        while self.is_running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Error del consumidor: {msg.error()}")
                        continue
                
                self.process_message(msg)
            except Exception as e:
                print(f"Error en bucle principal: {e}")
                time.sleep(1)

    def shutdown(self):
        """Cierra el servicio de manera ordenada"""
        print("Cerrando servicio central...")
        self.is_running = False
        self.consumer.close()
        self.producer.flush()
        if hasattr(self, 'db'):
            self.db.connection.close()

# Rutas de la API
@app.route('/')
def root():
    return "EasyCab Central Service está ejecutándose"

@app.route('/health')
def health_check():
    if central_instance:
        return jsonify({"status": "OK"}), 200
    return jsonify({"status": "ERROR", "message": "Servicio no inicializado"}), 500

@app.route('/map')
def get_map():
    if central_instance:
        return jsonify(central_instance.map)
    return jsonify({"error": "Servicio no inicializado"}), 500

@app.route('/system/status')
def get_system_status():
    if not central_instance:
        return jsonify({"error": "Servicio no inicializado"}), 500
    
    active_taxis = len([t for t in central_instance.taxis.values() if t['state'] == 'MOVING'])
    idle_taxis = len([t for t in central_instance.taxis.values() if t['state'] == 'IDLE'])
    
    return jsonify({
        'taxis': {
            'total': len(central_instance.taxis),
            'active': active_taxis,
            'idle': idle_taxis
        },
        'pending_requests': len(central_instance.pending_queue),
        'map_size': len(central_instance.map)
    })

@app.route('/taxis')
def get_taxis():
    if central_instance:
        return jsonify({
            'taxis': central_instance.taxis,
            'total': len(central_instance.taxis)
        })
    return jsonify({"error": "Servicio no inicializado"}), 500

@app.route('/taxis/<taxi_id>')
def get_taxi_status(taxi_id):
    if not central_instance:
        return jsonify({"error": "Servicio no inicializado"}), 500
    
    if taxi_id in central_instance.taxis:
        return jsonify(central_instance.taxis[taxi_id])
    return jsonify({'error': 'Taxi no encontrado'}), 404

@app.route('/rides/active')
def get_active_rides():
    if central_instance:
        return jsonify({
            'active_rides': central_instance.active_rides,
            'total': len(central_instance.active_rides)
        })
    return jsonify({"error": "Servicio no inicializado"}), 500

@app.route('/rides/<ride_id>')
def get_ride_status(ride_id):
    if not central_instance:
        return jsonify({"error": "Servicio no inicializado"}), 500
    
    if ride_id in central_instance.active_rides:
        return jsonify(central_instance.active_rides[ride_id])
    return jsonify({'error': 'Viaje no encontrado'}), 404

@app.route('/queue/status')
def get_queue_status():
    if central_instance:
        return jsonify({
            'pending_requests': len(central_instance.pending_queue),
            'requests': central_instance.pending_queue
        })
    return jsonify({"error": "Servicio no inicializado"}), 500

@app.route('/taxi/control/<taxi_id>', methods=['POST'])
def control_taxi(taxi_id):
    """Endpoint para control manual de taxis"""
    if not central_instance:
        return jsonify({"error": "Servicio no inicializado"}), 500
    
    if taxi_id not in central_instance.taxis:
        return jsonify({"error": "Taxi no encontrado"}), 404
    
    action = request.json.get('action')
    if not action:
        return jsonify({"error": "Acción no especificada"}), 400
    
    if action == 'stop':
        central_instance.send_taxi_instruction(taxi_id, 'STOP', None)
        return jsonify({"message": f"Instrucción de parada enviada a taxi {taxi_id}"})
    elif action == 'resume':
        central_instance.send_taxi_instruction(taxi_id, 'RESUME', None)
        return jsonify({"message": f"Instrucción de reanudar enviada a taxi {taxi_id}"})
    elif action == 'return':
        central_instance.send_taxi_instruction(taxi_id, 'RETURN', [1, 1])
        return jsonify({"message": f"Instrucción de retorno a base enviada a taxi {taxi_id}"})
    else:
        return jsonify({"error": "Acción no válida"}), 400

def wait_for_flask():
    time.sleep(2)

def run_flask():
    app.run(host='0.0.0.0', port=central_instance.listen_port, use_reloader=False)

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Uso: python EC_Central.py <puerto_escucha> <kafka_ip:puerto> <db_host> <db_user> <db_password>")
        print("Ejemplo: python EC_Central.py 8000 192.168.1.42:9092 192.168.1.42 root password")
        sys.exit(1)
    
    try:
        # Parsear parámetros
        listen_port = int(sys.argv[1])
        kafka_broker = sys.argv[2]
        db_host = sys.argv[3]
        db_user = sys.argv[4]
        db_password = sys.argv[5]
        
        # Configuración base de datos
        db_config = {
            'host': db_host,
            'user': db_user,
            'password': db_password,
            'database': 'easycab'
        }
        
        # Iniciar central
        central_instance = ECCentral(
            listen_port=listen_port,
            kafka_broker=kafka_broker,
            db_config=db_config
        )
        
        # Iniciar servidor Flask
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        wait_for_flask()
        
        try:
            central_instance.run()
        except KeyboardInterrupt:
            print("\nApagando el sistema...")
            central_instance.shutdown()
        except Exception as e:
            print(f"\nError fatal: {e}")
            central_instance.shutdown()
            
    except Exception as e:
        print(f"Error iniciando el sistema: {e}")
        sys.exit(1)