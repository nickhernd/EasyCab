import socket
import sys
import os
import json
import threading
import time
import logging
from typing import List, Dict, Optional

# Add the root directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.kafka_utils import KafkaClient, TOPICS, create_message

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Customer:
    def __init__(self, customer_id: str, kafka_url: str):
        self.customer_id = customer_id
        self.pending_services: List[str] = []
        self.current_service: Optional[str] = None
        self.assigned_taxi: Optional[int] = None
        self.service_status = None
        self.taxi_position = "Unknown"
        self.central_socket = None
        
        self.running = True
        self.lock = threading.Lock()
        
        # Kafka setup
        self.kafka = KafkaClient(kafka_url, f"customer_{customer_id}")
        self.setup_kafka()
        
        # UI
        self.display_lock = threading.Lock()
        
        # Load services
        self.load_services()

    def connect_to_central(self, host: str, port: int, retries: int = 3) -> bool:
        """Attempt to connect to the central server with retry logic."""
        for attempt in range(retries):
            try:
                logger.info(f"Connecting to central server {host}:{port} (Attempt {attempt+1}/{retries})")
                self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.central_socket.connect((host, port))
                
                # Send authentication data
                auth_data = {'type': 'customer', 'customer_id': self.customer_id}
                self.send_message(self.central_socket, auth_data)
                
                # Receive response
                response = self.receive_message(self.central_socket)
                if response.get('status') == 'OK':
                    logger.info("Successfully connected to central server")
                    return True
                logger.error(f"Connection error: {response}")
            except Exception as e:
                logger.error(f"Connection attempt {attempt+1} failed: {e}")
                time.sleep(1)
        
        # Reset central_socket to None if all attempts fail
        self.central_socket = None
        return False

    def setup_kafka(self):
        """Configure Kafka subscriptions."""
        self.kafka.subscribe(
            TOPICS['SERVICE_UPDATES'],
            self.handle_service_update,
            f"customer_{self.customer_id}_service"
        )
        self.kafka.subscribe(
            TOPICS['TAXI_POSITIONS'],
            self.handle_taxi_position,
            f"customer_{self.customer_id}_positions"
        )

    def load_services(self) -> bool:
        """Load services from a JSON file."""
        try:
            logger.info("Attempting to load services...")
            with open('data/EC_Requests.json', 'r') as f:
                data = json.load(f)
                self.pending_services = [req['Id'] for req in data['Requests']]
            logger.info(f"Loaded {len(self.pending_services)} services: {self.pending_services}")
            return True
        except Exception as e:
            logger.error(f"Error loading services: {e}")
            return False

    def request_service(self, destination: str) -> bool:
        """Request a taxi service."""
        if not self.central_socket:
            logger.error("Central server connection not established. Cannot request service.")
            return False

        try:
            request = {
                'type': 'service_request',
                'customer_id': self.customer_id,
                'destination': destination
            }
            self.send_message(self.central_socket, request)
            response = self.receive_message(self.central_socket)
            
            if response.get('status') == 'OK':
                self.current_service = response.get('service_id')
                self.assigned_taxi = response.get('taxi_id')
                self.display_message(f"Service accepted - Taxi {self.assigned_taxi} assigned")
                return True
            else:
                self.display_message(f"Service rejected: {response.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Error requesting service: {e}")
            return False

    def send_message(self, socket, message: dict):
        """Send a JSON-encoded message to a socket."""
        try:
            socket.send(json.dumps(message).encode())
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def receive_message(self, socket, buffer_size=1024) -> dict:
        """Receive a JSON-encoded message from a socket."""
        try:
            return json.loads(socket.recv(buffer_size).decode())
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return {}

    def handle_service_update(self, message: Dict):
        """Process a service update message from Kafka."""
        payload = message.get('payload', {})
        if payload.get('customer_id') == self.customer_id:
            update_type = payload.get('update_type')
            service_id = payload.get('service_id')
            
            handler_mapping = {
                'service_accepted': self.handle_service_accepted,
                'service_completed': self.handle_service_completed,
                'service_cancelled': self.handle_service_cancelled,
                'taxi_status': self.handle_taxi_status_update
            }
            handler = handler_mapping.get(update_type)
            if handler:
                handler(payload)
            else:
                logger.warning(f"Unhandled service update type: {update_type}")

    def handle_service_accepted(self, data: Dict):
        """Handle service acceptance updates."""
        with self.lock:
            self.current_service = data['service_id']
            self.assigned_taxi = data['taxi_id']
            self.service_status = 'ACCEPTED'
            self.display_message(f"Service accepted - Taxi {self.assigned_taxi}")

    def handle_service_completed(self, service_id: str):
        """Handle service completion updates."""
        if service_id == self.current_service:
            self.display_message(f"Service {service_id} completed")
            self.reset_service()
            threading.Timer(4.0, self.request_next_service).start()

    def reset_service(self):
        """Reset service variables to their default state."""
        self.current_service = None
        self.assigned_taxi = None
        self.service_status = None

    def handle_taxi_position(self, message: Dict):
        """Handle taxi position updates."""
        payload = message.get('payload', {})
        if payload.get('taxi_id') == self.assigned_taxi:
            self.taxi_position = payload.get('position', "Unknown")
            self.update_display()

    def request_next_service(self):
        """Request the next service in the pending queue."""
        with self.lock:
            if not self.pending_services:
                self.display_message("No more pending services")
                return
            
            destination = self.pending_services.pop(0)
            self.display_message(f"Requesting service to {destination}")
            if not self.request_service(destination):
                self.pending_services.insert(0, destination)
                threading.Timer(5.0, self.request_next_service).start()

    def display_message(self, message: str):
        """Display a message on the console."""
        with self.display_lock:
            print(f"\n{self.customer_id}: {message}")

    def update_display(self):
        """Update the user interface to show the current state."""
        with self.display_lock:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\n=== Customer {self.customer_id} ===")
            print(f"Current service: {self.current_service}")
            print(f"Status: {self.service_status}")
            print(f"Assigned taxi: {self.assigned_taxi}")
            print(f"Pending services: {len(self.pending_services)}")
            print(f"Taxi position: {self.taxi_position}")
            print("=" * 40)

    def run(self):
        """Start the customer client."""
        display_thread = threading.Thread(target=self.display_loop)
        display_thread.daemon = True
        display_thread.start()
        
        self.request_next_service()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()

    def display_loop(self):
        """Periodically refresh the display."""
        while self.running:
            self.update_display()
            time.sleep(1)

    def cleanup(self):
        """Clean up resources upon exiting."""
        self.running = False
        self.kafka.close()
        if self.central_socket:
            self.central_socket.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='EC_Customer: Taxi Client')
    
    parser.add_argument('kafka_ip', help='IP address of Kafka broker')
    parser.add_argument('kafka_port', type=int, help='Port of Kafka broker')
    parser.add_argument('customer_id', help='Customer ID')
    
    args = parser.parse_args()
    
    kafka_url = f"{args.kafka_ip}:{args.kafka_port}"
    customer = Customer(args.customer_id, kafka_url)
    customer.run()
