"""
Main CrewAI application using Ollama integration with Kafka
"""

import os
import argparse
import functools
from crewai import Crew, Process
from dotenv import load_dotenv

# Import our modular components
from agents import create_agents, create_tasks
from callbacks import step_callback, get_log_count, set_kafka_enabled, _agent_id_to_role, _agent_role_to_id, _agent_roles
from kafka_utility import create_kafka_producer, create_kafka_consumer, publish_message, KAFKA_TOPIC, AGENT_MESSAGES_TOPIC, set_kafka_enabled as set_kafka_utility_enabled
from agent_logging import global_logger

# Load environment variables
load_dotenv()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run CrewAI with or without Kafka integration')
    parser.add_argument('--kafka', dest='use_kafka', action='store_true', 
                        help='Enable Kafka integration')
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
        
        # Log system message
        global_logger.log_system_message("Starting debate on autonomous vehicles", "debate_start")
        
        # Create Kafka consumer
        consumer = create_kafka_consumer()
        
        # Process messages
        global_logger.log_system_message("Waiting for messages...", "info")
        for message in consumer:
            global_logger.log_system_message(f"Received message: {message.value}", "kafka_received")
            
            # Execute the debate
            global_logger.log_system_message("Starting debate...", "debate_begin")
            crew_output = debate_crew.kickoff()
            
            # Extract the result as string from the CrewOutput object
            debate_result = str(crew_output)
            
            # Publish result back to Kafka
            result_data = {"result": debate_result}
            publish_message(producer, "debate_topic_result", result_data)
            
            # Log completion
            global_logger.log_system_message(
                f"Debate completed with {len(debate_result)} characters",
                "debate_complete"
            )
            
            # Only process one message
            break
        
        return "Debate completed. Results published to Kafka."
    
    except Exception as e:
        global_logger.log_system_message(f"Error running with Kafka: {e}", "error")
        raise

def run_direct(debate_crew):
    """Run the debate directly without Kafka"""
    try:
        # Execute the debate directly
        global_logger.log_system_message("Starting debate in direct mode (no Kafka)", "debate_begin")
        
        crew_output = debate_crew.kickoff()
        
        # Extract the result as string from the CrewOutput object
        debate_result = str(crew_output)
        
        global_logger.log_system_message("================== DEBATE TRANSCRIPT ==================", "info")
        global_logger.log_system_message(debate_result, "debate_transcript")
        global_logger.log_system_message("=======================================================", "info")
        
        # Log completion to console
        global_logger.log_system_message("DEBATE COMPLETE (DIRECT MODE)", "debate_complete")
        global_logger.log_system_message(
            f"Result length: {len(debate_result)} characters",
            "debate_stats"
        )
        
        return debate_result
    
    except Exception as e:
        global_logger.log_system_message(f"Error running directly: {e}", "error")
        raise

# Initialize agent IDs from config
def init_agent_ids():
    """Initialize agent IDs from the configured agents"""
    for agent_key, agent_role in _agent_roles.items():
        agent_id = agent_key.lower()
        _agent_id_to_role[agent_id] = agent_role
        _agent_role_to_id[agent_role] = agent_id
        print(f"Registered agent: {agent_id} -> {agent_role}")

def main():
    """Main application entry point"""
    args = parse_arguments()
    
    # Set the Kafka enabled flag
    set_kafka_utility_enabled(args.use_kafka)
    set_kafka_enabled(args.use_kafka)
    
    # Create agents and tasks
    agents = create_agents()
    tasks = create_tasks(agents)
    
    # Set up callback
    global_logger.log_system_message(f"Available task keys: {list(tasks.keys())}", "setup")
    global_logger.log_system_message(f"Available agent keys: {list(agents.keys())}", "setup")
    
    # Log application start
    global_logger.log_system_message(
        f"CrewAI application started {'with' if args.use_kafka else 'without'} Kafka", 
        "application_start"
    )
    
    # Call this function near the start of your script
    init_agent_ids()
    
    # Create the debate crew
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
        verbose=True,
        step_callback=step_callback  # Use our callback to capture all events
    )
    
    global_logger.log_system_message(f"Starting CrewAI debate {'with' if args.use_kafka else 'without'} Kafka", "crew_start")
    
    if args.use_kafka:
        result = run_with_kafka(debate_crew)
    else:
        result = run_direct(debate_crew)
    
    # Display total log count
    log_count = get_log_count()
    global_logger.log_system_message(f"Collected {log_count} callback log entries", "log_stats")
    
    return result

if __name__ == "__main__":
    main()
