import time
from confluent_kafka import Producer

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

conf = {'bootstrap.servers': 'localhost:9092'}

producer = Producer(conf)

try:
    for i in range(10):
        message = f"Test message {i}"
        producer.produce('test-topic', message.encode('utf-8'), callback=delivery_report)
        producer.poll(0)
        time.sleep(1)

    print('Waiting for any outstanding messages to be delivered and delivery report callbacks to be triggered...')
    producer.flush()

except Exception as e:
    print(f"An error occurred: {e}")

print("Producer completed.")
