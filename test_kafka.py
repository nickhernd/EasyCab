from confluent_kafka import Producer, Consumer, KafkaError
import json

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

def test_kafka():
    # Configuración del productor
    producer_conf = {'bootstrap.servers': 'localhost:9092'}
    producer = Producer(producer_conf)

    # Enviar un mensaje
    topic = 'test-topic'
    producer.produce(topic, json.dumps({'message': 'Hello, Kafka!'}).encode('utf-8'), callback=delivery_report)
    producer.flush()

    # Configuración del consumidor
    consumer_conf = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'mygroup',
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(consumer_conf)

    # Suscribirse al topic
    consumer.subscribe([topic])

    # Leer un mensaje
    try:
        msg = consumer.poll(timeout=5.0)
        if msg is None:
            print('No message received')
        elif msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                print('End of partition reached')
            else:
                print(f'Error: {msg.error()}')
        else:
            print(f'Received message: {msg.value().decode("utf-8")}')
    finally:
        consumer.close()

if __name__ == "__main__":
    test_kafka()