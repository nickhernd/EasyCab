import os
import json
from kafka import KafkaProducer, KafkaConsumer
import mysql.connector

class ECCentral:
    def __init__(self):
        self.kafka_broker = os.environ['KAFKA_BROKER']
        self.producer = KafkaProducer(bootstrap_servers=[self.kafka_broker])
        self.consumer = KafkaConsumer('customer_requests', bootstrap_servers=[self.kafka_broker])
        self.db = mysql.connector.connect(
            host=os.environ['DB_HOST'],
            port=os.environ['DB_PORT'],
            user="root",
            password="rootpassword",
            database="easycab"
        )
        self.cursor = self.db.cursor()

    def run(self):
        print("EC_Central is running...")
        for message in self.consumer:
            request = json.loads(message.value.decode())
            self.process_request(request)

    def process_request(self, request):
        # Process the customer request
        # For now, just print it
        print(f"Received request: {request}")
        
        # TODO: Implement logic to assign taxi, update database, etc.

    def send_response(self, customer_id, response):
        self.producer.send('customer_responses', json.dumps(response).encode())

if __name__ == "__main__":
    central = ECCentral()
    central.run()