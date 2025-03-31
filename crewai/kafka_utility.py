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

# Add a new topic for complete conversations
CONVERSATION_TOPIC = "complete_conversations"

# Add a dedicated topic for real-time agent responses
AGENT_RESPONSES_TOPIC = "agent_responses"

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
    """Publish a message to a Kafka topic with improved error handling"""
    try:
        # Ensure message is properly serializable
        if not isinstance(message, (str, dict)):
            # If it's a non-standard object, convert to a simpler representation
            if hasattr(message, '__dict__'):
                # Extract attributes from the object
                safe_message = {
                    "object_type": message.__class__.__name__,
                    "attributes": {k: str(v) for k, v in message.__dict__.items() if not k.startswith('_')}
                }
            else:
                # If it's not a simple object with __dict__, convert to string
                safe_message = {
                    "object_type": type(message).__name__,
                    "string_representation": str(message)
                }
        else:
            safe_message = message
        
        # Add timeout parameters to make sure we don't block forever
        producer.send(topic, safe_message)
        
        # Use a reasonable flush timeout - 5 seconds should be sufficient for most cases
        producer.flush(timeout=5)
        print(f"Published message to Kafka topic: {topic}")
        return True
        
    except Exception as e:
        print(f"Error publishing message to {topic}: {e}")
        # Don't raise the exception - just log it and continue
        # This prevents Kafka issues from breaking the main application flow
        return False 