"""
Simple monitoring system for CrewAI agents
"""

import time
import os
from kafka_utility import AGENT_MESSAGES_TOPIC, create_kafka_producer, publish_message

# Keep track of producers to avoid creating new ones for every message
_producer = None
_use_kafka = None

def get_kafka_enabled():
    """Check if Kafka is enabled"""
    global _use_kafka
    if _use_kafka is None:
        # Check environment variable or command-line args
        # Default to False if not specified
        _use_kafka = os.environ.get('USE_KAFKA', 'false').lower() == 'true'
    return _use_kafka

def set_kafka_enabled(enabled):
    """Set whether Kafka should be used"""
    global _use_kafka
    _use_kafka = enabled
    print(f"Kafka logging {'enabled' if enabled else 'disabled'}")

def get_or_create_producer():
    """Get existing producer or create a new one"""
    if not get_kafka_enabled():
        return None
        
    global _producer
    if _producer is None:
        _producer = create_kafka_producer()
    return _producer

def record_agent_message(agent_id, agent_role, message_type, content, context=None):
    """Record an agent message to Kafka with improved object handling"""
    try:
        # Always print to console regardless of Kafka state
        if not isinstance(content, str):
            content = str(content)
            
        # Prepare the content for display
        content_display = content[:100] + "..." if len(content) > 100 else content
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {agent_role} ({message_type}): {content_display}")
        
        # Only try to use Kafka if it's enabled
        if not get_kafka_enabled():
            return
            
        producer = get_or_create_producer()
        if not producer:
            return
        
        # The rest of the function remains the same...
        if not isinstance(content, str):
            # If it's an object, try to convert it in a meaningful way
            if hasattr(content, '__class__') and 'AgentFinish' in content.__class__.__name__:
                # Special handling for AgentFinish objects
                if hasattr(content, 'return_values'):
                    content = f"Agent finished with values: {str(content.return_values)}"
                else:
                    content = f"Agent finished: {str(content)}"
            else:
                # Generic object conversion
                content = str(content)
            
        # Truncate if too long
        content = content[:1000] + "..." if len(content) > 1000 else content
        
        # Ensure context is a dict and contains only simple types
        if context is None:
            context = {}
        elif not isinstance(context, dict):
            context = {"original_context": str(context)}
        else:
            # Make sure all values in the context dict are simple types
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
        import traceback
        traceback.print_exc()

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

def publish_to_kafka(topic, message):
    """Publish a message to a specific Kafka topic immediately
    
    This is a helper function to publish messages in real-time
    """
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