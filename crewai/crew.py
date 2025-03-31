"""
Main CrewAI application using Ollama integration with Kafka
"""

import os
import argparse
import time
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

# Import our modular components
from agents import create_all_agents
from tasks import create_all_tasks
from kafka_utility import create_kafka_producer, create_kafka_consumer, publish_message, KAFKA_TOPIC, AGENT_MESSAGES_TOPIC
from monitoring import record_agent_message, close_monitor, set_kafka_enabled
from agent_logging import step_callback_handler, task_callback_handler, crew_callback_handler

# Load environment variables
load_dotenv()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run CrewAI with or without Kafka integration')
    parser.add_argument('--kafka', dest='use_kafka', action='store_true', 
                        help='Enable Kafka integration (default)')
    parser.add_argument('--no-kafka', dest='use_kafka', action='store_false',
                        help='Disable Kafka integration and run directly')
    parser.set_defaults(use_kafka=False)
    return parser.parse_args()

def run_with_kafka(debate_crew):
    """Run the debate with Kafka integration"""
    try:
        # Create Kafka producer
        producer = create_kafka_producer()
        
        # Produce the initial topic to Kafka
        topic_data = {"topic": "Will autonomous vehicles bring more benefits than risks to society?"}
        publish_message(producer, KAFKA_TOPIC, topic_data)
        
        # Also log to the agent messages topic
        system_message = {
            "timestamp": time.time(),
            "agent_role": "system",
            "message_type": "debate_start",
            "content": "Starting debate on autonomous vehicles",
        }
        publish_message(producer, AGENT_MESSAGES_TOPIC, system_message)
        
        # Create Kafka consumer
        consumer = create_kafka_consumer()
        
        # Process messages
        print("Waiting for messages...")
        for message in consumer:
            print(f"Received message: {message.value}")
            
            # Execute the debate
            print("Starting debate...")
            crew_output = debate_crew.kickoff()
            
            # Extract the result as string from the CrewOutput object
            debate_result = str(crew_output)
            
            # Publish result back to Kafka
            result_data = {"result": debate_result}
            publish_message(producer, "debate_topic_result", result_data)
            
            # Log completion
            system_message = {
                "timestamp": time.time(),
                "agent_role": "system",
                "message_type": "debate_complete",
                "content": f"Debate completed with {len(debate_result) if isinstance(debate_result, str) else 'unknown'} characters",
            }
            publish_message(producer, AGENT_MESSAGES_TOPIC, system_message)
            
            # Only process one message
            break
        
        return "Debate completed. Results published to Kafka."
    
    except Exception as e:
        print(f"Error running with Kafka: {e}")
        raise

def run_direct(debate_crew):
    """Run the debate directly without Kafka"""
    try:
        # Execute the debate directly
        print("\n\nStarting debate...")
        print("Running in direct mode (no Kafka)")
        
        # Simple console logging for direct mode
        print("\n==== STARTING DEBATE (DIRECT MODE) ====")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=======================================\n")
        
        crew_output = debate_crew.kickoff()
        
        # Extract the result as string from the CrewOutput object
        debate_result = str(crew_output)
        
        print("\n================== DEBATE TRANSCRIPT ==================")
        print(debate_result)
        print("=======================================================")
        
        # Log completion to console
        print("\n==== DEBATE COMPLETE (DIRECT MODE) ====")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Result type: {type(crew_output).__name__}")
        print(f"Result length: {len(debate_result) if isinstance(debate_result, str) else 'unknown'} characters")
        print("========================================\n")
        
        return debate_result
    
    except Exception as e:
        print(f"Error running directly: {e}")
        raise

def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Import here to avoid circular imports
    from monitoring import set_kafka_enabled
    # Set the Kafka enabled flag in monitoring module
    set_kafka_enabled(args.use_kafka)
    
    # Create agents and tasks
    agents = create_all_agents()
    tasks = create_all_tasks(agents)
    
    print(f"Available task keys: {list(tasks.keys())}")
    print(f"Available agent keys: {list(agents.keys())}")
    
    # Create Kafka monitoring only if using Kafka mode
    if args.use_kafka:
        # Create Kafka producer for monitoring
        producer = create_kafka_producer()
        
        # Log application start
        system_message = {
            "timestamp": time.time(),
            "agent_role": "system",
            "message_type": "application_start",
            "content": "CrewAI application started with Kafka",
        }
        publish_message(producer, AGENT_MESSAGES_TOPIC, system_message)
    else:
        print("Starting in direct mode (no Kafka)")
    
    # Create the debate crew with hierarchical debate process using actual task names
    debate_crew = Crew(
        agents=[
            agents["pro_debater"],
            agents["anti_debater"]
        ],
        tasks=[
            tasks["management_task"],    # Moderator's task
            tasks["pro_opening_task"],   # Pro debater's opening
            tasks["anti_rebuttal_task"], # Anti debater's rebuttal
            tasks["pro_counter_task"],   # Pro debater's counter
            tasks["anti_closing_task"]   # Anti debater's closing
        ],
        manager_agent=agents["moderator"],
        process=Process.sequential,
        verbose=False,
        # Add comprehensive callbacks for monitoring
        step_callback=step_callback_handler,
        task_callback=task_callback_handler,
        crew_callback=crew_callback_handler  # Add this new callback
    )
    
    print(f"Starting CrewAI debate {'with' if args.use_kafka else 'without'} Kafka")
    
    if args.use_kafka:
        result = run_with_kafka(debate_crew)
    else:
        result = run_direct(debate_crew)
    
    return result

if __name__ == "__main__":
    main()
