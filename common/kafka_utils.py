from kafka import KafkaProducer, KafkaConsumer
import json
from typing import Dict, Any, Callable
import logging
import time
from .config import KAFKA_BOOTSTRAP_SERVERS, TOPICS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaClient:
    def __init__(self, client_id: str):
        """
        Initialize Kafka client with producer and consumer capabilities
        
        Args:
            client_id (str): Unique identifier for this client
        """
        self.client_id = client_id
        self.producer = None
        self.consumers = {}
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                client_id=client_id
            )
            logger.info(f"Kafka producer initialized for {client_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    def publish_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish message to specified Kafka topic
        
        Args:
            topic (str): Topic to publish to
            message (Dict): Message to publish
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            message['client_id'] = self.client_id
            message['timestamp'] = time.time()
            
            future = self.producer.send(topic, message)
            future.get(timeout=10)  # Wait for message to be delivered
            logger.debug(f"Message published to {topic}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
            return False

    def subscribe_to_topic(self, topic: str, handler: Callable[[Dict], None], group_id: str = None) -> None:
        """
        Subscribe to a Kafka topic with a message handler
        
        Args:
            topic (str): Topic to subscribe to
            handler (Callable): Function to handle received messages
            group_id (str): Consumer group ID
        """
        try:
            if not group_id:
                group_id = f"{self.client_id}_group"
                
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest'
            )
            
            self.consumers[topic] = consumer
            
            # Start consumer thread
            import threading
            thread = threading.Thread(
                target=self._consume_messages,
                args=(consumer, handler),
                daemon=True
            )
            thread.start()
            
            logger.info(f"Subscribed to topic {topic} with group {group_id}")
        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {e}")
            raise

    def _consume_messages(self, consumer: KafkaConsumer, handler: Callable[[Dict], None]) -> None:
        """
        Internal method to consume messages from Kafka
        """
        try:
            for message in consumer:
                try:
                    handler(message.value)
                except Exception as e:
                    logger.error(f"Error handling message {message.value}: {e}")
        except Exception as e:
            logger.error(f"Consumer error: {e}")

    def close(self) -> None:
        """
        Close all Kafka connections
        """
        if self.producer:
            self.producer.close()
        
        for consumer in self.consumers.values():
            consumer.close()