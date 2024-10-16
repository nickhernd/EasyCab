from confluent_kafka import Producer, Consumer
import os

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

def test_kafka_connection():
    bootstrap_servers = 'localhost:9092'  # Cambiado de kafka:9092 a localhost:9092
    
    # Test Producer
    producer = Producer({'bootstrap.servers': bootstrap_servers})
    producer.produce('test_topic', 'Hello, Kafka!', callback=delivery_report)
    producer.flush()

    # Test Consumer
    consumer = Consumer({
        'bootstrap.servers': bootstrap_servers,
        'group.id': 'test_group',
        'auto.offset.reset': 'earliest'
    })

    consumer.subscribe(['test_topic'])

    try:
        msg = consumer.poll(5.0)
        if msg is None:
            print('No message received')
        elif msg.error():
            print(f'Consumer error: {msg.error()}')
        else:
            print(f'Received message: {msg.value().decode("utf-8")}')
    finally:
        consumer.close()

if __name__ == "__main__":
    test_kafka_connection()