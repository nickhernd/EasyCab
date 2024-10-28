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
    def __init__(self, customer_id: str, kafka_url: str, host: str, port: int):
        self.customer_id = customer_id
        self.host = host
        self.port = port
        self.pending_services: List[str] = []
        self.current_service: Optional[str] = None
        self.assigned_taxi: Optional[int] = None
        self.service_status = None
        self.taxi_position = "Unknown"
        self.central_socket = None  # Socket starts as None
        
        self.running = True
        self.lock = threading.Lock()
        
        # Kafka setup
        self.kafka = KafkaClient(kafka_url, f"customer_{customer_id}")
        self.setup_kafka()
        
        # UI
        self.display_lock = threading.Lock()
        
        # Load services
        self.load_services()

    def connect_to_central(self, retries: int = 3) -> bool:
        """Attempt to connect to the central server with retry logic."""
        # Close any existing socket before reconnecting
        if self.central_socket:
            self.central_socket.close()

        self.central_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        for attempt in range(retries):
            try:
                logger.info(f"Connecting to central server {self.host}:{self.port} (Attempt {attempt+1}/{retries})")
                self.central_socket.connect((self.host, self.port))
                
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
        
        # If connection fails, close the socket and set it to None
        self.central_socket.close()
        self.central_socket = None
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

    def request_next_service(self):
        """Request the next service in the pending queue with connection check."""
        with self.lock:
            # Ensure connection before requesting service
            if not self.central_socket and not self.connect_to_central():
                self.display_message("Unable to connect to central server. Retrying...")
                threading.Timer(5.0, self.request_next_service).start()
                return
            
            if not self.pending_services:
                self.display_message("No more pending services")
                return
            
            destination = self.pending_services.pop(0)
            self.display_message(f"Requesting service to {destination}")
            if not self.request_service(destination):
                self.pending_services.insert(0, destination)
                threading.Timer(5.0, self.request_next_service).start()

    def send_message(self, socket, message: dict):
        """Send a JSON-encoded message to a socket."""
        if socket:
            try:
                socket.send(json.dumps(message).encode())
            except Exception as e:
                logger.error(f"Error sending message: {e}")
        else:
            logger.error("Attempted to send message on a closed or uninitialized socket.")

    def receive_message(self, socket, buffer_size=1024) -> dict:
        """Receive a JSON-encoded message from a socket."""
        if socket:
            try:
                return json.loads(socket.recv(buffer_size).decode())
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                return {}
        else:
            logger.error("Attempted to receive message on a closed or uninitialized socket.")
            return {}

    def run(self):
        """Start the customer client and ensure connection to central server."""
        # Attempt to connect to the central server before proceeding
        if not self.connect_to_central():
            logger.error("Failed to connect to central server. Exiting client.")
            self.running = False
            return  # Exit if unable to connect

        # Start the display thread
        display_thread = threading.Thread(target=self.display_loop)
        display_thread.daemon = True
        display_thread.start()
        
        # Start requesting the first service
        self.request_next_service()
        
        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()

    def cleanup(self):
        """Clean up resources upon exiting."""
        self.running = False
        self.kafka.close()
        if self.central_socket:
            try:
                self.central_socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
            finally:
                self.central_socket = None

    def setup_kafka(self):
        self.kafka = KafkaClient(self.kafka_url, f"customer_{self.customer_id}")
        logger.info("Kafka setup completed")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='EC_Customer: Taxi Client')
    
    parser.add_argument('kafka_ip', help='IP address of Kafka broker')
    parser.add_argument('kafka_port', type=int, help='Port of Kafka broker')
    parser.add_argument('customer_id', help='Customer ID')
    parser.add_argument('central_host', help='IP address of Central Server')
    parser.add_argument('central_port', type=int, help='Port of Central Server')
    
    args = parser.parse_args()
    
    kafka_url = f"{args.kafka_ip}:{args.kafka_port}"
    customer = Customer(args.customer_id, kafka_url, args.central_host, args.central_port)
    customer.run()
