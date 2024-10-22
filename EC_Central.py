from confluent_kafka import Producer, Consumer, KafkaError
import json
import threading
import time
from flask import Flask, jsonify, request
import os
import math
import heapq
from typing import List, Tuple, Dict

app = Flask(__name__)
central_instance = None

class RouteOptimizer:
    def __init__(self):
        self.map_size = 20

    def calculate_manhattan_distance(self, point1: List[int], point2: List[int]) -> int:
        """Calcula la distancia Manhattan entre dos puntos"""
        return abs(point1[0] - point2[0]) + abs(point1[1] - point2[1])

    def calculate_euclidean_distance(self, point1: List[int], point2: List[int]) -> float:
        """Calcula la distancia Euclidiana entre dos puntos"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def find_optimal_route(self, start: List[int], end: List[int]) -> List[List[int]]:
        """Encuentra la ruta óptima entre dos puntos usando A*"""
        def heuristic(point):
            return self.calculate_manhattan_distance(point, end)
        
        def get_neighbors(point):
            x, y = point
            neighbors = []
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                new_x, new_y = (x + dx) % self.map_size, (y + dy) % self.map_size
                neighbors.append([new_x, new_y])
            return neighbors

        start_tuple = tuple(start)
        end_tuple = tuple(end)
        
        frontier = [(0, start_tuple)]
        came_from = {start_tuple: None}
        cost_so_far = {start_tuple: 0}
        
        while frontier:
            current_cost, current = heapq.heappop(frontier)
            
            if current == end_tuple:
                break
                
            for next_pos in get_neighbors(current):
                next_tuple = tuple(next_pos)
                new_cost = cost_so_far[current] + 1
                
                if next_tuple not in cost_so_far or new_cost < cost_so_far[next_tuple]:
                    cost_so_far[next_tuple] = new_cost
                    priority = new_cost + heuristic(next_pos)
                    heapq.heappush(frontier, (priority, next_tuple))
                    came_from[next_tuple] = current
        
        # Reconstruir el camino
        path = []
        current = end_tuple
        while current is not None:
            path.append(list(current))
            current = came_from.get(current)
        return list(reversed(path))

    def assign_optimal_taxi(self, customer_request: Dict, available_taxis: Dict) -> Tuple[str, List[List[int]], float]:
        """Asigna el taxi óptimo para una solicitud"""
        best_taxi = None
        best_score = float('inf')
        best_route = None
        customer_pos = customer_request.get('pickup_position', [1, 1])

        for taxi_id, taxi_info in available_taxis.items():
            if taxi_info['state'] != 'IDLE':
                continue

            taxi_pos = taxi_info.get('position', [0, 0])
            distance = self.calculate_manhattan_distance(taxi_pos, customer_pos)
            
            # Score basado en distancia y estado del taxi
            score = distance * 1.0  # Factor base: distancia
            
            if score < best_score:
                route = self.find_optimal_route(taxi_pos, customer_pos)
                best_score = score
                best_taxi = taxi_id
                best_route = route

        return best_taxi, best_route, best_score

class ECCentral:
    def __init__(self):
        self.map = self.load_map()
        self.kafka_broker = os.environ.get('KAFKA_BROKER', 'kafka:9092')
        print(f"Connecting to Kafka at {self.kafka_broker}")
        
        # Estado del sistema
        self.taxis = {}
        self.pending_queue = []
        self.active_rides = {}
        self.ride_counter = 0
        self.is_running = True
        
        # Inicializar optimizador de rutas
        self.route_optimizer = RouteOptimizer()
        
        # Configuración Kafka
        self.setup_kafka()
        
    def setup_kafka(self):
        """Configura las conexiones Kafka"""
        producer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'debug': 'all'
        }
        self.producer = Producer(producer_conf)

        consumer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': 'central',
            'auto.offset.reset': 'earliest',
            'debug': 'all'
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
                print(f"Attempting to create/verify topic: {topic}")
                self.producer.produce(topic, b'topic_init')
                self.producer.flush(timeout=5)
                print(f"Topic {topic} is ready")
            except Exception as e:
                print(f"Error ensuring topic {topic} exists: {e}")
        time.sleep(2)

    def load_map(self):
        """Carga el mapa inicial"""
        return [[0 for _ in range(20)] for _ in range(20)]

    def update_map(self):
        """Actualiza el mapa con las posiciones actuales"""
        new_map = self.load_map()
        for taxi_id, info in self.taxis.items():
            pos = info.get('position', [0, 0])
            state = info.get('state', 'IDLE')
            if 0 <= pos[0] < 20 and 0 <= pos[1] < 20:
                # Añadir estado al identificador del taxi en el mapa
                new_map[pos[0]][pos[1]] = f"T{taxi_id}_{state}"
        self.map = new_map

    def generate_ride_id(self):
        """Genera un ID único para cada viaje"""
        self.ride_counter += 1
        return f"RIDE_{self.ride_counter}"

    def assign_taxi(self, customer_request):
        """Asigna un taxi a una solicitud de cliente usando el optimizador"""
        customer_id = customer_request['customer_id']
        customer_position = customer_request.get('pickup_position', [1, 1])
        destination = customer_request['destination']

        # Usar el optimizador para encontrar el mejor taxi
        best_taxi_id, best_route, score = self.route_optimizer.assign_optimal_taxi(
            customer_request,
            self.taxis
        )
        
        if best_taxi_id:
            ride_id = self.generate_ride_id()
            
            # Actualizar estado del taxi
            self.taxis[best_taxi_id]['state'] = 'MOVING'
            self.taxis[best_taxi_id]['current_ride'] = ride_id
            
            # Registrar el viaje
            self.active_rides[ride_id] = {
                'customer_id': customer_id,
                'taxi_id': best_taxi_id,
                'pickup_position': customer_position,
                'destination': destination,
                'status': 'ASSIGNED',
                'route': best_route,
                'start_time': time.time()
            }
            
            # Enviar instrucción al taxi
            self.send_taxi_instruction(best_taxi_id, 'PICKUP', customer_position, best_route)
            
            response = {
                'status': 'OK',
                'message': f'Taxi {best_taxi_id} assigned',
                'ride_id': ride_id,
                'estimated_pickup_time': len(best_route)
            }
        else:
            # No hay taxis disponibles
            self.pending_queue.append(customer_request)
            response = {
                'status': 'QUEUED',
                'message': 'No taxis available, request queued',
                'queue_position': len(self.pending_queue)
            }
        
        return response

    def update_taxi_status(self, status):
        """Actualiza el estado de un taxi"""
        taxi_id = status.get('taxi_id')
        if not taxi_id:
            return

        old_state = self.taxis.get(taxi_id, {}).get('state')
        new_state = status.get('state')
        
        self.taxis[taxi_id] = {
            'position': status.get('position', [0, 0]),
            'state': new_state,
            'last_update': time.time(),
            'current_ride': self.taxis.get(taxi_id, {}).get('current_ride')
        }

        if old_state != 'IDLE' and new_state == 'IDLE':
            ride_id = self.taxis[taxi_id].get('current_ride')
            if ride_id and ride_id in self.active_rides:
                self.active_rides[ride_id]['status'] = 'COMPLETED'
                self.taxis[taxi_id]['current_ride'] = None

            # Procesar siguiente solicitud en cola
            if self.pending_queue:
                next_request = self.pending_queue.pop(0)
                self.process_customer_request(next_request)

        self.update_map()

    def send_taxi_instruction(self, taxi_id, instruction_type, destination, route=None):
        """Envía instrucciones a un taxi"""
        instruction = {
            'taxi_id': taxi_id,
            'type': instruction_type,
            'destination': destination,
            'route': route,
            'timestamp': time.time()
        }
        try:
            self.producer.produce('taxiinstructions', json.dumps(instruction).encode('utf-8'))
            self.producer.flush()
            print(f"Instruction sent to taxi {taxi_id}: {instruction}")
        except Exception as e:
            print(f"Error sending taxi instruction: {e}")

    def process_customer_request(self, request):
        """Procesa una solicitud de cliente"""
        print(f"Processing customer request: {request}")
        response = self.assign_taxi(request)
        try:
            self.producer.produce('centralresponses', json.dumps(response).encode('utf-8'))
            self.producer.flush()
            print(f"Response sent: {response}")
        except Exception as e:
            print(f"Error sending response: {e}")

    def process_message(self, msg):
        """Procesa los mensajes recibidos"""
        try:
            data = json.loads(msg.value().decode('utf-8'))
            if msg.topic() == 'taxistatus':
                self.update_taxi_status(data)
            elif msg.topic() == 'customerrequests':
                self.process_customer_request(data)
        except json.JSONDecodeError:
            print(f"Received invalid JSON: {msg.value().decode('utf-8')}")
        except Exception as e:
            print(f"Error processing message: {e}")

    def run(self):
        """Bucle principal del servicio"""
        print("Central service starting...")
        while self.is_running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"Consumer error: {msg.error()}")
                        continue
                
                self.process_message(msg)
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

    def shutdown(self):
        """Cierra el servicio de manera ordenada"""
        self.is_running = False
        self.consumer.close()
        self.producer.flush()

# Flask routes
@app.route('/')
def root():
    return "EasyCab Central Service is running"

@app.route('/health')
def health_check():
    if central_instance:
        return jsonify({"status": "OK"}), 200
    return jsonify({"status": "ERROR", "message": "Service not initialized"}), 500

@app.route('/map')
def get_map():
    if central_instance:
        return jsonify(central_instance.map)
    return jsonify({"error": "Service not initialized"}), 500

@app.route('/system/status')
def get_system_status():
    if not central_instance:
        return jsonify({"error": "Service not initialized"}), 500
    
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
    return jsonify({"error": "Service not initialized"}), 500

@app.route('/taxis/<taxi_id>')
def get_taxi_status(taxi_id):
    if not central_instance:
        return jsonify({"error": "Service not initialized"}), 500
    
    if taxi_id in central_instance.taxis:
        return jsonify(central_instance.taxis[taxi_id])
    return jsonify({'error': 'Taxi not found'}), 404

@app.route('/rides/active')
def get_active_rides():
    if central_instance:
        return jsonify({
            'active_rides': central_instance.active_rides,
            'total': len(central_instance.active_rides)
        })
    return jsonify({"error": "Service not initialized"}), 500

@app.route('/rides/<ride_id>')
def get_ride_status(ride_id):
    if not central_instance:
        return jsonify({"error": "Service not initialized"}), 500
    
    if ride_id in central_instance.active_rides:
        return jsonify(central_instance.active_rides[ride_id])
    return jsonify({'error': 'Ride not found'}), 404

@app.route('/queue/status')
def get_queue_status():
    if central_instance:
        return jsonify({
            'pending_requests': len(central_instance.pending_queue),
            'requests': central_instance.pending_queue
        })
    return jsonify({"error": "Service not initialized"}), 500

# Nuevos endpoints para control manual de taxis
@app.route('/taxi/control/<taxi_id>', methods=['POST'])
def control_taxi(taxi_id):
    if not central_instance:
        return jsonify({"error": "Service not initialized"}), 500
    
    if taxi_id not in central_instance.taxis:
        return jsonify({"error": "Taxi not found"}), 404
    
    action = request.json.get('action')
    if not action:
        return jsonify({"error": "No action specified"}), 400
    
    if action == 'stop':
        central_instance.send_taxi_instruction(taxi_id, 'STOP', None)
        return jsonify({"message": f"Stop instruction sent to taxi {taxi_id}"})
    elif action == 'resume':
        central_instance.send_taxi_instruction(taxi_id, 'RESUME', None)
        return jsonify({"message": f"Resume instruction sent to taxi {taxi_id}"})
    elif action == 'return':
        central_instance.send_taxi_instruction(taxi_id, 'RETURN', [1, 1])
        return jsonify({"message": f"Return to base instruction sent to taxi {taxi_id}"})
    else:
        return jsonify({"error": "Invalid action"}), 400

def wait_for_flask():
    time.sleep(2)

def run_flask():
    app.run(host='0.0.0.0', port=8000, use_reloader=False)

if __name__ == "__main__":
    central_instance = ECCentral()
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    wait_for_flask()
    
    try:
        central_instance.run()
    except KeyboardInterrupt:
        print("Shutting down...")
        central_instance.shutdown()
    except Exception as e:
        print(f"Error: {e}")
        central_instance.shutdown()