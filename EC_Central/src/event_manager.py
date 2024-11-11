from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import time
import logging
from enum import Enum
import json
from kafka import KafkaProducer

class EventType(Enum):
    TAXI_REGISTERED = "TAXI_REGISTERED"
    TAXI_MOVED = "TAXI_MOVED"
    TAXI_STOPPED = "TAXI_STOPPED"
    TAXI_RESUMED = "TAXI_RESUMED"
    SERVICE_REQUESTED = "SERVICE_REQUESTED"
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_COMPLETED = "SERVICE_COMPLETED"
    TRAFFIC_UPDATE = "TRAFFIC_UPDATE"
    SENSOR_ALERT = "SENSOR_ALERT"
    MAP_UPDATED = "MAP_UPDATED"

@dataclass
class Event:
    type: EventType
    data: dict
    timestamp: float = time.time()
    source_id: str = None
    target_id: str = None

class EventManager:
    def __init__(self, kafka_server: str):
        self.logger = logging.getLogger('EC_Central.EventManager')
        self.handlers: Dict[EventType, List[Callable]] = {event_type: [] for event_type in EventType}
        self.event_history: List[Event] = []
        
        # Configurar Kafka
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_server],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )

    def register_handler(self, event_type: EventType, handler: Callable):
        """Registra un manejador para un tipo de evento"""
        self.handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for {event_type.value}")

    def dispatch_event(self, event: Event):
        """Procesa un evento y lo envía a los manejadores correspondientes"""
        self.logger.info(f"Processing event: {event.type.value}")
        self.event_history.append(event)

        # Enviar evento a Kafka
        try:
            self.producer.send(
                'events',
                {
                    'type': event.type.value,
                    'data': event.data,
                    'timestamp': event.timestamp,
                    'source_id': event.source_id,
                    'target_id': event.target_id
                }
            )
        except Exception as e:
            self.logger.error(f"Error sending event to Kafka: {e}")

        # Procesar con manejadores locales
        for handler in self.handlers[event.type]:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}")

    def get_recent_events(self, minutes: int = 5) -> List[Event]:
        """Obtiene eventos recientes para auditoría"""
        cutoff_time = time.time() - (minutes * 60)
        return [event for event in self.event_history if event.timestamp >= cutoff_time]

    def cleanup_old_events(self, hours: int = 24):
        """Limpia eventos antiguos"""
        cutoff_time = time.time() - (hours * 3600)
        self.event_history = [event for event in self.event_history 
                            if event.timestamp >= cutoff_time]