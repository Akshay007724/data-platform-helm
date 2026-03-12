"""
Centralised LLM client — OpenAI-compatible, pointed at local Ollama.
All services import from here so model config lives in one place.
"""
import os
from openai import OpenAI

# Ollama exposes an OpenAI-compatible API at /v1
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1"

# Model names — override via environment variables in docker-compose.yml
VISION_MODEL = os.getenv("VISION_MODEL", "minicpm-v")  # for screenshots / images
TEXT_MODEL   = os.getenv("TEXT_MODEL",   "glm4")        # for text tasks

# Ollama doesn't need a real API key — use a placeholder
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Return a singleton OpenAI client pointed at the local Ollama instance."""
    global _client
    if _client is None:
        _client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
    return _client
