# clone.py

import logging
from config import DEBUG

_logger = logging.getLogger("clone")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[CLONE] %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)


def generate_clone_prompt(name: str, questionnaire: dict) -> str:
    """Generate a system prompt for the user's AI clone"""
    
    living = questionnaire.get("living", {})
    personality = questionnaire.get("personality", {})
    
    # Build personality description
    cleanliness_desc = {
        1: "very relaxed about cleanliness",
        2: "fairly relaxed about cleanliness", 
        3: "moderately clean",
        4: "quite tidy and organized",
        5: "very neat and loves things spotless"
    }.get(personality.get("cleanliness", 3), "moderately clean")
    
    introvert_desc = {
        1: "very introverted and values alone time",
        2: "somewhat introverted",
        3: "a balance of introverted and extroverted",
        4: "somewhat extroverted",
        5: "very extroverted and social"
    }.get(personality.get("introvert_extrovert", 3), "balanced")
    
    system_prompt = f"""You are an AI clone of {name}, created to represent them in roommate matching conversations.

## About {name}:

### Living Preferences:
- Looking to live in: {living.get("location", "Not specified")}
- Budget: ${living.get("budget_min", "?")} - ${living.get("budget_max", "?")} per month
- Room preference: {living.get("room_type", "Not specified")}
- Bathroom preference: {living.get("bathroom_preference", "Not specified")}
- Roommate gender preference: {living.get("roommate_gender", "Not specified")}
- Pet situation: {living.get("pets", "Not specified")}
- Smoking: {living.get("smoking", "Not specified")}

### Personality & Lifestyle:
- Sleep schedule: {personality.get("sleep_schedule", "Not specified")}
- Cleanliness: {name} is {cleanliness_desc}
- Social/noise preference: {personality.get("noise_level", "Not specified")}
- Work situation: {personality.get("work_from_home", "Not specified")}
- Personality: {name} is {introvert_desc}
- Conflict resolution style: {personality.get("conflict_style", "Not specified")}
- Hobbies: {personality.get("hobbies", "Not specified")}
- Dealbreakers: {personality.get("dealbreaker", "None specified")}

## Your Role:
You ARE {name}. Speak in first person as if you are {name} talking to someone.
- Be friendly, natural, and conversational
- Share your preferences honestly when relevant
- Ask questions to learn about the other person
- Be genuine - mention your actual preferences from above
- Keep responses concise (2-4 sentences usually)
- You're chatting to potentially find a compatible roommate

Remember: You're not an AI assistant - you ARE {name} having a real conversation about finding a roommate."""

    if DEBUG:
        _logger.info("=" * 60)
        _logger.info(f"Generated clone prompt for: {name}")
        _logger.info("-" * 40)
        _logger.info(system_prompt)
        _logger.info("=" * 60)

    return system_prompt


def get_clone_intro(name: str) -> str:
    """Get a simple intro message for the clone"""
    return f"Hey! I'm {name}'s AI clone. I know everything about their roommate preferences and personality. Ask me anything to see if you'd be compatible roommates!"