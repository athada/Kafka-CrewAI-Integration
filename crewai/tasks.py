"""
Task definitions for CrewAI debate system
"""

from crewai import Task

def create_debate_management_task(moderator):
    """Create the main task for the debate moderator"""
    return Task(
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
        agent=moderator
    )

def create_pro_av_opening_task(pro_debater):
    """Create the task for the pro-AV opening argument"""
    return Task(
        description="""Construct a strong, fact-based opening argument making the case FOR 
        autonomous vehicles. Focus on safety improvements, economic benefits, accessibility 
        advantages, and environmental impacts. Provide specific data points and research 
        findings. Your argument should be 4-5 paragraphs and anticipate potential counterarguments.""",
        expected_output="A compelling opening argument supporting autonomous vehicles",
        agent=pro_debater
    )

def create_anti_av_rebuttal_task(anti_debater):
    """Create the task for the anti-AV rebuttal"""
    return Task(
        description="""Create a powerful rebuttal to the arguments presented for autonomous vehicles. 
        Identify flawed assumptions, cherry-picked data, overlooked risks, and implementation challenges. 
        Focus on safety concerns, cybersecurity vulnerabilities, job displacement, and infrastructure 
        requirements. Be factual but merciless in exposing weaknesses in their argument. 
        Your rebuttal should be 4-5 paragraphs.""",
        expected_output="A devastating rebuttal to the pro-autonomous vehicle argument",
        agent=anti_debater
    )

def create_pro_av_counter_task(pro_debater):
    """Create the task for the pro-AV counter-response"""
    return Task(
        description="""Create a targeted counter-response that defends your original position 
        while exposing logical fallacies and misrepresentations in the opposition's argument. 
        Address each major criticism directly with additional evidence. Emphasize the practical 
        pathways to overcoming the challenges they raised. Your counter-response should be 3-4 paragraphs.""",
        expected_output="A strategic counter-response that undermines the opposition's arguments",
        agent=pro_debater
    )

def create_anti_av_closing_task(anti_debater):
    """Create the task for the anti-AV closing argument"""
    return Task(
        description="""Deliver a powerful closing argument that reinforces your skeptical position 
        on autonomous vehicles. Address the weaknesses in the counter-response, emphasize the most 
        compelling concerns that remain unaddressed, and conclude with a call for a careful, measured 
        approach to AV deployment that prioritizes public safety over corporate profits and technological 
        enthusiasm. Your closing should be 2-3 paragraphs and leave a lasting impression.""",
        expected_output="A compelling closing argument that cements the case for caution with autonomous vehicles",
        agent=anti_debater
    )

def create_all_tasks(agents):
    """Create all debate tasks"""
    return {
        "management_task": create_debate_management_task(agents["moderator"]),
        "pro_opening_task": create_pro_av_opening_task(agents["pro_debater"]),
        "anti_rebuttal_task": create_anti_av_rebuttal_task(agents["anti_debater"]),
        "pro_counter_task": create_pro_av_counter_task(agents["pro_debater"]),
        "anti_closing_task": create_anti_av_closing_task(agents["anti_debater"])
    } 