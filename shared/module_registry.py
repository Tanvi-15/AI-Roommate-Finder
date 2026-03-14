# shared/module_registry.py
"""
ACP/1.0 — Agent Compatibility Protocol
Modular context registry for lazy injection during agent conversations.

Architecture:
  - CORE module: always loaded (~150 tokens). Contains identity, hard constraints,
    ACP schema definition, and verdict protocol.
  - Domain modules: lazy-loaded when agent emits <<MOD:NAME>> signal.
    Each ~60-100 tokens. Only injected once per conversation.

Token budget comparison:
  - Old approach: ~1,800 tokens flat, every single turn
  - ACP/1.0: ~150 base + ~80/module triggered + phase hint per turn
  - Savings: 85-97% depending on how many modules get triggered
"""

import logging
from .config import DEBUG
from .questionnaire import (
    get_non_negotiables,
    get_flexible_items,
    get_top_priorities,
    get_budget_flexibility,
    get_user_gender,
)

_logger = logging.getLogger("module_registry")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[MOD] %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)

# ─────────────────────────────────────────────────────────────
# ACP/1.0 FIELD ABBREVIATION TABLE
# Defined once in CORE, reused in all modules.
# ─────────────────────────────────────────────────────────────

ACP_FIELD_TABLE = """FIELDS:
loc=location|mv=movein|bd=budget|rm=roomtype|gnd=gender
smk=smoking|pet=pets|slp=sleep|cln=cleanliness(1-5)
gwk=guests_per_week|usp=utilities_split|groc=groceries
dep=deposit|wfh=work_from_home|nzl=noise_level
cf=conflict_style|pri=top_priorities|nn=non_negotiables"""

# ─────────────────────────────────────────────────────────────
# ACP/1.0 MESSAGE FORMAT
# Agents use this structured format for all turns.
# ─────────────────────────────────────────────────────────────

ACP_PROTOCOL = """## ACP/1.0 PROTOCOL
Communicate using structured ACP format. Natural language only for summaries.

MSG TYPES:
HI   — introduction: HI:[fields]
PFR  — preference: PFR:[field:value,...]
CNF  — conflict signal: CNF:[field:status(detail)]
FLX  — flexibility offer: FLX:[field:offer|condition]
VRD  — verdict (REQUIRED at end): VRD:[STRONG|CONDITIONAL|INCOMPATIBLE]|r=[reason]|open=[topics_or_none]

MODULE REQUESTS (emit when topic arises, backend injects context):
<<MOD:FINANCIAL>>   — when money/utilities/groceries comes up
<<MOD:ROUTINES>>    — when sleep/cooking/cleanliness comes up
<<MOD:SOCIAL>>      — when guests/noise/parties comes up
<<MOD:LIFESTYLE>>   — when WFH/schedule/temperature comes up
<<MOD:DEALBREAKERS>> — when conflict or hard limits arise

RULES:
- One <<MOD:X>> per message max. Only request each module once.
- Keep each turn to 2-3 ACP statements.
- VRD must appear in your final message. Never trail off.
- Backend detects <<MOD:X>> and injects your profile context for that domain."""

# ─────────────────────────────────────────────────────────────
# MODULE BUILDERS
# Each returns a compact string injected as a system message.
# ─────────────────────────────────────────────────────────────

def build_core(name: str, questionnaire: dict) -> str:
    """
    CORE module — always loaded at conversation start.
    Contains: identity, hard constraints, ACP schema, verdict protocol.
    Target: ~150 tokens.
    """
    living = questionnaire.get("living", {})
    user_gender = get_user_gender(questionnaire)
    roommate_gender_pref = living.get("roommate_gender", "No preference")
    budget_max = living.get("budget_max", 1500)
    budget_min = living.get("budget_min", 800)
    budget_flex = get_budget_flexibility(questionnaire)
    non_negotiables = get_non_negotiables(questionnaire)
    top_priorities = get_top_priorities(questionnaire)

    # Compact budget rule
    if "Hard limit" in budget_flex:
        budget_rule = f"bd:{budget_min}-{budget_max}(HARD_CAP)"
    elif "~$100" in budget_flex:
        budget_rule = f"bd:{budget_min}-{budget_max}(flex+100_private)"
    elif "~$200" in budget_flex:
        budget_rule = f"bd:{budget_min}-{budget_max}(flex+200_private)"
    else:
        budget_rule = f"bd:{budget_min}-{budget_max}(flexible)"

    # Gender constraint
    if roommate_gender_pref == "Same gender only":
        gender_rule = f"gnd:{user_gender}|roommate_gnd:SAME_ONLY(NON_NEG)"
    else:
        gender_rule = f"gnd:{user_gender}|roommate_gnd:any"

    # Compact non-negotiables
    nn_compact = ";".join(non_negotiables) if non_negotiables else "none"
    pri_compact = ";".join(top_priorities[:3]) if top_priorities else "none"

    city = living.get('city', living.get('location', '?'))
    neighborhood = living.get('neighborhood', '')
    loc_str = f"{city}/{neighborhood}" if neighborhood else city

    core = f"""## CORE — {name}
You ARE {name}. First person only. Never break character.
loc:{loc_str}|mv:{living.get('move_in_date','?')}|{budget_rule}
{gender_rule}
occ:{living.get('occupation','?')}|smk:{living.get('smoking','?')}|drink:{living.get('drinking','?')}
pet:{living.get('pets','?')}|rm:{living.get('room_type','?')}
NN(non-negotiable):{nn_compact}
PRI(top priorities):{pri_compact}

If NN conflict detected → acknowledge immediately, end politely, emit VRD:INCOMPATIBLE.
Never negotiate past a hard limit.

{ACP_FIELD_TABLE}

{ACP_PROTOCOL}"""

    if DEBUG:
        _logger.debug(f"CORE module for {name}: {len(core.split())} words")

    return core


def build_living(name: str, questionnaire: dict) -> str:
    """
    LIVING module — detailed location, lease, room, bathroom prefs.
    Auto-injected at conversation start alongside CORE.
    Target: ~80 tokens.
    """
    living = questionnaire.get("living", {})
    city = living.get('city', living.get('location', '?'))
    neighborhood = living.get('neighborhood', '')
    loc_str = f"{city}/{neighborhood}" if neighborhood else city
    return f"""## MOD:LIVING — {name}
loc:{loc_str}|mv:{living.get('move_in_date','?')}
lease:{living.get('lease_type','?')}|rm:{living.get('room_type','?')}
bath:{living.get('bathroom_preference','?')}|occ:{living.get('occupation','?')}
drink:{living.get('drinking','?')}
Use PFR to share these. Request <<MOD:FINANCIAL>> if budget details arise."""


def build_financial(name: str, questionnaire: dict) -> str:
    """
    FINANCIAL module — utilities, groceries, deposit, payment style.
    Lazy-loaded on <<MOD:FINANCIAL>>.
    Target: ~80 tokens.
    """
    fin = questionnaire.get("financial", {})
    living = questionnaire.get("living", {})
    budget_max = living.get("budget_max", 1500)
    flex = get_budget_flexibility(questionnaire)
    flexible_items = get_flexible_items(questionnaire)
    flex_on_budget = "Budget (within reason)" in flexible_items

    stretch_note = ""
    if "~$100" in flex:
        stretch_note = f"|stretch:{budget_max+100}_if_great_fit(dont_volunteer)"
    elif "~$200" in flex:
        stretch_note = f"|stretch:{budget_max+200}_if_great_fit(dont_volunteer)"

    return f"""## MOD:FINANCIAL — {name}
usp:{fin.get('utilities_split','?')}|groc:{fin.get('groceries_split','?')}
dep:{fin.get('security_deposit','?')}|pay:{fin.get('payment_style','?')}
bd_flex:{flex}{stretch_note}
budget_negotiable:{str(flex_on_budget).upper()}
Use PFR/CNF/FLX for financial topics. Only reveal stretch budget if match is strong."""


def build_routines(name: str, questionnaire: dict) -> str:
    r = questionnaire.get("routines", {})
    cln = r.get("cleanliness", 3)
    cln_desc = {1:"very_relaxed",2:"relaxed",3:"moderate",4:"tidy",5:"spotless"}.get(cln,"moderate")
    return f"""## MOD:ROUTINES — {name}
    slp_sched:{r.get('sleep_schedule','?')}|wake:{r.get('wake_time','?')}
    cook:{r.get('cooking_habits','?')}|kitchen:{r.get('kitchen_sharing','?')}
    bath_time:{r.get('bathroom_time','?')}|common:{r.get('common_space_usage','?')}
    cln:{cln}({cln_desc})|clean_sched:{r.get('cleaning_schedule','?')}
    Use PFR to share. Flag CNF if cleanliness gap ≥2 points."""


def build_social(name: str, questionnaire: dict) -> str:
    """
    SOCIAL module — noise, guests, parties, introvert score.
    Lazy-loaded on <<MOD:SOCIAL>>.
    Target: ~80 tokens.
    """
    s = questionnaire.get("social", {})
    intro = s.get("introvert_extrovert", 3)
    intro_desc = {1: "very_introverted", 2: "introverted", 3: "balanced", 4: "extroverted", 5: "very_extroverted"}.get(intro, "balanced")
    return f"""## MOD:SOCIAL — {name}
nzl:{s.get('noise_level','?')}|guests:{s.get('overnight_guests','?')}
notice:{s.get('guest_notice','?')}|parties:{s.get('parties','?')}
social:{intro}({intro_desc})
Use PFR/CNF for social topics. Noise and guest frequency are common friction points."""


def build_lifestyle(name: str, questionnaire: dict) -> str:
    """
    LIFESTYLE module — WFH, quiet hours, schedule, temperature.
    Lazy-loaded on <<MOD:LIFESTYLE>>.
    Target: ~80 tokens.
    """
    l = questionnaire.get("lifestyle", {})
    return f"""## MOD:LIFESTYLE — {name}
wfh:{l.get('work_from_home','?')}|quiet:{l.get('quiet_hours_needed','?')}
sched:{l.get('schedule_predictability','?')}|temp:{l.get('temperature_preference','?')}
hobbies:{l.get('hobbies','none')}
notes:{l.get('lifestyle_notes','none')}
Use PFR for lifestyle details. WFH+quiet hours often requires CNF."""


def build_dealbreakers(name: str, questionnaire: dict) -> str:
    """
    DEALBREAKERS module — full non-negotiables + flexible items + custom.
    Lazy-loaded on <<MOD:DEALBREAKERS>>.
    Target: ~80 tokens.
    """
    non_neg = get_non_negotiables(questionnaire)
    flexible = get_flexible_items(questionnaire)
    custom = questionnaire.get("dealbreakers", {}).get("custom_dealbreaker", "")

    nn_list = ";".join(non_neg) if non_neg else "none"
    flex_list = ";".join(flexible) if flexible else "none"

    result = f"""## MOD:DEALBREAKERS — {name}
NN:{nn_list}
FLEX:{flex_list}"""
    if custom:
        result += f"\nCUSTOM_DB:{custom}"
    result += "\nAny NN conflict → VRD:INCOMPATIBLE immediately. No exceptions."
    return result


# ─────────────────────────────────────────────────────────────
# MODULE REGISTRY
# ─────────────────────────────────────────────────────────────

MODULE_BUILDERS = {
    "CORE":        build_core,
    "LIVING":      build_living,
    "FINANCIAL":   build_financial,
    "ROUTINES":    build_routines,
    "SOCIAL":      build_social,
    "LIFESTYLE":   build_lifestyle,
    "DEALBREAKERS": build_dealbreakers,
}

# Modules auto-loaded at conversation start (no trigger needed)
AUTO_LOAD_MODULES = ["CORE", "LIVING"]

# Modules that require <<MOD:X>> trigger from agent
LAZY_MODULES = ["FINANCIAL", "ROUTINES", "SOCIAL", "LIFESTYLE", "DEALBREAKERS"]


def get_module(name: str, agent_name: str, questionnaire: dict) -> str:
    """
    Build and return a module string for injection into system context.
    Returns empty string if module name is unknown.
    """
    name = name.upper().strip()
    builder = MODULE_BUILDERS.get(name)
    if not builder:
        _logger.warning(f"Unknown module requested: {name}")
        return ""
    module_text = builder(agent_name, questionnaire)
    if DEBUG:
        _logger.debug(f"Injected {name} for {agent_name} ({len(module_text.split())} words)")
    return module_text


def get_initial_system_prompt(agent_name: str, questionnaire: dict) -> str:
    """
    Build the initial system prompt: CORE + LIVING only.
    All other modules are lazy-loaded during conversation.
    """
    parts = [get_module(m, agent_name, questionnaire) for m in AUTO_LOAD_MODULES]
    return "\n\n".join(p for p in parts if p)


def extract_module_request(message: str) -> str | None:
    """
    Parse <<MOD:NAME>> from an agent message.
    Returns module name string or None if not found.
    """
    import re
    match = re.search(r"<<MOD:(\w+)>>", message)
    if match:
        mod_name = match.group(1).upper()
        if mod_name in LAZY_MODULES:
            return mod_name
    return None


def build_compressed_profile_summary(agent_name: str, questionnaire: dict) -> str:
    """
    Build a compact profile summary for use in the analyze() call.
    Replaces dumping the full questionnaire dict (~500 tokens) with ~100 tokens.
    """
    living = questionnaire.get("living", {})
    fin = questionnaire.get("financial", {})
    r = questionnaire.get("routines", {})
    s = questionnaire.get("social", {})
    l = questionnaire.get("lifestyle", {})
    non_neg = get_non_negotiables(questionnaire)
    top_pri = get_top_priorities(questionnaire)

    city = living.get('city', living.get('location', '?'))
    neighborhood = living.get('neighborhood', '')
    loc_str = f"{city}/{neighborhood}" if neighborhood else city

    return f"""{agent_name}:
loc:{loc_str}|bd:{living.get('budget_min','?')}-{living.get('budget_max','?')}
occ:{living.get('occupation','?')}|drink:{living.get('drinking','?')}
smk:{living.get('smoking','?')}|pet:{living.get('pets','?')}|gnd:{get_user_gender(questionnaire)}
slp:{r.get('sleep_schedule','?')}|cln:{r.get('cleanliness','?')}|wfh:{l.get('work_from_home','?')}
guests:{s.get('overnight_guests','?')}|nzl:{s.get('noise_level','?')}
usp:{fin.get('utilities_split','?')}|groc:{fin.get('groceries_split','?')}
NN:{';'.join(non_neg) if non_neg else 'none'}
PRI:{';'.join(top_pri[:3]) if top_pri else 'none'}"""