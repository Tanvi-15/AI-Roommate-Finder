# shared/clone.py
"""
Clone prompt generation.

With ACP/1.0, generate_clone_prompt() now returns ONLY the CORE+LIVING modules
(~230 tokens) instead of the monolithic 1,800-token prompt.

Additional modules (FINANCIAL, ROUTINES, SOCIAL, LIFESTYLE, DEALBREAKERS) are
lazy-loaded by server.py when the agent emits <<MOD:NAME>> during conversation.

Existing call sites (server.py Agent.__init__, clone chat preview) are unchanged —
they still call generate_clone_prompt(name, questionnaire) and get a system prompt back.
"""

import logging
from .config import DEBUG
from .module_registry import get_initial_system_prompt

_logger = logging.getLogger("clone")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[CLONE] %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)


def generate_clone_prompt(name: str, questionnaire: dict) -> str:
    """
    Generate the initial system prompt for an agent clone.

    Returns CORE + LIVING modules only (~230 tokens).
    Remaining modules injected lazily via server.py on <<MOD:X>> signals.

    Previously: ~1,800 tokens flat
    Now: ~230 tokens + ~80 per triggered module
    """
    prompt = get_initial_system_prompt(name, questionnaire)

    if DEBUG:
        _logger.debug("=" * 60)
        _logger.debug(f"Initial prompt for {name} ({len(prompt.split())} words):")
        _logger.debug(prompt)
        _logger.debug("=" * 60)

    return prompt


def get_clone_intro(name: str) -> str:
    """Opening message when a user chats with their own clone (preview mode)."""
    return (
        f"Hey! I'm {name}'s AI clone. I know everything about their roommate preferences, "
        f"their non-negotiables, and what they're flexible on. "
        f"Ask me anything to see if you'd be a good fit!"
    )