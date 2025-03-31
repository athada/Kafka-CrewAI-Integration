"""
Agent definitions for CrewAI debate system using YAML configuration
"""

import os
import yaml
from pathlib import Path
from crewai import Agent, LLM, Task
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_llm():
    """Configure the LLM for all agents"""
    # Get Ollama URL from environment or determine the best default
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    print(f"Connecting to Ollama at: {ollama_base_url}")
    
    # Set environment variables for CrewAI
    os.environ["CREWAI_LLM_PROVIDER"] = "ollama"
    os.environ.pop("OPENAI_API_KEY", None)  # Ensure no OpenAI key is set
    
    # Initialize using CrewAI's built-in LLM with Ollama provider
    return LLM(
        model="ollama/deepseek-r1",
        base_url=ollama_base_url,
        temperature=0.7
    )

def load_yaml_config(config_path):
    """Load YAML configuration from file"""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def create_agents():
    """Create all debate agents from YAML configuration"""
    llm = setup_llm()
    
    # Determine the config directory path
    # First check if there's a config directory in the current working directory
    config_dir = Path("config")
    
    # If not found, try relative to the script location
    if not config_dir.exists():
        script_dir = Path(__file__).parent
        config_dir = script_dir / "config"
    
    # If still not found, raise an error
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found. Expected at './config' or '{Path(__file__).parent}/config'")
    
    # Load agent configurations
    agent_config_path = config_dir / "agents.yml"
    
    if not agent_config_path.exists():
        raise FileNotFoundError(f"Agent configuration file not found at {agent_config_path}")
    
    agent_configs = load_yaml_config(agent_config_path)
    
    # Create agents from config
    agents = {}
    for agent_id, config in agent_configs.items():
        agents[agent_id] = Agent(
            role=config.get("role"),
            goal=config.get("goal"),
            backstory=config.get("backstory"),
            verbose=config.get("verbose", True),
            allow_delegation=config.get("allow_delegation", False),
            llm=llm,
            system_message=config.get("system_message")
        )
        print(f"Created agent: {agent_id}")
    
    return agents

def create_tasks(agents):
    """Create debate tasks from YAML configuration"""
    # Determine the config directory path
    # First check if there's a config directory in the current working directory
    config_dir = Path("config")
    
    # If not found, try relative to the script location
    if not config_dir.exists():
        script_dir = Path(__file__).parent
        config_dir = script_dir / "config"
    
    # If still not found, raise an error
    if not config_dir.exists():
        raise FileNotFoundError(f"Config directory not found. Expected at './config' or '{Path(__file__).parent}/config'")
    
    # Load task configurations
    task_config_path = config_dir / "tasks.yml"
    
    if not task_config_path.exists():
        raise FileNotFoundError(f"Task configuration file not found at {task_config_path}")
    
    task_configs = load_yaml_config(task_config_path)
    
    # Create tasks from config
    tasks = {}
    for task_id, config in task_configs.items():
        agent_id = config.get("agent")
        if agent_id not in agents:
            raise ValueError(f"Task {task_id} references unknown agent {agent_id}")
        
        tasks[task_id] = Task(
            description=config.get("description"),
            expected_output=config.get("expected_output"),
            agent=agents[agent_id]
        )
        print(f"Created task: {task_id} (assigned to {agent_id})")
    
    return tasks