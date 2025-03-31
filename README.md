# Kafka-CrewAI-Integration

A system for capturing all agent interactions in a CrewAI debate application and streaming them to Kafka for real-time monitoring and analysis.

## Overview

This project integrates CrewAI, a framework for orchestrating role-playing AI agents, with Apache Kafka for comprehensive logging and monitoring. We've created a debate system where multiple AI agents engage in a structured debate on autonomous vehicles, with all their interactions captured and streamed to Kafka topics.

## Process Flow

1. **Setup**: Configure CrewAI agents and Kafka connection
2. **Debate Execution**: Run a hierarchical debate with multiple specialized agents
3. **Message Capture**: Intercept all agent communications using custom callbacks
4. **Kafka Publishing**: Stream captured messages to Kafka topics
5. **Monitoring**: View agent interactions in Kafka UI or process them with other systems

## File Structure

| File | Description |
|------|-------------|
| `crewai/crew.py` | Main application entry point; sets up and runs the CrewAI debate with Kafka integration |
| `crewai/agents.py` | Defines all AI agents with their roles, goals, and backstories for the debate |
| `crewai/tasks.py` | Defines the tasks each agent needs to complete as part of the debate |
| `crewai/kafka_utility.py` | Utilities for connecting to Kafka, creating producers/consumers, and publishing messages |
| `crewai/monitoring.py` | Functions for recording agent messages and managing the Kafka producer |
| `crewai/agent_logging.py` | Custom callbacks to intercept and log all CrewAI agent interactions |
| `crewai/Dockerfile` | Defines the container for running the CrewAI application |
| `utilities/docker-compose.yml` | Docker Compose configuration for setting up the entire environment |

## Key Features

- **Comprehensive Agent Monitoring**: Captures all agent thinking, communications, and task outputs
- **Real-time Message Streaming**: Publishes agent interactions to Kafka as they happen
- **Structured Debate Format**: Multi-agent debate with hierarchical task delegation
- **Error Handling**: Detailed error logging and recovery mechanisms
- **Containerized Deployment**: Complete Docker setup for easy deployment

## Running the Project

# Start the environment
docker-compose up -d

# View logs
docker-compose logs -f crewai-app

# Access Kafka UI (if configured)
# Visit http://localhost:8080