"""
Simple logging system for CrewAI system messages
"""

import time
from kafka_utility import publish_to_kafka, SYSTEM_MESSAGES_TOPIC

class CrewAILogger:
    """Simple logging system for CrewAI application"""
    
    def __init__(self, kafka_enabled=True):
        self.kafka_enabled = kafka_enabled
        self.system_logs = []
    
    def log_system_message(self, message: str, message_type: str = "info", send_to_kafka: bool = True):
        """Log system messages (not from agents)"""
        log_entry = {
            "timestamp": time.time(),
            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "message_type": message_type,
            "content": message
        }
        
        # Add to internal logs
        self.system_logs.append(log_entry)
        
        # Print to console
        print(f"[{log_entry['formatted_time']}] SYSTEM ({message_type}): {message}")
        
        # Publish to Kafka if enabled and requested
        if self.kafka_enabled and send_to_kafka:
            publish_to_kafka(SYSTEM_MESSAGES_TOPIC, log_entry)
    
    def get_system_logs(self):
        """Return all system logs collected so far"""
        return self.system_logs

# Create a global logger instance for use throughout the application
global_logger = CrewAILogger()