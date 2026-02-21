# questionnaire.py

# ─────────────────────────────────────────────
# SECTION 1: LIVING PREFERENCES
# ─────────────────────────────────────────────

LIVING_PREFERENCES = {
    "location": {
        "question": "What city/area are you looking to live in?",
        "type": "text",
        "placeholder": "e.g., Boston, Cambridge, Roxbury",
        "required": True,
    },
    "gender": {
        "question": "What is your gender?",
        "type": "select",
        "options": ["Man", "Woman", "Non-binary", "Prefer not to say"],
        "required": True,
        "help": "Used to match 'same gender only' preferences accurately.",
    },
    "move_in_date": {
        "question": "When are you looking to move in?",
        "type": "select",
        "options": ["ASAP", "Within 1 month", "1–3 months", "3–6 months", "Flexible"],
    },
    "lease_type": {
        "question": "What kind of lease do you prefer?",
        "type": "select",
        "options": ["Month-to-month", "6-month lease", "1-year lease", "No preference"],
    },
    "budget_min": {
        "question": "Minimum monthly budget ($)",
        "type": "number",
        "min": 300,
        "max": 5000,
        "default": 800,
        "required": True,
    },
    "budget_max": {
        "question": "Maximum monthly budget ($)",
        "type": "number",
        "min": 300,
        "max": 5000,
        "default": 1500,
        "required": True,
    },
    "budget_flexibility": {
        "question": "How flexible is your budget?",
        "type": "select",
        "options": ["Hard limit — cannot go over", "Can flex up to ~$100", "Can flex up to ~$200", "Fairly flexible if the fit is right"],
        "priority_field": True,
        "required": True,
    },
    "room_type": {
        "question": "Room preference",
        "type": "select",
        "options": ["Private room", "Shared room", "Either is fine"],
        "required": True,
    },
    "bathroom_preference": {
        "question": "Bathroom preference",
        "type": "select",
        "options": ["Private bathroom", "Shared with 1 person", "Shared with 2+ people", "No preference"],
    },
    "roommate_gender": {
        "question": "Roommate gender preference",
        "type": "select",
        "options": ["Same gender only", "Any gender", "No preference"],
        "required": True,
    },
    "pets": {
        "question": "Pet situation",
        "type": "select",
        "options": ["I have pets", "I love pets but don't have any", "No pets please", "Allergic to pets"],
        "required": True,
    },
    "smoking": {
        "question": "Smoking preference",
        "type": "select",
        "options": ["I smoke", "Okay with smokers", "Non-smoking household only"],
        "required": True,
    },
}

# ─────────────────────────────────────────────
# SECTION 2: FINANCIAL & UTILITIES
# ─────────────────────────────────────────────

FINANCIAL_QUESTIONS = {
    "utilities_split": {
        "question": "How do you prefer to split utilities (electricity, internet, etc.)?",
        "type": "select",
        "options": ["Split equally", "Split by usage/room size", "Included in rent", "Discuss case by case"]
    },
    "groceries_split": {
        "question": "How do you feel about shared groceries?",
        "type": "select",
        "options": ["Completely separate groceries", "Split basics (condiments, cleaning)", "Fully shared groceries", "Open to discussing"]
    },
    "security_deposit": {
        "question": "Can you cover a security deposit upfront?",
        "type": "select",
        "options": ["Yes, up to 1 month's rent", "Yes, up to 2 months' rent", "Need to split the deposit", "Not sure yet"]
    },
    "payment_style": {
        "question": "How do you prefer to handle shared payments?",
        "type": "select",
        "options": ["One person pays, others Venmo/Zelle", "Each person pays their share directly", "Shared app (Splitwise, etc.)", "No preference"]
    }
}

# ─────────────────────────────────────────────
# SECTION 3: DAILY ROUTINES
# ─────────────────────────────────────────────

ROUTINE_QUESTIONS = {
    "sleep_schedule": {
        "question": "What's your typical sleep schedule?",
        "type": "select",
        "options": ["Early bird (sleep before 10pm)", "Night owl (sleep after midnight)", "Somewhere in between", "Varies a lot"],
        "required": True,
    },
    "wake_time": {
        "question": "What time do you usually wake up?",
        "type": "select",
        "options": ["Before 6am", "6am–8am", "8am–10am", "After 10am", "Varies"],
    },
    "cooking_habits": {
        "question": "How often do you cook at home?",
        "type": "select",
        "options": ["Daily — I cook most meals", "A few times a week", "Rarely, mostly takeout/delivery", "Meal prep on weekends only"],
    },
    "kitchen_sharing": {
        "question": "How do you feel about sharing kitchen time/space?",
        "type": "select",
        "options": ["Happy to share and cook together sometimes", "Prefer separate times in the kitchen", "No strong preference", "I barely use the kitchen"],
    },
    "bathroom_time": {
        "question": "How long do you typically spend in the bathroom in the morning?",
        "type": "select",
        "options": ["Under 15 minutes", "15–30 minutes", "30–45 minutes", "Over 45 minutes"],
    },
    "common_space_usage": {
        "question": "How do you use common spaces (living room, etc.)?",
        "type": "select",
        "options": ["I spend a lot of time in common areas", "I mostly stay in my room", "Balanced use", "Depends on day"],
    },
    "cleanliness": {
        "question": "How would you rate your cleanliness standard? (1 = Relaxed, 5 = Spotless)",
        "type": "slider",
        "min": 1,
        "max": 5,
        "default": 3,
        "required": True,
    },
    "cleaning_schedule": {
        "question": "How do you prefer to handle shared cleaning?",
        "type": "select",
        "options": ["Rotating chore chart", "Clean as you go / whoever notices", "Hire a cleaner and split cost", "Discuss and decide together"],
    },
}

# ─────────────────────────────────────────────
# SECTION 4: GUESTS & SOCIAL LIFE
# ─────────────────────────────────────────────

SOCIAL_QUESTIONS = {
    "noise_level": {
        "question": "What's your noise and social preference at home?",
        "type": "select",
        "options": ["Very quiet, minimal guests", "Occasional friends over (weekends)", "Social and lively, guests often", "Balance of both — depends on the week"],
        "required": True,
    },
    "overnight_guests": {
        "question": "How often might you have overnight guests?",
        "type": "select",
        "options": ["Never / very rarely", "Occasionally (once a month or less)", "Regularly (weekly)", "Partner stays over frequently"],
        "required": True,
    },
    "guest_notice": {
        "question": "When having guests over, would you give advance notice?",
        "type": "select",
        "options": ["Always give notice", "Usually, for anything more than 1–2 people", "No strong opinion", "Prefer spontaneous — it's a shared home"],
    },
    "parties": {
        "question": "Are you okay with occasional parties or gatherings at home?",
        "type": "select",
        "options": ["Yes, I'd love that", "Small gatherings only (< 10 people)", "Rarely, and with advance notice", "No parties please"],
    },
    "introvert_extrovert": {
        "question": "How would you describe yourself socially?",
        "type": "slider",
        "min": 1,
        "max": 5,
        "default": 3,
        "labels": ["Very Introverted", "Very Extroverted"],
    },
}

# ─────────────────────────────────────────────
# SECTION 5: WORK & LIFESTYLE
# ─────────────────────────────────────────────

LIFESTYLE_QUESTIONS = {
    "work_from_home": {
        "question": "Do you work or study from home?",
        "type": "select",
        "options": ["Yes, full-time remote", "Hybrid (a few days a week)", "No, I go to office/school daily", "Varies by week"]
    },
    "quiet_hours_needed": {
        "question": "Do you need quiet hours for work/study calls?",
        "type": "select",
        "options": ["Yes, I'm on calls frequently during the day", "Occasionally — a few times a week", "Rarely, headphones handle it", "No, not an issue"]
    },
    "schedule_predictability": {
        "question": "How predictable is your daily schedule?",
        "type": "select",
        "options": ["Very consistent — same routine daily", "Mostly consistent with some variation", "Quite unpredictable / shift work", "Changes by season / project"]
    },
    "temperature_preference": {
        "question": "What's your thermostat preference at home?",
        "type": "select",
        "options": ["Cool (below 68°F / 20°C)", "Moderate (68–72°F / 20–22°C)", "Warm (above 72°F / 22°C)", "No strong preference"]
    },
    "hobbies": {
        "question": "What are your main hobbies or interests?",
        "type": "text",
        "placeholder": "e.g., gaming, cooking, hiking, music, yoga..."
    },
    "lifestyle_notes": {
        "question": "Anything else about your lifestyle a potential roommate should know?",
        "type": "text",
        "placeholder": "e.g., I practice guitar, I keep odd hours during finals, I fast in the mornings..."
    }
}

# ─────────────────────────────────────────────
# SECTION 6: PERSONALITY & CONFLICT
# ─────────────────────────────────────────────

PERSONALITY_QUESTIONS = {
    "conflict_style": {
        "question": "How do you prefer to handle conflicts?",
        "type": "select",
        "options": ["Direct conversation immediately", "Cool off first, then discuss", "Write it out (text/note)", "Prefer to avoid if possible"]
    },
    "communication_style": {
        "question": "How do you prefer to communicate with your roommate day-to-day?",
        "type": "select",
        "options": ["Group chat / text for everything", "Talk in person when needed", "Keep it minimal — respect each other's space", "A mix depending on the situation"]
    },
    "roommate_relationship": {
        "question": "What kind of relationship do you want with your roommate?",
        "type": "select",
        "options": ["Close friends — hang out regularly", "Friendly but independent", "Cordial — mutual respect, mostly separate lives", "No preference"]
    }
}

# ─────────────────────────────────────────────
# SECTION 7: DEALBREAKERS & PRIORITIES
# ─────────────────────────────────────────────

DEALBREAKER_QUESTIONS = {
    "non_negotiables": {
        "question": "Select your absolute NON-NEGOTIABLES (things you will not compromise on):",
        "type": "multiselect",
        "options": [
            "No smoking indoors",
            "No pets",
            "No overnight guests",
            "Strict quiet hours (e.g., no noise after 10pm)",
            "Must keep kitchen very clean",
            "No parties ever",
            "Same gender roommate only",
            "Budget hard cap (cannot exceed max)",
            "Must be okay with my pet(s)",
            "Non-smoking household only",
        ],
        "required": True,
        "help": "Select at least 1. These will never be compromised in matching.",
    },
    "top_priorities": {
        "question": "What are your TOP 3 priorities in a roommate?",
        "type": "multiselect",
        "options": [
            "Compatible sleep schedule",
            "Similar cleanliness standards",
            "Respectful of quiet/work time",
            "Budget compatibility",
            "Pet-friendly",
            "Matching social energy",
            "Location match",
            "Honest communication style",
            "Similar guest/party preferences",
        ],
        "max_select": 3,
        "required": True,
        "help": "Choose up to 3. These guide what your clone fights for in negotiation.",
    },
    "flexible_on": {
        "question": "What are you MOST flexible on? (things you're willing to negotiate)",
        "type": "multiselect",
        "options": [
            "Budget (within reason)",
            "Move-in date",
            "Lease length",
            "Chore split style",
            "Grocery arrangement",
            "Guest frequency",
            "Noise levels",
            "Temperature preference",
        ],
    },
    "custom_dealbreaker": {
        "question": "Any other dealbreakers not listed above?",
        "type": "text",
        "placeholder": "e.g., Must be okay with incense, no loud phone calls in common areas after 9pm...",
    },
}


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_all_questions() -> dict:
    """Return all question sections"""
    return {
        "living": LIVING_PREFERENCES,
        "financial": FINANCIAL_QUESTIONS,
        "routines": ROUTINE_QUESTIONS,
        "social": SOCIAL_QUESTIONS,
        "lifestyle": LIFESTYLE_QUESTIONS,
        "personality": PERSONALITY_QUESTIONS,
        "dealbreakers": DEALBREAKER_QUESTIONS
    }


def get_section_labels() -> dict:
    """Human-readable labels for each section (used in UI headers)"""
    return {
        "living": "🏠 Living Preferences",
        "financial": "💰 Financial & Utilities",
        "routines": "🌅 Daily Routines",
        "social": "🎉 Guests & Social Life",
        "lifestyle": "💼 Work & Lifestyle",
        "personality": "🤝 Personality & Communication",
        "dealbreakers": "🚨 Dealbreakers & Priorities"
    }


def get_non_negotiables(questionnaire: dict) -> list:
    """Extract non-negotiable items from a completed questionnaire"""
    return questionnaire.get("dealbreakers", {}).get("non_negotiables", [])


def get_flexible_items(questionnaire: dict) -> list:
    """Extract flexible items from a completed questionnaire"""
    return questionnaire.get("dealbreakers", {}).get("flexible_on", [])


def get_top_priorities(questionnaire: dict) -> list:
    """Extract top priorities from a completed questionnaire"""
    return questionnaire.get("dealbreakers", {}).get("top_priorities", [])


def get_budget_flexibility(questionnaire: dict) -> str:
    """Extract budget flexibility preference"""
    return questionnaire.get("living", {}).get("budget_flexibility", "No preference")


def get_user_gender(questionnaire: dict) -> str:
    """Extract user's own gender — used by clone for gender preference matching."""
    return questionnaire.get("living", {}).get("gender", "Prefer not to say")


def get_required_fields() -> dict:
    """
    Returns a flat dict of all required fields keyed as 'section.field_key'.
    Used by validate_questionnaire() and app.py to show * markers.
    """
    required = {}
    all_q = get_all_questions()
    for section_key, questions in all_q.items():
        for q_key, q in questions.items():
            if q.get("required"):
                required[f"{section_key}.{q_key}"] = q["question"]
    return required


def validate_questionnaire(collected: dict) -> list:
    """
    Validate a collected questionnaire dict against required fields.
    Returns a list of error strings. Empty list = valid.
    """
    errors = []
    all_q = get_all_questions()

    for section_key, questions in all_q.items():
        section_data = collected.get(section_key, {})
        for q_key, q in questions.items():
            if not q.get("required"):
                continue

            val = section_data.get(q_key)
            label = q["question"]

            # Text fields — must be non-empty string
            if q["type"] == "text":
                if not val or not str(val).strip():
                    errors.append(f"'{label}' is required.")

            # Number fields — treat 0 as invalid since budgets can't be 0
            elif q["type"] == "number":
                if val is None or val == 0:
                    errors.append(f"'{label}' is required and must be greater than 0.")

            # Multiselect — must have at least 1 selection
            elif q["type"] == "multiselect":
                if not val or len(val) == 0:
                    errors.append(f"'{label}' — please select at least one option.")

            # Slider — always has a value (default), so no validation needed
            # Select — always has a value (first option), so no validation needed

    # Extra cross-field validation
    living = collected.get("living", {})
    budget_min = living.get("budget_min", 0)
    budget_max = living.get("budget_max", 0)
    if budget_min and budget_max and budget_min > budget_max:
        errors.append("Minimum budget cannot be greater than maximum budget.")

    return errors