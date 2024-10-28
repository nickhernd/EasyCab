import time
from kafka import KafkaProducer, KafkaConsumer
import json
import logging
import threading
from typing import Callable, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self, broker_url: str, client_id: str):
        """
        Inicializar cliente Kafka
        
        Args:
            broker_url: URL del broker Kafka (host:port)
            client_id: Identificador único del cliente
        """
        self.broker_url = broker_url
        self.client_id = client_id
        self.producer = None
        self.consumers = {}
        self.running = True
        
        # Inicializar producer
        self.init_producer()

    def init_producer(self):
        """Inicializar el productor Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.broker_url,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                client_id=self.client_id
            )
            logger.info(f"Productor Kafka iniciado para {self.client_id}")
        except Exception as e:
            logger.error(f"Error iniciando productor Kafka: {e}")
            raise

    def publish(self, topic: str, message: Dict) -> bool:
        """
        Publicar mensaje en un topic
        
        Args:
            topic: Nombre del topic
            message: Mensaje a publicar
        Returns:
            bool: True si se publicó correctamente
        """
        try:
            # Añadir metadatos al mensaje
            message['client_id'] = self.client_id
            message['timestamp'] = time.time()
            
            # Enviar mensaje
            future = self.producer.send(topic, message)
            future.get(timeout=10)  # Esperar confirmación
            logger.debug(f"Mensaje publicado en {topic}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error publicando en {topic}: {e}")
            return False

    def subscribe(self, topic: str, handler: Callable[[Dict], None], group_id: Optional[str] = None):
        """
        Suscribirse a un topic
        
        Args:
            topic: Nombre del topic
            handler: Función que procesará los mensajes
            group_id: ID del grupo de consumidores (opcional)
        """
        try:
            if not group_id:
                group_id = f"{self.client_id}_group"
                
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.broker_url,
                group_id=group_id,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest'
            )
            
            self.consumers[topic] = consumer
            
            # Iniciar thread de consumo
            thread = threading.Thread(
                target=self._consume_messages,
                args=(consumer, handler),
                daemon=True
            )
            thread.start()
            
            logger.info(f"Suscrito a {topic} con grupo {group_id}")
        except Exception as e:
            logger.error(f"Error suscribiéndose a {topic}: {e}")
            raise

    def _consume_messages(self, consumer: KafkaConsumer, handler: Callable[[Dict], None]):
        """Consumir mensajes de un topic"""
        try:
            while self.running:
                # Obtener mensajes con timeout para poder cerrar limpiamente
                messages = consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            handler(record.value)
                        except Exception as e:
                            logger.error(f"Error procesando mensaje {record.value}: {e}")
        except Exception as e:
            logger.error(f"Error en consumidor: {e}")

    def close(self):
        """Cerrar conexiones de Kafka"""
        self.running = False
        
        if self.producer:
            self.producer.close()
            
        for consumer in self.consumers.values():
            consumer.close()

# Topics de Kafka
TOPICS = {
    'TAXI_POSITIONS': 'taxi_positions',    # Posiciones de taxis
    'TAXI_STATUS': 'taxi_status',         # Estados de taxis
    'CUSTOMER_REQUESTS': 'customer_requests',  # Solicitudes de servicio
    'SERVICE_UPDATES': 'service_updates',   # Actualizaciones de servicio
    'MAP_UPDATES': 'map_updates',         # Actualizaciones del mapa
    'SENSOR_DATA': 'sensor_data'          # Datos de sensores
}

# Utilidad para crear mensaje con formato estándar
def create_message(msg_type: str, payload: Dict) -> Dict:
    return {
        'type': msg_type,
        'payload': payload,
        'timestamp': time.time()
    }