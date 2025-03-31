import time
from kafka import KafkaProducer

# Try both connection strings
connection_strings = ['localhost:9092', 'localhost:9094', '127.0.0.1:9092', '127.0.0.1:9094']

for conn in connection_strings:
    print(f"\nTrying to connect to: {conn}")
    try:
        producer = KafkaProducer(bootstrap_servers=conn)
        print(f"SUCCESS: Connected to Kafka at {conn}!")
        producer.close()
    except Exception as e:
        print(f"FAILED: Could not connect to {conn} - {str(e)}")
    time.sleep(1) 