from confluent_kafka import Producer, Consumer

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

def test_kafka_connection():
    # Productor
    producer = Producer({'bootstrap.servers': 'localhost:9092'})
    producer.produce('test_topic', 'Hello, Kafka!', callback=delivery_report)
    producer.flush()

    # Consumidor
    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'test_group',
        'auto.offset.reset': 'earliest'
    })

    consumer.subscribe(['test_topic'])

    msg = consumer.poll(5.0)
    if msg is None:
        print('No message received')
    elif msg.error():
        print(f'Consumer error: {msg.error()}')
    else:
        print(f'Received message: {msg.value().decode("utf-8")}')

    consumer.close()

if __name__ == "__main__":
    test_kafka_connection()