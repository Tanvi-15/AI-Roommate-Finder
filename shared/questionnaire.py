# questionnaire.py

LIVING_PREFERENCES = {
    "location": {
        "question": "What city/area are you looking to live in?",
        "type": "text",
        "placeholder": "e.g., Boston, Cambridge"
    },
    "budget_min": {
        "question": "Minimum monthly budget ($)",
        "type": "number",
        "min": 300,
        "max": 5000,
        "default": 800
    },
    "budget_max": {
        "question": "Maximum monthly budget ($)",
        "type": "number",
        "min": 300,
        "max": 5000,
        "default": 1500
    },
    "room_type": {
        "question": "Room preference",
        "type": "select",
        "options": ["Private room", "Shared room", "Either is fine"]
    },
    "bathroom_preference": {
        "question": "Bathroom preference",
        "type": "select",
        "options": ["Private bathroom", "Shared with 1 person", "Shared with 2+ people", "No preference"]
    },
    "roommate_gender": {
        "question": "Roommate gender preference",
        "type": "select",
        "options": ["Same gender only", "Any gender", "No preference"]
    },
    "pets": {
        "question": "Pet situation",
        "type": "select",
        "options": ["I have pets", "I love pets but don't have any", "No pets please", "Allergic to pets"]
    },
    "smoking": {
        "question": "Smoking preference",
        "type": "select",
        "options": ["I smoke", "Okay with smokers", "Non-smoking household only"]
    }
}

PERSONALITY_QUESTIONS = {
    "sleep_schedule": {
        "question": "What's your typical sleep schedule?",
        "type": "select",
        "options": ["Early bird (before 10pm)", "Night owl (after midnight)", "Somewhere in between"]
    },
    "cleanliness": {
        "question": "How would you rate your cleanliness? (1=Relaxed, 5=Spotless)",
        "type": "slider",
        "min": 1,
        "max": 5,
        "default": 3
    },
    "noise_level": {
        "question": "Noise and social preferences",
        "type": "select",
        "options": ["Very quiet, minimal guests", "Occasional friends over", "Social and lively", "Balance of both"]
    },
    "work_from_home": {
        "question": "Do you work from home?",
        "type": "select",
        "options": ["Yes, full-time", "Hybrid (few days a week)", "No, I go to office/school", "Varies"]
    },
    "introvert_extrovert": {
        "question": "Are you more introverted or extroverted?",
        "type": "slider",
        "min": 1,
        "max": 5,
        "default": 3,
        "labels": ["Very Introverted", "Very Extroverted"]
    },
    "conflict_style": {
        "question": "How do you prefer to handle conflicts?",
        "type": "select",
        "options": ["Direct conversation immediately", "Cool off first, then discuss", "Write it out (text/note)", "Avoid if possible"]
    },
    "hobbies": {
        "question": "What are your main hobbies/interests?",
        "type": "text",
        "placeholder": "e.g., Gaming, cooking, hiking, reading..."
    },
    "dealbreaker": {
        "question": "Any absolute dealbreakers in a roommate?",
        "type": "text",
        "placeholder": "e.g., No loud music after 10pm, must be okay with my cat..."
    }
}

def get_all_questions() -> dict:
    """Return all questions combined"""
    return {
        "living": LIVING_PREFERENCES,
        "personality": PERSONALITY_QUESTIONS
    }