"""
Test Ollama integration with CrewAI using a hierarchical debate structure
with a manager/moderator overseeing two adversarial debating agents.
"""

from crewai import Agent, Task, Process, Crew, LLM
import os

# Configure the LLM
llm = LLM(model="ollama/deepseek-r1", base_url="http://localhost:11434")

# Create a debate moderator (manager agent)
debate_moderator = Agent(
    role="Debate Moderator",
    goal="Facilitate a balanced, fact-based debate on autonomous vehicles",
    backstory="""You are a highly respected technology debate moderator with expertise in
    emerging technologies and their societal impacts. You ensure debates remain factual,
    balanced, and productive. You have complete authority to structure the debate,
    ask clarifying questions, and ensure both sides get fair representation.""",
    verbose=True,
    allow_delegation=True,  # Required for hierarchical process
    llm=llm
)

# Create pro-autonomous vehicles debater
pro_av_debater = Agent(
    role="Pro-Autonomous Vehicle Advocate",
    goal="Convincingly argue that autonomous vehicles will revolutionize transportation for the better",
    backstory="""You are an expert in autonomous vehicle technology and policy with a strong 
    belief in their potential to transform society positively. Your job is to present 
    compelling, fact-based arguments supporting autonomous vehicles while actively 
    identifying and exploiting weaknesses in opposing arguments.""",
    verbose=True,
    allow_delegation=False,  # This agent doesn't delegate - only responds to the moderator
    llm=llm
)

# Create anti-autonomous vehicles debater
anti_av_debater = Agent(
    role="Autonomous Vehicle Skeptic",
    goal="Convincingly argue that autonomous vehicles pose significant risks that outweigh benefits",
    backstory="""You are a transportation safety expert who has extensively studied the 
    limitations and risks of autonomous vehicles. You believe in technological progress 
    but are deeply concerned about premature deployment of AV technology. You use facts 
    and logical analysis to challenge overly optimistic claims about autonomous vehicles.""",
    verbose=True,
    allow_delegation=False,  # This agent doesn't delegate - only responds to the moderator
    llm=llm
)

# Main debate management task for the moderator
debate_management_task = Task(
    description="""You are moderating a debate on autonomous vehicles. Your job is to:
    
    1. Introduce the debate topic: "Will autonomous vehicles bring more benefits than risks to society?"
    2. First ask the Pro-Autonomous Vehicle Advocate to present their opening argument (delegate to them)
    3. Then ask the Autonomous Vehicle Skeptic to provide their rebuttal (delegate to them)
    4. Ask the Pro-Autonomous Vehicle Advocate for a counter-response (delegate to them)
    5. Ask the Autonomous Vehicle Skeptic for their closing argument (delegate to them)
    6. Summarize the key points from both sides and provide your own balanced assessment
       of the strongest arguments presented.
    
    Feel free to interject with clarifying questions between arguments if needed, or to
    redirect debaters if they stray from factual information. You have complete authority
    to structure this debate as you see fit to ensure it's informative and balanced.""",
    expected_output="A complete moderated debate with summary and assessment",
    agent=debate_moderator
)

# Pro-AV opening argument task
pro_av_opening_task = Task(
    description="""Construct a strong, fact-based opening argument making the case FOR 
    autonomous vehicles. Focus on safety improvements, economic benefits, accessibility 
    advantages, and environmental impacts. Provide specific data points and research 
    findings. Your argument should be 4-5 paragraphs and anticipate potential counterarguments.""",
    expected_output="A compelling opening argument supporting autonomous vehicles",
    agent=pro_av_debater
)

# Anti-AV rebuttal task
anti_av_rebuttal_task = Task(
    description="""Create a powerful rebuttal to the arguments presented for autonomous vehicles. 
    Identify flawed assumptions, cherry-picked data, overlooked risks, and implementation challenges. 
    Focus on safety concerns, cybersecurity vulnerabilities, job displacement, and infrastructure 
    requirements. Be factual but merciless in exposing weaknesses in their argument. 
    Your rebuttal should be 4-5 paragraphs.""",
    expected_output="A devastating rebuttal to the pro-autonomous vehicle argument",
    agent=anti_av_debater
)

# Pro-AV counter-response task
pro_av_counter_task = Task(
    description="""Create a targeted counter-response that defends your original position 
    while exposing logical fallacies and misrepresentations in the opposition's argument. 
    Address each major criticism directly with additional evidence. Emphasize the practical 
    pathways to overcoming the challenges they raised. Your counter-response should be 3-4 paragraphs.""",
    expected_output="A strategic counter-response that undermines the opposition's arguments",
    agent=pro_av_debater
)

# Anti-AV closing task
anti_av_closing_task = Task(
    description="""Deliver a powerful closing argument that reinforces your skeptical position 
    on autonomous vehicles. Address the weaknesses in the counter-response, emphasize the most 
    compelling concerns that remain unaddressed, and conclude with a call for a careful, measured 
    approach to AV deployment that prioritizes public safety over corporate profits and technological 
    enthusiasm. Your closing should be 2-3 paragraphs and leave a lasting impression.""",
    expected_output="A compelling closing argument that cements the case for caution with autonomous vehicles",
    agent=anti_av_debater
)

# Create the crew with hierarchical process - moderator at the top
debate_crew = Crew(
    agents=[pro_av_debater, anti_av_debater],
    tasks=[
        debate_management_task,  # This is the main task for the manager
        pro_av_opening_task,     # These are tasks the manager can delegate to
        anti_av_rebuttal_task,
        pro_av_counter_task,
        anti_av_closing_task
    ],
    model="ollama/deepseek-r1",
    process=Process.hierarchical,  # Use hierarchical process
    manager_agent=debate_moderator,  # Add this line to specify the manager agent
    verbose=True,
    planning=True,
    planning_llm=llm
)

print("\n======= Autonomous Vehicle Debate with Ollama =======")
print(f"Model: deepseek-r1")
print(f"Base URL: {os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
print("Process: Hierarchical (moderator manages debate flow)")
print("=======================================================\n")

# Execute the debate
result = debate_crew.kickoff()

print("\n================== DEBATE TRANSCRIPT ==================")
print(result)
print("=======================================================")