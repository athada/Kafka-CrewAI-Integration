"""
Simple monitoring system for CrewAI agents
"""

import time
from kafka_utility import AGENT_MESSAGES_TOPIC, create_kafka_producer, publish_message

def record_agent_message(agent_id, agent_role, message_type, content, context=None):
    """Record an agent message to Kafka"""
    try:
        producer = create_kafka_producer()
        message_record = {
            "timestamp": time.time(),
            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_id": agent_id,
            "agent_role": agent_role,
            "message_type": message_type,
            "content": content[:500] + "..." if len(content) > 500 else content,
            "context": context or {}
        }
        publish_message(producer, AGENT_MESSAGES_TOPIC, message_record)
    except Exception as e:
        print(f"Error recording agent message: {e}")

def close_monitor():
    """Placeholder for compatibility"""
    pass 