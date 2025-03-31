"""
Kafka utility functions for CrewAI application
"""

import os
import json
import time
from kafka import KafkaProducer, KafkaConsumer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Kafka Configuration
KAFKA_TOPIC = "debate_topic"
KAFKA_RESULT_TOPIC = "debate_topic_result"
AGENT_MESSAGES_TOPIC = "agent_messages"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", 'localhost:9094')

def create_kafka_producer(max_retries=5, retry_interval=5):
    """Create a Kafka producer with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"Attempting to create Kafka producer (attempt {attempt+1}/{max_retries})")
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                api_version=(0, 10, 1),  # Specify API version if needed
                request_timeout_ms=30000  # 30 seconds timeout
            )
            print("Successfully created Kafka producer!")
            return producer
        except Exception as e:
            print(f"Failed to create Kafka producer: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                error_msg = f"ERROR: Failed to create Kafka producer after {max_retries} attempts: {e}"
                print(error_msg)
                raise RuntimeError(error_msg)

def create_kafka_consumer(topic=KAFKA_TOPIC, max_retries=5, retry_interval=5):
    """Create a Kafka consumer with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"Attempting to create Kafka consumer (attempt {attempt+1}/{max_retries})")
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                api_version=(0, 10, 1),  # Specify API version if needed
                request_timeout_ms=30000  # 30 seconds timeout
            )
            print("Successfully created Kafka consumer!")
            return consumer
        except Exception as e:
            print(f"Failed to create Kafka consumer: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                error_msg = f"ERROR: Failed to create Kafka consumer after {max_retries} attempts: {e}"
                print(error_msg)
                raise RuntimeError(error_msg)

def publish_message(producer, topic, message):
    """Publish a message to a Kafka topic"""
    try:
        producer.send(topic, message)
        producer.flush()
        print(f"Published message to Kafka topic: {topic}")
        return True
    except Exception as e:
        print(f"Error publishing message to {topic}: {e}")
        return False 