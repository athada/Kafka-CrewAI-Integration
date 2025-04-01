"""
Unified Kafka monitoring and utility system for CrewAI agents
"""

import os
import json
import time
from dotenv import load_dotenv
import traceback

# Try importing Kafka, but provide fallbacks if not available
try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Kafka packages not available. Kafka functionality will be disabled.")

# Load environment variables
load_dotenv()

# Kafka Configuration
KAFKA_TOPIC = "debate_topic"
KAFKA_RESULT_TOPIC = "debate_topic_result"
AGENT_MESSAGES_TOPIC = "agent_messages"
SYSTEM_MESSAGES_TOPIC = "system_messages"
AGENT_RESPONSES_TOPIC = "agent_responses"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", 'localhost:9094')

# Global variables for monitoring
_producer = None
_use_kafka = None

# Kafka utility functions
def get_kafka_enabled():
    """Check if Kafka is enabled"""
    global _use_kafka
    if _use_kafka is None:
        # Check environment variable or command-line args
        _use_kafka = os.environ.get('USE_KAFKA', 'false').lower() == 'true'
    return _use_kafka and KAFKA_AVAILABLE

def set_kafka_enabled(enabled):
    """Set whether Kafka should be used"""
    global _use_kafka
    _use_kafka = enabled and KAFKA_AVAILABLE
    print(f"Kafka logging {'enabled' if enabled and KAFKA_AVAILABLE else 'disabled'}")
    if enabled and not KAFKA_AVAILABLE:
        print("Warning: Kafka enabled but Kafka packages not available")

def get_or_create_producer():
    """Get existing producer or create a new one"""
    if not get_kafka_enabled():
        return None
        
    global _producer
    if _producer is None:
        _producer = create_kafka_producer()
    return _producer

def create_kafka_producer(max_retries=3, retry_interval=3):
    """Create a Kafka producer with retry logic"""
    if not KAFKA_AVAILABLE or not get_kafka_enabled():
        return None

    for attempt in range(max_retries):
        try:
            print(f"Attempting to create Kafka producer (attempt {attempt+1}/{max_retries})")
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                api_version=(0, 10, 1),
                request_timeout_ms=30000
            )
            print("Successfully created Kafka producer!")
            return producer
        except Exception as e:
            print(f"Failed to create Kafka producer: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                print(f"ERROR: Failed to create Kafka producer after {max_retries} attempts")
                return None

def create_kafka_consumer(topic=KAFKA_TOPIC, max_retries=3, retry_interval=3):
    """Create a Kafka consumer with retry logic"""
    if not KAFKA_AVAILABLE or not get_kafka_enabled():
        return None

    for attempt in range(max_retries):
        try:
            print(f"Attempting to create Kafka consumer (attempt {attempt+1}/{max_retries})")
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                api_version=(0, 10, 1),
                request_timeout_ms=30000
            )
            print("Successfully created Kafka consumer!")
            return consumer
        except Exception as e:
            print(f"Failed to create Kafka consumer: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                print(f"ERROR: Failed to create Kafka consumer after {max_retries} attempts")
                return None

def publish_message(producer, topic, message):
    """Publish a message to a Kafka topic with error handling"""
    if not producer:
        return False

    try:
        # Ensure message is properly serializable
        if not isinstance(message, (str, dict)):
            if hasattr(message, '__dict__'):
                safe_message = {
                    "object_type": message.__class__.__name__,
                    "attributes": {k: str(v) for k, v in message.__dict__.items() if not k.startswith('_')}
                }
            else:
                safe_message = {
                    "object_type": type(message).__name__,
                    "string_representation": str(message)
                }
        else:
            safe_message = message
        
        # Add timeout parameters
        producer.send(topic, safe_message)
        producer.flush(timeout=5)
        print(f"Published message to Kafka topic: {topic}")
        return True
        
    except Exception as e:
        print(f"Error publishing message to {topic}: {e}")
        return False

def publish_to_kafka(topic, message):
    """Publish a message to a specific Kafka topic immediately"""
    if not get_kafka_enabled():
        return False
        
    try:
        producer = get_or_create_producer()
        if not producer:
            return False
        
        # Publish the message
        success = publish_message(producer, topic, message)
        return success
    except Exception as e:
        print(f"Error publishing to {topic}: {e}")
        return False

def close_monitor():
    """Close the Kafka producer if it exists"""
    if not get_kafka_enabled():
        return
        
    global _producer
    if _producer is not None:
        try:
            _producer.close()
            _producer = None
        except Exception as e:
            print(f"Error closing Kafka producer: {e}")

def record_agent_message(agent_id, agent_role, message_type, content, context=None):
    """Record an agent message to Kafka"""
    try:
        # Always print to console regardless of Kafka state
        if not isinstance(content, str):
            content = str(content)
            
        # Prepare for display (truncate for console)
        content_display = content[:100] + "..." if len(content) > 100 else content
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {agent_role} ({message_type}): {content_display}")
        
        # Only try to use Kafka if it's enabled
        if not get_kafka_enabled():
            return
            
        producer = get_or_create_producer()
        if not producer:
            return
        
        # Ensure context is a dict with simple types
        if context is None:
            context = {}
        elif not isinstance(context, dict):
            context = {"original_context": str(context)}
        else:
            context = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                      for k, v in context.items()}
        
        message_record = {
            "timestamp": time.time(),
            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_id": agent_id,
            "agent_role": agent_role,
            "message_type": message_type,
            "content": content,
            "context": context
        }
        
        publish_message(producer, AGENT_MESSAGES_TOPIC, message_record)
        
    except Exception as e:
        print(f"Error recording agent message: {e}")
        traceback.print_exc()

# Renamed this function to avoid the naming conflict
def publish_message_simple(message, topic=AGENT_MESSAGES_TOPIC):
    """Simplified function to publish a message"""
    publish_to_kafka(topic, message) 