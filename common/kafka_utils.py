import json
from confluent_kafka import Producer, Consumer, KafkaException
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_kafka_message(producer: Producer, topic: str, message: dict):
    """
    Envía un mensaje a un topic de Kafka.
    """
    try:
        producer.produce(topic, json.dumps(message).encode('utf-8'))
        producer.flush()
        logger.info(f"Mensaje enviado exitosamente al topic '{topic}'")
    except KafkaException as e:
        logger.error(f"Error al enviar mensaje al topic '{topic}': {str(e)}")
        raise

def receive_kafka_message(message):
    """
    Decodifica un mensaje recibido de Kafka.
    """
    try:
        return json.loads(message.value().decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar el mensaje: {str(e)}")
        raise

def create_kafka_producer(bootstrap_servers):
    """
    Crea y retorna un productor de Kafka.
    """
    try:
        return Producer({'bootstrap.servers': bootstrap_servers})
    except KafkaException as e:
        logger.error(f"Error al crear el productor de Kafka: {str(e)}")
        raise

def create_kafka_consumer(bootstrap_servers, topic='easycab', group_id=None):
    """
    Crea y retorna un consumidor de Kafka para un topic específico.
    """
    try:
        consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id or 'easycab-group',
            'auto.offset.reset': 'earliest'
        })
        consumer.subscribe([topic])
        return consumer
    except KafkaException as e:
        logger.error(f"Error al crear el consumidor de Kafka: {str(e)}")
        raise