#!/bin/bash
# Unified script to start CrewAI with or without Kafka
# Usage: ./start.sh [--kafka] [--debug]

# Default values
USE_KAFKA=false
DEBUG_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --kafka)
      USE_KAFKA=true
      shift # past argument
      ;;
    --debug)
      DEBUG_MODE=true
      shift # past argument
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./start.sh [--kafka] [--debug]"
      exit 1
      ;;
  esac
done

# Display startup information
if [ "$USE_KAFKA" = true ]; then
  echo "Starting CrewAI WITH Kafka integration"
else
  echo "Starting CrewAI in direct mode (NO Kafka)"
fi

if [ "$DEBUG_MODE" = true ]; then
  echo "Debug mode: ENABLED"
fi

# Make sure ollama is running first
./utilities/start_ollama.sh

# Export environment variables for Docker Compose
export DEBUG_MODE=$DEBUG_MODE

# Start the appropriate Docker Compose profile
if [ "$USE_KAFKA" = true ]; then
  echo "Starting with Kafka profile..."
  docker compose -f utilities/docker-compose.yml --profile kafka up
else
  echo "Starting with default profile..."
  docker compose -f utilities/docker-compose.yml --profile default up
fi 