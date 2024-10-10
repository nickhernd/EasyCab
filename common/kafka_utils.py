
import json
from kafka import KafkaProducer, KafkaConsumer

def send_kafka_message(producer: KafkaProducer, topic: str, message: dict):
    """
    Envía un mensaje a un topic de Kafka.
    """
    producer.send(topic, json.dumps(message).encode('utf-8'))
    producer.flush()

def receive_kafka_message(message):
    """
    Decodifica un mensaje recibido de Kafka.
    """
    return json.loads(message.value.decode('utf-8'))

def create_kafka_producer(bootstrap_servers):
    """
    Crea y retorna un productor de Kafka.
    """
    return KafkaProducer(bootstrap_servers=bootstrap_servers)

def create_kafka_consumer(bootstrap_servers, topic):
    """
    Crea y retorna un consumidor de Kafka para un topic específico.
    """
    return KafkaConsumer(topic, bootstrap_servers=bootstrap_servers)