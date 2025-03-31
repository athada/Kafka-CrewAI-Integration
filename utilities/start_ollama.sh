#!/bin/bash
# Start Ollama service if it's not already running

# Check if Ollama is running
if pgrep -x "ollama" > /dev/null
then
    echo "Ollama is already running."
else
    echo "Starting Ollama service..."
    # Start Ollama in the background
    ollama serve &
    
    # Give Ollama a moment to start up
    sleep 2
    echo "Ollama started successfully."
fi

# Ensure the model is downloaded
echo "Ensuring deepseek-r1 model is available..."
ollama pull deepseek-r1 