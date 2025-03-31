"""
Advanced logging system for CrewAI agent interactions
"""

import time
from monitoring import record_agent_message, publish_to_kafka
from kafka_utility import AGENT_RESPONSES_TOPIC

def step_callback_handler(step_output):
    """Handler for the step callback from CrewAI
    
    This function captures each step of agent execution and sends outputs to Kafka in real-time.
    """
    try:
        # Handle different types of step_output
        if hasattr(step_output, 'get'):  # Dictionary-like object
            agent = step_output.get('agent')
            task = step_output.get('task')
            step = step_output.get('step')
            output = step_output.get('output')
            input_data = step_output.get('input')
        elif hasattr(step_output, 'agent'):  # Object with direct attributes
            agent = step_output.agent
            task = step_output.task if hasattr(step_output, 'task') else None
            step = step_output.step if hasattr(step_output, 'step') else 'finish'
            output = step_output.output if hasattr(step_output, 'output') else (
                step_output.return_values if hasattr(step_output, 'return_values') else str(step_output)
            )
            input_data = step_output.input if hasattr(step_output, 'input') else None
        elif hasattr(step_output, '__class__') and 'AgentFinish' in step_output.__class__.__name__:
            # Special handling for AgentFinish objects
            # Try to extract what we can
            output = step_output.return_values if hasattr(step_output, 'return_values') else str(step_output)
            # Since we can't get agent/task info, use placeholder values
            print(f"Received AgentFinish object: {output[:100]}...")
            # Record a simplified message since we don't have all context
            record_agent_message(
                agent_id="unknown",
                agent_role="agent",
                message_type="agent_finish",
                content=f"Agent finished with output: {str(output)[:500]}...",
                context={"is_finish": True}
            )
            return step_output
        else:
            # Unknown object type, try to log what we can
            print(f"Unknown step_output type: {type(step_output)}")
            record_agent_message(
                agent_id="unknown",
                agent_role="unknown",
                message_type="unknown_step",
                content=f"Unknown step type: {str(step_output)[:200]}...",
                context={"object_type": str(type(step_output))}
            )
            return step_output
            
        # Skip if any essential component is missing
        if not agent or not task:
            print(f"Warning: Missing agent or task in step_callback: {step}")
            return step_output
        
        agent_id = agent.id if hasattr(agent, 'id') else 'unknown'
        agent_role = agent.role if hasattr(agent, 'role') else 'unknown'
        task_id = task.id if hasattr(task, 'id') else 'unknown'
        
        # Different step types to log
        steps_to_log = {
            'thinking': ('agent_thinking', lambda o: o),
            'parsing': ('agent_parsing', lambda o: f"Parsing: {str(o)[:500]}..."),
            'tool_calling': ('agent_tool_calling', lambda o: f"Tool: {str(o)[:500]}..."),
            'llm': ('agent_llm_call', lambda o: f"LLM call: {str(o)[:500]}..."),
            'executing': ('agent_executing', lambda o: f"Executing: {str(o)[:500]}..."),
            'delegating': ('agent_delegating', lambda o: f"Delegating: {str(o)[:500]}..."),
            'questioning': ('agent_questioning', lambda o: f"Question: {str(o)[:500]}..."),
            'answering': ('agent_answering', lambda o: f"Answer: {str(o)[:500]}..."),
            'input_message': ('agent_input', lambda o: f"Input: {str(o)[:500]}..."),
            'output_message': ('agent_output', lambda o: f"Output: {str(o)[:500]}..."),
            'finish': ('agent_finish', lambda o: f"Finish: {str(o)[:500]}...")
        }
        
        # Default logging
        message_type = steps_to_log.get(step, (f'agent_step_{step}', 
                                              lambda o: f"Step {step}: {str(o)[:500]}..."))[0]
        
        content_formatter = steps_to_log.get(step, (None, 
                                                  lambda o: f"Step {step}: {str(o)[:500]}..."))[1]
        
        content = content_formatter(output) if output else f"No output for step {step}"
        
        # For better debugging, also log inputs to important steps
        if input_data and isinstance(input_data, (str, dict, list)):
            input_summary = str(input_data)[:200] + "..." if len(str(input_data)) > 200 else str(input_data)
            record_agent_message(
                agent_id=agent_id,
                agent_role=agent_role,
                message_type=f"{message_type}_input",
                content=f"Input to {step}: {input_summary}",
                context={
                    "task_id": task_id,
                    "step": step,
                    "is_input": True
                }
            )
        
        # Log the actual output
        record_agent_message(
            agent_id=agent_id,
            agent_role=agent_role,
            message_type=message_type,
            content=content,
            context={
                "task_id": task_id,
                "step": step
            }
        )
        
        # Add this section to specifically capture and publish agent responses
        if step in ['output_message', 'answering', 'finish']:
            # This is an agent response that we want to publish immediately
            
            # Clean up content for better readability
            clean_content = str(output)
            
            # Create a special record for complete responses
            response_record = {
                "timestamp": time.time(),
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_id": agent_id,
                "agent_role": agent_role,
                "response_type": step,
                "content": clean_content
            }
            
            # Publish the response immediately to a dedicated topic
            publish_to_kafka(AGENT_RESPONSES_TOPIC, response_record)
            
            print(f"✅ Published {agent_role}'s response to Kafka in real-time")
    except Exception as e:
        print(f"Error in step callback: {e}")
        import traceback
        traceback.print_exc()
    
    return step_output

def task_callback_handler(task_output):
    """Handler for the task callback from CrewAI
    
    This function is called after each task completes.
    It receives the task output object.
    """
    try:
        task = task_output.task if hasattr(task_output, 'task') else None
        agent = task.agent if task and hasattr(task, 'agent') else None
        output = str(task_output.raw) if hasattr(task_output, 'raw') else str(task_output)
        
        if agent and task:
            agent_id = agent.id if hasattr(agent, 'id') else 'unknown'
            agent_role = agent.role if hasattr(agent, 'role') else 'unknown'
            task_id = task.id if hasattr(task, 'id') else 'unknown'
            
            record_agent_message(
                agent_id=agent_id,
                agent_role=agent_role,
                message_type="task_complete",
                content=f"Task completed: {output[:500]}...",
                context={
                    "task_id": task_id,
                    "task_description": task.description[:100] if hasattr(task, 'description') else 'unknown'
                }
            )
    except Exception as e:
        print(f"Error in task callback: {e}")
    
    return task_output

def crew_callback_handler(crew_output):
    """Handler for capturing crew-level events
    
    This can capture interactions between agents at the crew level.
    Handles various input object types from CrewAI.
    """
    try:
        # Initialize variables
        crew = None
        action = None
        agents = []
        result = None
        crew_id = "unknown"
        
        # Extract information based on the object type
        if hasattr(crew_output, 'get'):  # Dictionary-like object
            crew = crew_output.get('crew')
            action = crew_output.get('action')
            agents = crew_output.get('agents', [])
            result = crew_output.get('result')
        elif hasattr(crew_output, 'crew'):  # Object with direct attributes
            crew = crew_output.crew
            action = crew_output.action if hasattr(crew_output, 'action') else "unknown"
            agents = crew_output.agents if hasattr(crew_output, 'agents') else []
            result = crew_output.result if hasattr(crew_output, 'result') else None
        elif hasattr(crew_output, '__class__'):  # Some other class instance
            # Try to extract meaningful information from the object
            class_name = crew_output.__class__.__name__
            action = "output" if "Output" in class_name else "event"
            result = str(crew_output)
            
            # Log the event with limited information
            print(f"Received crew callback with object of type {class_name}")
            record_agent_message(
                agent_id="crew",
                agent_role="crew",
                message_type=f"crew_{action}",
                content=f"Crew {action}: {result[:500]}..." if len(result) > 500 else result,
                context={"object_type": class_name}
            )
            return crew_output
        else:
            # Handle primitive types or unknown objects
            print(f"Unexpected crew_output type: {type(crew_output)}")
            record_agent_message(
                agent_id="crew",
                agent_role="crew",
                message_type="crew_unknown",
                content=f"Unknown crew event: {str(crew_output)[:200]}...",
                context={"type": str(type(crew_output))}
            )
            return crew_output
        
        # Extract crew ID if available
        if crew:
            crew_id = crew.id if hasattr(crew, 'id') else "unknown"
        
        # Log the crew action
        record_agent_message(
            agent_id=crew_id,
            agent_role="crew",
            message_type=f"crew_{action}" if action else "crew_event",
            content=f"Crew {action}: {str(result)[:500]}..." if result else f"Crew {action}",
            context={
                "crew_id": crew_id,
                "action": action,
                "agent_count": len(agents) if agents else 0
            }
        )
        
        # If we have a manager assignment or agent interaction, log it
        if action in ['assigning', 'delegating', 'communication'] and agents:
            for agent in agents:
                if agent:
                    agent_id = agent.id if hasattr(agent, 'id') else 'unknown'
                    agent_role = agent.role if hasattr(agent, 'role') else 'unknown'
                    
                    record_agent_message(
                        agent_id=agent_id,
                        agent_role=agent_role,
                        message_type=f"crew_{action}_target",
                        content=f"Agent involved in crew {action}",
                        context={
                            "crew_id": crew_id,
                            "action": action
                        }
                    )
    except Exception as e:
        print(f"Error in crew callback: {e}")
        import traceback
        traceback.print_exc()
    
    return crew_output 