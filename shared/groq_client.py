# shared/groq_client.py
"""
Drop-in replacement for ollama_client.py using Groq API.
All function signatures are identical so server.py import swap is the only change needed.
"""

import os
import logging
from groq import Groq
from .config import GROQ_MODEL, DEBUG

_logger = logging.getLogger("groq_client")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[GROQ] %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)

_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def chat(messages: list, system_prompt: str = None) -> str:
    """
    Send a conversation to Groq and return the response string.
    Drop-in replacement for ollama_client.chat().
    """
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    if DEBUG:
        total_chars = sum(len(m["content"]) for m in all_messages)
        _logger.debug(f"Sending {len(all_messages)} messages (~{total_chars} chars)")

    response = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=all_messages,
        max_tokens=500,
        temperature=0.7,
    )
    content = response.choices[0].message.content

    if DEBUG:
        _logger.debug(f"Response: {content[:200]}...")

    return content


def chat_stream(system_prompt: str, messages: list):
    """
    Stream response tokens. Used by clone chat preview.
    Drop-in replacement for ollama_client.chat_stream().
    """
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    stream = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=all_messages,
        max_tokens=500,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def check_ollama_running() -> bool:
    """
    Legacy compatibility check — now just verifies GROQ_API_KEY is set.
    Called by app.py home page status check.
    """
    return bool(os.environ.get("GROQ_API_KEY"))


def generate(prompt: str) -> str:
    """Single-turn generation. Legacy compatibility."""
    return chat([{"role": "user", "content": prompt}])