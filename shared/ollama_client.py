# ollama_client.py

import logging
import json

import ollama
from .config import OLLAMA_MODEL, DEBUG

# Configure debug logger - outputs to terminal when Streamlit runs
_logger = logging.getLogger("ollama_client")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[OLLAMA] %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)


def _log_llm_request(messages: list):
    """Log full payload being sent to Ollama"""
    if not DEBUG:
        return
    _logger.info("=" * 60)
    _logger.info("OUTGOING TO LLM (Ollama)")
    _logger.info("=" * 60)
    _logger.info(f"Model: {OLLAMA_MODEL}")
    _logger.info("-" * 40)
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        content = msg.get("content", "")[:500]
        if len(msg.get("content", "")) > 500:
            content += "... [truncated]"
        _logger.info(f"[{i}] {role}: {content}")
    _logger.info("=" * 60)


def _log_llm_response(content: str, raw_chunk=None):
    """Log response from LLM"""
    if not DEBUG:
        return
    _logger.info("-" * 60)
    _logger.info("RESPONSE FROM LLM")
    _logger.info("-" * 60)
    if raw_chunk:
        _logger.info(f"Raw chunk: {repr(raw_chunk)}")
    _logger.info(f"Content: {content}")
    _logger.info("=" * 60)


def check_ollama_running() -> bool:
    """Check if Ollama is running and model is available"""
    try:
        models = ollama.list()
        # ListResponse uses 'model' not 'name' for each item (ollama-python types)
        model_names = [m['model'] for m in models.get('models', []) if m.get('model')]
        # Check if our model exists (handle both 'gemma3' and 'gemma3:latest')
        return any(OLLAMA_MODEL in name for name in model_names)
    except Exception as e:
        print(f"Ollama error: {e}")
        return False

def chat(system_prompt: str, messages: list, stream: bool = True):
    """
    Send chat request to Ollama
    
    Args:
        system_prompt: The system prompt defining the AI's role
        messages: List of {"role": "user"|"assistant", "content": "..."}
        stream: Whether to stream the response
    
    Returns:
        Response content string, or generator if streaming
    """
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    _log_llm_request(full_messages)
    
    if stream:
        return ollama.chat(
            model=OLLAMA_MODEL,
            messages=full_messages,
            stream=True
        )
    
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=full_messages,
        stream=False
    )
    content = response.get("message", {}).get("content", "")
    _log_llm_response(content, raw_chunk=response)
    return content

def chat_stream(system_prompt: str, messages: list):
    """Generator that yields response chunks"""
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    _log_llm_request(full_messages)
    
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=full_messages,
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if 'message' in chunk and 'content' in chunk['message']:
            content = chunk['message']['content']
            full_response += content
            if DEBUG:
                _logger.debug(f"Chunk: {repr(chunk)}")
            yield content
    _log_llm_response(full_response, raw_chunk=f"(streamed, {len(full_response)} chars)")