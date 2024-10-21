import os
import json
import time
from kafka import KafkaProducer, KafkaConsumer

class ECCustomer:
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self.kafka_broker = os.environ['KAFKA_BROKER']
        self.producer = KafkaProducer(bootstrap_servers=[self.kafka_broker])
        self.consumer = KafkaConsumer('customer_responses', bootstrap_servers=[self.kafka_broker])

    def request_taxi(self, destination):
        request = {
            'customer_id': self.customer_id,
            'destination': destination,
            'timestamp': time.time()
        }
        self.producer.send('customer_requests', json.dumps(request).encode())

    def listen_for_responses(self):
        for message in self.consumer:
            response = json.loads(message.value.decode())
            if response['customer_id'] == self.customer_id:
                print(f"Received response: {response}")
                # TODO: Handle the response (e.g., display to user, update UI)

    def run(self):
        # Read destinations from a file
        with open('destinations.txt', 'r') as f:
            destinations = f.readlines()

        for destination in destinations:
            self.request_taxi(destination.strip())
            time.sleep(4)  # Wait 4 seconds before next request

if __name__ == "__main__":
    customer_id = os.environ.get('CUSTOMER_ID', '1')
    customer = ECCustomer(customer_id)
    customer.run()