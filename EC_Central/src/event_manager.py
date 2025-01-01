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

