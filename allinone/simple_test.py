from confluent_kafka import Consumer, KafkaError

c = Consumer({
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'mygroup',
    'auto.offset.reset': 'earliest'
})

c.subscribe(['taxi_updates', 'customer_updates', 'map_updates'])

while True:
    msg = c.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        print("Consumer error: {}".format(msg.error()))
        continue

    print('Received message: {}'.format(msg.value().decode('utf-8')))

c.close()