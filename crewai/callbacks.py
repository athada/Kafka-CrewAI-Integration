"""
Enhanced CrewAI callback system with accurate performance metrics and agent role tracking
"""

import time
import re
import uuid
import json
import hashlib
from typing import Any, Dict, Optional
from agent_logging import global_logger
from kafka_utility import publish_to_kafka, AGENT_MESSAGES_TOPIC, AGENT_RESPONSES_TOPIC, SYSTEM_MESSAGES_TOPIC

# Track statistics
_callback_count = 0
_kafka_enabled = True  # Set to True by default to ensure Kafka publishing works
_debug_mode = False  # Set to True to enable extra debug logging
_token_tracking_enabled = True  # Default to enabling token tracking
_token_usage = {}  # Store token usage by agent_id and task_id
_step_start_times = {}  # Track start times for steps to calculate duration
_agent_task_map = {}    # Map agents to their current tasks
_last_agent_activity = {}  # Track when we last saw activity from each agent
_agent_prompts = {}  # Track input prompts for each agent
_seen_responses = set()  # Avoid duplicates
_all_agent_interactions = []  # Track all agent interactions for debugging
_agent_roles = {
    "moderator": "Debate Moderator",
    "pro_debater": "Pro-Autonomous Vehicle Advocate",
    "anti_debater": "Autonomous Vehicle Skeptic"
}  # Based on the agents.yml config

# More distinct default prompts for each role
_default_prompts = {
    "Pro-Autonomous Vehicle Advocate": """As the Pro-AV Advocate, focus on:
    • Safety improvements
    • Efficiency gains
    • Accessibility benefits
    • Environmental advantages
    • Economic opportunities
    
    RESPONSE LIMIT: 400 WORDS MAX. Be concise and persuasive.""",
    
    "Autonomous Vehicle Skeptic": """As the AV Skeptic, focus on:
    • Safety concerns
    • Cybersecurity threats
    • Job displacement issues
    • Technological limitations
    • Ethical dilemmas
    • Infrastructure challenges
    
    RESPONSE LIMIT: 400 WORDS MAX. Be concise and persuasive.""",
    
    "Debate Moderator": """Format delegation requests as simple string values, not nested dictionaries.
    
    After the debate concludes, choose one side as the winner based on the strength 
    of their arguments. Justify your decision with specific points from the debate.
    
    RESPONSE LIMIT: 400 WORDS MAX. Be concise."""
}

# IMPROVED: More distinct agent role patterns
_role_mappings = {
    "moderator": "Debate Moderator",
    "pro_debater": "Pro-Autonomous Vehicle Advocate",
    "anti_debater": "Autonomous Vehicle Skeptic",
    "debate moderator": "Debate Moderator",
    "pro-autonomous": "Pro-Autonomous Vehicle Advocate",
    "autonomous vehicle skeptic": "Autonomous Vehicle Skeptic",
    "pro advocate": "Pro-Autonomous Vehicle Advocate",
    "av advocate": "Pro-Autonomous Vehicle Advocate",
    "av skeptic": "Autonomous Vehicle Skeptic",
    "facilitate": "Debate Moderator"
}

# Task pattern mapping - ENHANCED with more patterns
_task_role_map = {
    "opening": "Pro-Autonomous Vehicle Advocate",
    "rebuttal": "Autonomous Vehicle Skeptic",
    "counter": "Pro-Autonomous Vehicle Advocate",
    "closing": "Autonomous Vehicle Skeptic",
    "management": "Debate Moderator",
    "introduce": "Debate Moderator",
    "facilitate": "Debate Moderator",
    "advocate for": "Pro-Autonomous Vehicle Advocate",
    "present case": "Pro-Autonomous Vehicle Advocate",
    "argue against": "Autonomous Vehicle Skeptic",
    "critique": "Autonomous Vehicle Skeptic" 
}

def set_kafka_enabled(enabled):
    """Set whether Kafka should be used"""
    global _kafka_enabled
    _kafka_enabled = enabled
    print(f"Kafka publishing {'enabled' if enabled else 'disabled'}")

def get_log_count():
    """Return the number of callbacks logged"""
    global _callback_count
    return _callback_count

def debug_log(message):
    """Log debug messages if debug mode is enabled"""
    if _debug_mode:
        global_logger.log_system_message(
            message=f"DEBUG: {message}",
            message_type="agent_debug",
            send_to_kafka=False  # Don't flood Kafka with debug logs
        )

def agent_role_from_content(content):
    """Determine agent role from content patterns"""
    if not content:
        return None
        
    # Check role indicators in content
    if "as the debate moderator" in content.lower() or "facilitate this debate" in content.lower():
        return "Debate Moderator"
    elif any(x in content.lower() for x in ["support autonomous", "advocate for autonomous", "benefits of autonomous"]):
        return "Pro-Autonomous Vehicle Advocate"
    elif any(x in content.lower() for x in ["risks of autonomous", "concerns about autonomous", "against autonomous"]):
        return "Autonomous Vehicle Skeptic"
        
    return None

def generate_unique_agent_id(role, content=None):
    """Generate a unique, stable ID for an agent based on role and content patterns"""
    # Create a base ID from the role
    base_id = role.replace(" ", "_").lower()
    
    # Add content fingerprint if available
    if content:
        # Create a content fingerprint by looking for characteristic phrases
        fingerprint = ""
        if "moderator" in content.lower() or "facilitate" in content.lower():
            fingerprint = "mod"
        elif "advocate" in content.lower() or "support" in content.lower():
            fingerprint = "pro"
        elif "skeptic" in content.lower() or "concern" in content.lower():
            fingerprint = "anti"
        
        # Add fingerprint to base ID
        if fingerprint:
            base_id = f"{base_id}_{fingerprint}"
    
    # Create a stable hash from the base ID
    agent_id = hashlib.md5(base_id.encode()).hexdigest()[:8]
    return agent_id

def get_agent_prompt(agent_role):
    """Get the system prompt for an agent based on its role"""
    # First try exact match
    if agent_role in _agent_prompts:
        return _agent_prompts[agent_role]
    
    # Try partial match
    for role, prompt in _agent_prompts.items():
        if role in agent_role or agent_role in role:
            return prompt
    
    # Default prompt if no match
    return "You are an AI assistant participating in a debate. Be concise, clear, and persuasive."

def publish_agent_response(agent_role, message_type, content, metrics=None):
    """Publish an agent response to Kafka"""
    try:
        if not _kafka_enabled:
            return
            
        # Format agent_id consistently
        agent_id = agent_role.replace(" ", "_").lower() if agent_role else "unknown_agent"
        
        # Extract metrics
        input_tokens = metrics.get("input_tokens", 0) if metrics else 0
        output_tokens = metrics.get("output_tokens", 0) if metrics else 0
        
        # If no input tokens were provided, estimate them
        if _token_tracking_enabled and input_tokens <= 0:
            input_prompt = get_agent_prompt(agent_role)
            input_tokens = estimate_tokens(input_prompt)
            
        # Create message record
        message_record = {
            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_id": agent_id,
            "agent_role": agent_role,
            "message_type": message_type,
            "content": content
        }
        
        # Add token metrics if available
        if _token_tracking_enabled and (input_tokens > 0 or output_tokens > 0):
            message_record["token_info"] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "estimated": metrics is None or "estimated" in metrics
            }
            
        # Generate unique key for timing
        step_key = f"{agent_id}:{message_type}:{int(time.time())}"
        record_step_start(step_key)
            
        # Publish to Kafka
        print(f"Publishing agent response: {agent_role} ({message_type})")
        publish_to_kafka_with_timestamps(AGENT_RESPONSES_TOPIC, message_record, step_key)
            
        # Mark as completed
        record_step_end(step_key)
            
    except Exception as e:
        print(f"Error publishing agent response: {e}")
        import traceback
        traceback.print_exc()

def extract_agent_info(obj):
    """Extract agent ID and role from a CrewAI step object"""
    # Print object type for debugging
    obj_type = type(obj).__name__
    print(f"Extracting agent info from object of type: {obj_type}")
    
    # Handle AgentFinish objects
    if 'AgentFinish' in obj_type:
        # Look for agent name in the object representation
        obj_str = str(obj)
        for agent_id, role in _agent_roles.items():
            if agent_id.lower() in obj_str.lower() or role.lower() in obj_str.lower():
                print(f"Found agent {role} via string matching")
                return agent_id, role
    
    # Direct agent attribute access
    if hasattr(obj, 'agent') and obj.agent:
        agent = obj.agent
        print(f"Found agent attribute: {agent}")
        
        # Check for role attribute
        if hasattr(agent, 'role') and agent.role:
            role = agent.role
            # Format agent_id from role
            agent_id = role.replace(" ", "_")
            print(f"Extracted agent info from role: {agent_id}, {role}")
            return agent_id, role
            
        # Check for name attribute
        if hasattr(agent, 'name') and agent.name:
            name = agent.name
            # Map name to role if possible
            for agent_id, role in _agent_roles.items():
                if agent_id.lower() in name.lower() or role.lower() in name.lower():
                    print(f"Mapped agent name {name} to role {role}")
                    return agent_id, role
            
            # If no mapping, use name directly
            agent_id = name.replace(" ", "_")
            print(f"Using agent name directly: {agent_id}, {name}")
            return agent_id, name
    
    # For dictionary-style objects
    if isinstance(obj, dict) and 'agent' in obj:
        agent = obj['agent']
        print(f"Found agent in dictionary: {agent}")
        
        if isinstance(agent, dict):
            # Check for role in dict
            if 'role' in agent and agent['role']:
                role = agent['role']
                agent_id = role.replace(" ", "_")
                print(f"Extracted agent info from dict role: {agent_id}, {role}")
                return agent_id, role
                
            # Check for name in dict
            if 'name' in agent and agent['name']:
                name = agent['name']
                # Try to map to known role
                for agent_id, role in _agent_roles.items():
                    if agent_id.lower() in name.lower() or role.lower() in name.lower():
                        print(f"Mapped agent dict name {name} to role {role}")
                        return agent_id, role
                
                # If no mapping, use name directly
                agent_id = name.replace(" ", "_")
                print(f"Using agent dict name directly: {agent_id}, {name}")
                return agent_id, name
    
    # Check for task-related info that might indicate agent
    if hasattr(obj, 'task') and obj.task:
        task = obj.task
        task_str = str(task)
        print(f"Checking task for agent info: {task_str[:50]}...")
        
        # Look for agent indicators in task string
        for agent_id, role in _agent_roles.items():
            if agent_id.lower() in task_str.lower() or role.lower() in task_str.lower():
                print(f"Found agent {role} via task matching")
                return agent_id, role
    
    # Last resort - check object string representation for known roles
    obj_str = str(obj)
    print(f"Checking object string: {obj_str[:50]}...")
    
    # Look for specific role patterns
    if "pro" in obj_str.lower() and ("advocate" in obj_str.lower() or "debater" in obj_str.lower()):
        print("Detected Pro-Autonomous Vehicle Advocate in string")
        return "pro_debater", "Pro-Autonomous Vehicle Advocate"
    elif "skeptic" in obj_str.lower() or "anti" in obj_str.lower():
        print("Detected Autonomous Vehicle Skeptic in string")
        return "anti_debater", "Autonomous Vehicle Skeptic"
    elif "moderator" in obj_str.lower() or "debate" in obj_str.lower():
        print("Detected Debate Moderator in string")
        return "moderator", "Debate Moderator"
    
    # Final fallback - try to parse from detailed object inspection
    print("Using fallback agent detection")
    if hasattr(obj, "__dict__"):
        for attr_name, attr_value in obj.__dict__.items():
            attr_str = str(attr_value)
            if "pro" in attr_str.lower() and "advocate" in attr_str.lower():
                return "pro_debater", "Pro-Autonomous Vehicle Advocate"
            elif "skeptic" in attr_str.lower():
                return "anti_debater", "Autonomous Vehicle Skeptic"
            elif "moderator" in attr_str.lower():
                return "moderator", "Debate Moderator"
    
    # Ultimate fallback
    print("Could not determine agent, using Unknown")
    return "unknown_agent", "Unknown Agent"

def step_callback(step_output=None, step_name=None):
    """Universal CrewAI step callback handling all interaction types"""
    global _callback_count
    _callback_count += 1
    
    try:
        # 1. Extract content - safe handling for different object types
        content = extract_content(step_output)
        
        # 2. Extract agent information
        agent_id, agent_role = extract_agent_info(step_output)
        
        # 3. Extract task information
        task_id, task_description = extract_task_info(step_output)
        
        # Create a unique step key for tracking timing
        step_key = get_step_key(agent_id, task_id, step_name)
        record_step_start(step_key)
        
        # 4. Token usage tracking
        token_info = None
        if _token_tracking_enabled:
            # Try to extract token counts directly
            input_tokens = 0
            output_tokens = 0
            is_estimated = True
            
            # Try to get token counts from the step output
            if hasattr(step_output, 'token_usage'):
                token_usage = step_output.token_usage
                if token_usage:
                    if isinstance(token_usage, dict):
                        input_tokens = token_usage.get('prompt_tokens', 0)
                        output_tokens = token_usage.get('completion_tokens', 0)
                        is_estimated = False
                    elif hasattr(token_usage, 'prompt_tokens'):
                        input_tokens = token_usage.prompt_tokens
                        output_tokens = token_usage.completion_tokens
                        is_estimated = False
            
            # If not available, estimate based on content length
            if output_tokens <= 0 and content:
                output_tokens = estimate_tokens(content)
                
            # If input tokens not available, estimate based on role and task
            if step_name in ["thinking", "answering", "final_answer"] and input_tokens < 100:
                input_tokens = estimate_default_prompt_tokens(agent_role, task_description)
                is_estimated = True
                
            token_info = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "estimated": is_estimated
            }
            
            # Update token usage tracking
            if input_tokens > 0 or output_tokens > 0:
                usage_key = f"{agent_id}:{task_id}"
                
                if usage_key not in _token_usage:
                    _token_usage[usage_key] = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    }
                
                _token_usage[usage_key]["input_tokens"] += input_tokens
                _token_usage[usage_key]["output_tokens"] += output_tokens
                _token_usage[usage_key]["total_tokens"] += (input_tokens + output_tokens)
                
            # Log token usage in debug mode
            if _debug_mode and (input_tokens > 0 or output_tokens > 0):
                debug_msg = (
                    f"Token usage for {agent_role} ({step_name}): "
                    f"Input={input_tokens}, Output={output_tokens}, "
                    f"Total={input_tokens + output_tokens}, "
                    f"Estimated={is_estimated}"
                )
                global_logger.log_system_message(debug_msg, "token_debug")
        
        # 5. Log based on step type
        if step_name == "thinking":
            # Agent thinking step
            event_type = "agent_thinking"
            message = f"{agent_role} thinking: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
            # Force publish to Kafka AGENT_RESPONSES_TOPIC
            print(f"Publishing thinking step for {agent_role}")
            record = {
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_id": agent_id,
                "agent_role": agent_role,
                "message_type": event_type,
                "content": content
            }
            
            if token_info:
                record["token_info"] = token_info
                
            publish_to_kafka_with_timestamps(AGENT_RESPONSES_TOPIC, record, step_key)
            
        elif step_name == "answering":
            # Agent answer/response
            event_type = "agent_answering"
            message = f"{agent_role} answering: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
            # Force publish to Kafka AGENT_RESPONSES_TOPIC
            print(f"Publishing answering step for {agent_role}")
            record = {
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_id": agent_id,
                "agent_role": agent_role,
                "message_type": event_type,
                "content": content
            }
            
            if token_info:
                record["token_info"] = token_info
                
            publish_to_kafka_with_timestamps(AGENT_RESPONSES_TOPIC, record, step_key)
            
        elif step_name == "final_answer":
            # Final answer/result from agent
            event_type = "agent_final_answer"
            message = f"{agent_role} final answer: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
            # Force publish to Kafka AGENT_RESPONSES_TOPIC
            print(f"Publishing final answer for {agent_role}")
            record = {
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_id": agent_id,
                "agent_role": agent_role,
                "message_type": event_type,
                "content": content
            }
            
            if token_info:
                record["token_info"] = token_info
                
            publish_to_kafka_with_timestamps(AGENT_RESPONSES_TOPIC, record, step_key)
            
        elif step_name == "task_complete":
            # Task completed
            event_type = "task_complete"
            message = f"Task completed by {agent_role}: {task_description}"
            global_logger.log_system_message(message, event_type)
            
            # Get total token usage for this task
            task_tokens = {}
            for key, usage in _token_usage.items():
                if key.endswith(f":{task_id}"):
                    task_tokens = {
                        "input_tokens": task_tokens.get("input_tokens", 0) + usage["input_tokens"],
                        "output_tokens": task_tokens.get("output_tokens", 0) + usage["output_tokens"],
                        "total_tokens": task_tokens.get("total_tokens", 0) + usage["total_tokens"]
                    }
            
            # Force publish to Kafka
            print(f"Publishing task complete for {agent_role}")
            record = {
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_id": agent_id,
                "agent_role": agent_role,
                "message_type": event_type,
                "task_id": task_id,
                "task": task_description,
                "content": content
            }
            
            if task_tokens:
                record["token_info"] = task_tokens
                
            publish_to_kafka_with_timestamps(AGENT_MESSAGES_TOPIC, record, step_key)
                
            # Clean up step timing data for this task
            for key in list(_step_start_times.keys()):
                if f":{task_id}:" in key:
                    del _step_start_times[key]
            
        else:
            # Generic event
            event_type = f"agent_step_{step_name}" if step_name else "agent_event"
            message = f"{agent_role} {step_name}: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
            # Force publish to Kafka
            print(f"Publishing generic step {step_name} for {agent_role}")
            record = {
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_id": agent_id,
                "agent_role": agent_role,
                "message_type": event_type,
                "content": content
            }
            
            if token_info:
                record["token_info"] = token_info
                
            publish_to_kafka_with_timestamps(AGENT_MESSAGES_TOPIC, record, step_key)
            
            # Special handling for debugging in CrewAI initial callbacks
            if step_name == "CrewAI" and _debug_mode:
                msg_type = "crew_debug"
                print(f"Publishing crew debug message")
                publish_agent_response("CrewAI-System", msg_type, content)
        
        # Mark step as ended
        record_step_end(step_key)
        
        # Return the original output
        return step_output
        
    except Exception as e:
        # Log the error but don't break the flow
        error_msg = f"Error in callback: {str(e)}"
        print(error_msg)
        global_logger.log_system_message(
            message=error_msg,
            message_type="callback_error"
        )
        import traceback
        traceback.print_exc()
        return step_output

def extract_content(obj):
    """Extract content from an object (supports multiple formats)"""
    # Print object type for debugging
    obj_type = type(obj).__name__
    print(f"Extracting content from object of type: {obj_type}")
    
    # Handle AgentFinish objects properly (common in CrewAI)
    if 'AgentFinish' in obj_type:
        print("Found AgentFinish object, extracting return values")
        if hasattr(obj, 'return_values'):
            values = obj.return_values
            if isinstance(values, dict):
                if 'output' in values:
                    return values['output']
                elif 'content' in values:
                    return values['content']
                elif 'response' in values:
                    return values['response']
                else:
                    # Return first value if we can't identify the right key
                    first_key = next(iter(values), None)
                    if first_key:
                        return values[first_key]
        
        # Try direct string representation, might contain the actual output
        obj_str = str(obj)
        if not obj_str.startswith("<") and len(obj_str) > 15:
            return obj_str
    
    # Direct content attribute access
    if hasattr(obj, 'content') and obj.content:
        print("Found content attribute")
        return obj.content
    
    # Dictionary with content
    if isinstance(obj, dict) and 'content' in obj:
        return obj['content']
    
    # For Agent Action objects
    if hasattr(obj, 'log') and obj.log:
        return obj.log
    
    # For tool outputs
    if hasattr(obj, 'tool_input'):
        if isinstance(obj.tool_input, str):
            return obj.tool_input
        elif isinstance(obj.tool_input, dict) and 'input' in obj.tool_input:
            return obj.tool_input['input']
    
    # For message objects
    if hasattr(obj, 'message'):
        msg = obj.message
        if hasattr(msg, 'content'):
            return msg.content
        elif isinstance(msg, str):
            return msg
    
    # For response objects
    if hasattr(obj, 'response'):
        return obj.response
    
    # Get output attribute
    if hasattr(obj, 'output'):
        return obj.output
    
    # For string objects
    if isinstance(obj, str):
        return obj
    
    # Last resort - extract text from string representation
    obj_repr = str(obj)
    # If it's just the default object representation, it's not helpful
    if obj_repr.startswith("<") and obj_repr.endswith(">"):
        # Try a more aggressive approach
        if hasattr(obj, "__dict__"):
            # Look through all attributes for likely content
            for attr_name, attr_value in obj.__dict__.items():
                if isinstance(attr_value, str) and len(attr_value) > 20:
                    if "content" in attr_name or "output" in attr_name or "response" in attr_name:
                        return attr_value
        
        # Final fallback
        return "Unable to extract content from object"
    
    return obj_repr

def extract_task_description(obj):
    """Extract task description from a CrewAI step object"""
    # Look for task description
    if hasattr(obj, 'task') and obj.task:
        if hasattr(obj.task, 'description'):
            return obj.task.description
        else:
            return str(obj.task)
    elif isinstance(obj, dict) and 'task' in obj and obj['task']:
        if hasattr(obj['task'], 'description'):
            return obj['task'].description
        else:
            return str(obj['task'])
    
    # Try extracting from string representation
    obj_str = str(obj)
    task_patterns = [
        r"task description['\"]?:\s*['\"]?([^'\"]+)",
        r"description['\"]?:\s*['\"]?([^'\"]+)"
    ]
    
    for pattern in task_patterns:
        match = re.search(pattern, obj_str)
        if match:
            return match.group(1).strip()
            
    return ""

def extract_step_name(obj):
    """
    Extract the step name from a CrewAI step object
    This function identifies what kind of step or action is being performed
    """
    # Try direct attribute access first
    if hasattr(obj, 'step'):
        return obj.step
    elif hasattr(obj, 'step_name'):
        return obj.step_name
    elif isinstance(obj, dict) and 'step' in obj:
        return obj['step']
    elif isinstance(obj, dict) and 'step_name' in obj:
        return obj['step_name']
    
    # Check for common CrewAI step types by class name
    obj_class = type(obj).__name__
    if 'AgentFinish' in obj_class:
        return "final_answer"
    elif 'AgentAction' in obj_class:
        return "agent_action"
    elif 'LLMThinking' in obj_class or 'ThinkingStep' in obj_class:
        return "thinking"
    elif 'TaskExecution' in obj_class:
        return "task_execution"
    elif 'AnswerStep' in obj_class:
        return "answering"
    
    # Check object string representation for clues
    obj_str = str(obj)
    if "thinking" in obj_str.lower():
        return "thinking"
    elif "answer" in obj_str.lower():
        return "answering"
    elif "final" in obj_str.lower() and "response" in obj_str.lower():
        return "final_answer"
    elif "task" in obj_str.lower() and "complete" in obj_str.lower():
        return "task_complete"
    
    # Default fallback
    return "unknown_step"

def get_step_key(agent_id, task_id, step_name):
    """Create a unique key for tracking step times"""
    ts = int(time.time())
    return f"{agent_id}:{task_id}:{step_name}:{ts}"

def record_step_start(step_key):
    """Record start time for a step"""
    global _step_start_times
    if step_key not in _step_start_times:
        _step_start_times[step_key] = {"start": time.time()}
    return _step_start_times[step_key]["start"]

def record_step_end(step_key):
    """Record end time for a step"""
    global _step_start_times
    if step_key in _step_start_times:
        _step_start_times[step_key]["end"] = time.time()
    return _step_start_times.get(step_key, {}).get("end", time.time())

def get_step_timestamps(step_key):
    """Get start and end timestamps for a step"""
    global _step_start_times
    times = _step_start_times.get(step_key, {})
    start_time = times.get("start", time.time())
    end_time = times.get("end", time.time())
    return start_time, end_time

def publish_to_kafka_with_timestamps(topic, record, step_key):
    """Publish a record to Kafka with timing information"""
    if not _kafka_enabled:
        return False
        
    try:
        # Get timing information
        start_time, end_time = get_step_timestamps(step_key)
        
        # Add timing info to record
        record["start_timestamp"] = start_time
        record["end_timestamp"] = end_time
        
        # Calculate duration in seconds
        duration_seconds = end_time - start_time
        record["duration_seconds"] = duration_seconds
        
        # Send to Kafka
        return publish_to_kafka(topic, record)
    except Exception as e:
        print(f"Error publishing to Kafka: {e}")
        return False

def map_agent_name_to_role(agent_name):
    """Map agent ID to its role based on configuration"""
    global _agent_roles
    
    # Try direct mapping from our predefined roles
    if agent_name in _agent_roles:
        return _agent_roles[agent_name]
    
    # Try content-based mapping
    if "pro" in agent_name.lower() or "advocate" in agent_name.lower():
        return "Pro-Autonomous Vehicle Advocate"
    elif "skeptic" in agent_name.lower() or "anti" in agent_name.lower():
        return "Autonomous Vehicle Skeptic" 
    elif "moderator" in agent_name.lower() or "debate" in agent_name.lower():
        return "Debate Moderator"
    
    # Default
    return agent_name

def extract_task_info(obj):
    """Extract task ID and description from a CrewAI step object"""
    # Default values
    task_id = "unknown_task"
    task_description = ""
    
    try:
        # Method 1: Direct task attribute
        if hasattr(obj, 'task') and obj.task:
            task = obj.task
            if hasattr(task, 'id'):
                task_id = task.id
            if hasattr(task, 'description'):
                task_description = task.description
            return task_id, task_description
        
        # Method 2: Task in dictionary
        if isinstance(obj, dict) and 'task' in obj:
            task = obj['task']
            if isinstance(task, dict):
                task_id = task.get('id', task_id)
                task_description = task.get('description', task_description)
            return task_id, task_description
        
        # Method 3: Extract from string representation
        str_rep = str(obj)
        
        # Look for task ID pattern
        id_pattern = r"Task: ([^,\n]+)"
        id_match = re.search(id_pattern, str_rep)
        if id_match:
            task_id = id_match.group(1).strip()
        
        # Look for description pattern
        desc_pattern = r"Description: ([^\n]+)"
        desc_match = re.search(desc_pattern, str_rep)
        if desc_match:
            task_description = desc_match.group(1).strip()
    except:
        pass
        
    return task_id, task_description

def estimate_tokens(text):
    """
    Estimate token count based on text length
    This is a rough approximation; ~4 chars per token for English text
    """
    if not text:
        return 0
    # Simple estimation - about 4 characters per token for English
    return len(text) // 4

def set_debug_mode(enabled):
    """Enable or disable debug logging"""
    global _debug_mode
    _debug_mode = enabled
    global_logger.log_system_message(
        f"Debug mode {'enabled' if enabled else 'disabled'}", 
        "config"
    )

def set_token_tracking(enabled):
    """Enable or disable token usage tracking"""
    global _token_tracking_enabled
    _token_tracking_enabled = enabled
    global_logger.log_system_message(
        f"Token tracking {'enabled' if enabled else 'disabled'}", 
        "config"
    )

def estimate_default_prompt_tokens(agent_role, task_description=None):
    """Estimate token count for default prompts based on agent role"""
    # Get the system prompt for this agent
    system_prompt = get_agent_prompt(agent_role)
    prompt_tokens = estimate_tokens(system_prompt)
    
    # Add tokens for task description if available
    if task_description:
        prompt_tokens += estimate_tokens(task_description)
    
    # Add tokens for debate context (conservative estimate)
    prompt_tokens += 500  # Base context about autonomous vehicles
    
    return prompt_tokens