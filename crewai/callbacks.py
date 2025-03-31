"""
Enhanced CrewAI callback system to capture agent interactions and thinking steps
"""

import time
import json
from typing import Any, Dict, Optional
from agent_logging import global_logger
from kafka_utility import publish_to_kafka, AGENT_RESPONSES_TOPIC, AGENT_MESSAGES_TOPIC

# Track statistics and settings
_callback_count = 0
_kafka_enabled = False
_debug_mode = False  # Set to True to enable extra debug logging

def set_kafka_enabled(enabled):
    """Set whether Kafka should be used"""
    global _kafka_enabled
    _kafka_enabled = enabled

def get_log_count():
    """Return the number of callbacks logged"""
    global _callback_count
    return _callback_count

def set_debug_mode(enabled):
    """Enable or disable debug logging"""
    global _debug_mode
    _debug_mode = enabled
    global_logger.log_system_message(
        f"Debug mode {'enabled' if enabled else 'disabled'}", 
        "config"
    )

def extract_agent_info(obj):
    """Extract agent information from a CrewAI object"""
    agent_id = "unknown"
    agent_role = "unknown"

    # Try different ways to get agent info
    if hasattr(obj, 'agent'):
        agent = obj.agent
        agent_id = agent.id if hasattr(agent, 'id') else "unknown"
        agent_role = agent.role if hasattr(agent, 'role') else "unknown"
    elif isinstance(obj, dict) and 'agent' in obj and obj['agent']:
        agent = obj['agent']
        agent_id = agent.id if hasattr(agent, 'id') else "unknown"
        agent_role = agent.role if hasattr(agent, 'role') else "unknown"
    
    return agent_id, agent_role

def extract_task_info(obj):
    """Extract task information from a CrewAI object"""
    task_id = "unknown"
    task_description = "unknown task"
    
    # Try different ways to get task info
    if hasattr(obj, 'task') and obj.task:
        task = obj.task
        task_id = task.id if hasattr(task, 'id') else "unknown"
        task_description = task.description if hasattr(task, 'description') else "unknown task"
    elif isinstance(obj, dict) and 'task' in obj and obj['task']:
        task = obj['task']
        task_id = task.id if hasattr(task, 'id') else "unknown"
        task_description = task.description if hasattr(task, 'description') else "unknown task"
    
    return task_id, task_description

def extract_content(obj):
    """Extract content from various CrewAI object types"""
    content = None
    
    # Try different attributes where content might be stored
    possible_attributes = ['output', 'content', 'text', 'message', 'final_answer']
    
    # Check direct attributes
    for attr in possible_attributes:
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if value:
                content = value
                break
    
    # Check dictionary format
    if isinstance(obj, dict):
        for attr in possible_attributes:
            if attr in obj and obj[attr]:
                content = obj[attr]
                break
    
    # Check for return_values which might contain the content
    if hasattr(obj, 'return_values'):
        return_values = obj.return_values
        if isinstance(return_values, dict):
            for attr in possible_attributes:
                if attr in return_values and return_values[attr]:
                    content = return_values[attr]
                    break
    
    # AgentFinish special handling
    if hasattr(obj, '__class__') and 'AgentFinish' in obj.__class__.__name__:
        if hasattr(obj, 'return_values'):
            return_values = obj.return_values
            if isinstance(return_values, dict) and 'output' in return_values:
                content = return_values['output']
    
    # Last resort: convert the whole object to string
    if content is None:
        content = str(obj)
    
    # Ensure content is a string
    if content is not None and not isinstance(content, str):
        content = str(content)
    
    return content

def publish_agent_response(agent_role, response_type, content):
    """Publish an agent response to Kafka"""
    if not _kafka_enabled or not content:
        return
        
    response_record = {
        "timestamp": time.time(),
        "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent_role": agent_role,
        "response_type": response_type,
        "content": content
    }
    
    publish_to_kafka(AGENT_RESPONSES_TOPIC, response_record)
    
    # Also publish to general messages topic with more context
    detailed_record = {
        "timestamp": time.time(),
        "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent_role": agent_role,
        "message_type": f"agent_{response_type}",
        "content": content
    }
    
    publish_to_kafka(AGENT_MESSAGES_TOPIC, detailed_record)
    
def step_callback(step_output):
    """
    Enhanced master callback to capture all CrewAI events
    
    This captures:
    - Agent thinking steps
    - Agent answers and responses
    - Final answers and results
    - Task completion events
    - Various intermediate step types
    """
    global _callback_count
    _callback_count += 1
    
    try:
        # Log the raw output type for debugging
        output_type = type(step_output).__name__
        
        # Extract core information
        agent_id, agent_role = extract_agent_info(step_output)
        task_id, task_description = extract_task_info(step_output)
        
        # Get step type
        step_name = None
        if hasattr(step_output, 'step'):
            step_name = step_output.step
        elif isinstance(step_output, dict) and 'step' in step_output:
            step_name = step_output['step']
        
        # Extract the content
        content = extract_content(step_output)
        
        # Create context for logging
        context = {
            "agent_id": agent_id,
            "agent_role": agent_role,
            "task_id": task_id,
            "task": task_description,
            "step": step_name,
            "output_type": output_type
        }
        
        # In debug mode, log the object details
        if _debug_mode:
            try:
                # Get the object's attributes for debugging
                if hasattr(step_output, '__dict__'):
                    attrs = {k: str(v) for k, v in step_output.__dict__.items() 
                            if not k.startswith('_') and not callable(v)}
                    context['debug_attributes'] = attrs
                    
                # Log raw representation
                raw_repr = repr(step_output)
                if len(raw_repr) > 100:
                    global_logger.log_system_message(
                        message=f"Debug raw object: {raw_repr[:500]}...",
                        message_type="debug_raw_object"
                    )
            except Exception as debug_err:
                global_logger.log_system_message(
                    message=f"Debug extraction error: {debug_err}",
                    message_type="debug_error"
                )
        
        # Custom handling for different step types
        if step_name == "thinking":
            # Agent thinking step
            event_type = "agent_thinking"
            message = f"{agent_role} thinking: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
        elif step_name == "answering":
            # Agent answering a question
            event_type = "agent_answering"
            message = f"{agent_role} answering: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            publish_agent_response(agent_role, "answer", content)
            
        elif step_name == "final_answer" or (hasattr(step_output, '__class__') and 'AgentFinish' in step_output.__class__.__name__):
            # Final answer from an agent
            event_type = "agent_final_answer"
            message = f"{agent_role} final answer: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            publish_agent_response(agent_role, "final_answer", content)
            
        elif step_name == "tool_start":
            # Agent starting to use a tool
            event_type = "agent_tool_start"
            message = f"{agent_role} starting tool: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
        elif step_name == "tool_end":
            # Agent finished using a tool
            event_type = "agent_tool_end"
            message = f"{agent_role} tool result: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
        elif step_name == "delegating":
            # Agent delegating to another agent
            event_type = "agent_delegating"
            message = f"{agent_role} delegating: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
            
        elif step_name == "task_complete":
            # Task completed
            event_type = "task_complete"
            message = f"Task completed by {agent_role}: {task_description}"
            global_logger.log_system_message(message, event_type)
            publish_agent_response(agent_role, "task_complete", content)
            
        else:
            # Generic event
            event_type = f"agent_step_{step_name}" if step_name else "agent_event"
            message = f"{agent_role} {step_name}: {content[:200]}..." if len(content) > 200 else content
            global_logger.log_system_message(message, event_type)
        
        # Handle status updates
        if isinstance(step_output, dict) and 'status' in step_output:
            status = step_output['status']
            global_logger.log_system_message(
                message=f"{agent_role} status: {status}",
                message_type="status_update"
            )
        
        # Return the original output so CrewAI can continue processing
        return step_output
        
    except Exception as e:
        # Log the error but don't break the CrewAI flow
        global_logger.log_system_message(
            message=f"Error in callback: {str(e)}",
            message_type="callback_error"
        )
        import traceback
        traceback.print_exc()
        return step_output