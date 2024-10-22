from confluent_kafka import Producer, Consumer
import json
import time
import random

class TestClient:
    def __init__(self, client_id):
        self.client_id = client_id
        self.kafka_broker = 'kafka:9092'
        self.producer = Producer({'bootstrap.servers': self.kafka_broker})
        self.consumer = Consumer({
            'bootstrap.servers': self.kafka_broker,
            'group.id': f'testclient{client_id}',
            'auto.offset.reset': 'earliest'
        })
        time.sleep(5)  # Esperar a que los tópicos se creen
        self.consumer.subscribe(['centralresponses'])

    def send_request(self, destination):
        request = {
            'client_id': self.client_id,
            'destination': destination,
            'timestamp': time.time()
        }
        self.producer.produce('customerrequests', json.dumps(request).encode('utf-8'))
        self.producer.flush()
        print(f"Client {self.client_id} sent request to {destination}")

    def receive_response(self):
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue
            response = json.loads(msg.value().decode('utf-8'))
            print(f"Client {self.client_id} received response: {response}")
            break

    def run(self):
        destinations = ['A', 'B', 'C', 'D', 'E']
        for _ in range(5):  # Send 5 requests
            destination = random.choice(destinations)
            self.send_request(destination)
            self.receive_response()
            time.sleep(2)  # Wait 2 seconds between requests

if __name__ == "__main__":
    client = TestClient('1')
    client.run()