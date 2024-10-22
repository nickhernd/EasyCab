from confluent_kafka import Producer, Consumer, KafkaError
import json
import threading
import time
from flask import Flask, jsonify, request
import os

app = Flask(__name__)

class ECCentral:
    def __init__(self):
        self.map = self.load_map()
        self.kafka_broker = os.environ.get('KAFKA_BROKER', 'kafka:9092')
        print(f"Connecting to Kafka at {self.kafka_broker}")
        
        # Configuración del productor con más opciones de debug
        producer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'debug': 'all'
        }
        self.producer = Producer(producer_conf)

        # Configuración del consumidor con más opciones de debug
        consumer_conf = {
            'bootstrap.servers': self.kafka_broker,
            'group.id': 'central',
            'auto.offset.reset': 'earliest',
            'debug': 'all'
        }
        self.consumer = Consumer(consumer_conf)
        
        self.topics = ['customerrequests', 'centralresponses']
        self.ensure_topics_exist(self.topics)
        self.consumer.subscribe(['customerrequests'])

    def ensure_topics_exist(self, topics):
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
        return [[0 for _ in range(20)] for _ in range(20)]

    def process_customer_request(self, request):
        print(f"Processing customer request: {request}")
        response = {'status': 'processing', 'message': 'Finding a taxi for you'}
        try:
            self.producer.produce('centralresponses', json.dumps(response).encode('utf-8'))
            self.producer.flush()
            print(f"Response sent: {response}")
        except Exception as e:
            print(f"Error sending response: {e}")

    def run(self):
        print("Central service starting...")
        while True:
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
                
                try:
                    request = json.loads(msg.value().decode('utf-8'))
                    self.process_customer_request(request)
                except json.JSONDecodeError:
                    print(f"Received invalid JSON: {msg.value().decode('utf-8')}")
                except Exception as e:
                    print(f"Error processing message: {e}")
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

@app.route('/')
def root():
    return "EasyCab Central Service is running"

@app.route('/health')
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route('/map')
def get_map():
    return jsonify(central.map)

def run_flask():
    app.run(host='0.0.0.0', port=8000)

if __name__ == "__main__":
    central = ECCentral()
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    try:
        central.run()
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")