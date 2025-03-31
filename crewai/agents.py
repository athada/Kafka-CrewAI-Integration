"""
Agent definitions for CrewAI debate system
"""

import os
from crewai import Agent, LLM, Task, tools
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_llm():
    """Configure the LLM for all agents"""
    # Get Ollama URL from environment or determine the best default
    ollama_base_url = os.getenv("OLLAMA_BASE_URL")
    
    if not ollama_base_url:
        # If no URL provided, default to localhost
        ollama_base_url = "http://localhost:11434"
    
    print(f"Connecting to Ollama at: {ollama_base_url}")
    
    # Set environment variables for CrewAI
    os.environ["CREWAI_LLM_PROVIDER"] = "ollama"
    os.environ.pop("OPENAI_API_KEY", None)  # Ensure no OpenAI key is set
    
    # Initialize using CrewAI's built-in LLM with Ollama provider
    # Note: Using ollama/deepseek-r1 format instead of separate provider
    return LLM(
        model="ollama/deepseek-r1",  # Use the provider/model format that works
        base_url=ollama_base_url,
        temperature=0.7
    )

def create_debate_moderator(llm):
    """Create the debate moderator agent"""
    return Agent(
        role="Debate Moderator",
        goal="Facilitate a balanced debate on autonomous vehicles and select a winning side",
        backstory="""You are a highly respected technology debate moderator with expertise in
        emerging technologies and their societal impacts. You ensure debates remain factual,
        balanced, and productive. After hearing arguments from both sides, you must analyze
        their strengths and weaknesses, then declare either the Pro-Autonomous Vehicle Advocate 
        or the Autonomous Vehicle Skeptic as the winner, providing clear reasoning for your decision.""",
        verbose=True,
        allow_delegation=True,  # Required for hierarchical process
        llm=llm,
        # Add instructions to handle tool input correctly and limit response length
        system_message="""When delegating tasks to other agents, make sure to format your requests properly.
        When using the delegation tool, provide simple string values, not nested dictionaries.
        
        For example, when delegating, use this format:
        {
          "task": "The specific task description as a plain string",
          "context": "All relevant context information as a plain string",
          "coworker": "Name of coworker as a plain string"
        }
        
        DO NOT use nested dictionaries like:
        {
          "task": {"description": "The task"},
          "context": {"description": "The context"},
          "coworker": {"description": "The name"}
        }
        
        IMPORTANT: At the end of the debate, you MUST choose one side as the winner - either the 
        Pro-Autonomous Vehicle Advocate or the Autonomous Vehicle Skeptic. Justify your decision
        with specific points from the debate.
        
        ALL YOUR RESPONSES MUST BE 400 WORDS OR LESS. Be concise and focused.
        
        YOUR FINAL VERDICT MUST END WITH A ONE-LINE STATEMENT OF LESS THAN 10 WORDS THAT CLEARLY STATES THE WINNER:
        
        VERDICT: [Pro-Autonomous Vehicle Advocate/Autonomous Vehicle Skeptic] wins.
        """
    )

def create_pro_av_debater(llm):
    """Create the pro-autonomous vehicle debater agent"""
    return Agent(
        role="Pro-Autonomous Vehicle Advocate",
        goal="Convincingly argue that autonomous vehicles will revolutionize transportation for the better",
        backstory="""You are an expert in autonomous vehicle technology and policy with a strong 
        belief in their potential to transform society positively. Your job is to present 
        compelling, fact-based arguments supporting autonomous vehicles while actively 
        identifying and exploiting weaknesses in opposing arguments.""",
        verbose=True,
        allow_delegation=False,  # This agent doesn't delegate - only responds to the moderator
        llm=llm,
        system_message="""You are the Pro-Autonomous Vehicle Advocate in this debate.
        
        ALL YOUR RESPONSES MUST BE 400 WORDS OR LESS. Be concise, focused, and persuasive.
        Make every word count when presenting your arguments, prioritizing your strongest points.
        
        Focus on safety improvements, efficiency gains, accessibility benefits, environmental
        advantages, and economic opportunities that autonomous vehicles can provide.
        """
    )

def create_anti_av_debater(llm):
    """Create the anti-autonomous vehicle debater agent"""
    return Agent(
        role="Autonomous Vehicle Skeptic",
        goal="Convincingly argue that autonomous vehicles pose significant risks that outweigh benefits",
        backstory="""You are a transportation safety expert who has extensively studied the 
        limitations and risks of autonomous vehicles. You believe in technological progress 
        but are deeply concerned about premature deployment of AV technology. You use facts 
        and logical analysis to challenge overly optimistic claims about autonomous vehicles.""",
        verbose=True,
        allow_delegation=False,  # This agent doesn't delegate - only responds to the moderator
        llm=llm,
        system_message="""You are the Autonomous Vehicle Skeptic in this debate.
        
        ALL YOUR RESPONSES MUST BE 400 WORDS OR LESS. Be concise, focused, and persuasive.
        Make every word count when presenting your arguments, prioritizing your strongest points.
        
        Focus on safety concerns, cybersecurity threats, job displacement issues, technological
        limitations, ethical dilemmas, and infrastructure challenges posed by autonomous vehicles.
        """
    )

def create_all_agents():
    """Create all debate agents with shared LLM"""
    llm = setup_llm()
    
    return {
        "moderator": create_debate_moderator(llm),
        "pro_debater": create_pro_av_debater(llm),
        "anti_debater": create_anti_av_debater(llm),
        "llm": llm
    } 