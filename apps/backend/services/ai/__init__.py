"""
AI Services Package

Provides AI processing capabilities including:
- LLM provider abstraction (Ollama, OpenAI, Anthropic)
- Model management and selection
- Text generation and completion
- Embedding generation
- Entity extraction
- Summarization
"""

from .providers import (
    LLMProvider,
    OllamaProvider,
    get_llm_provider,
)

__all__ = [
    "LLMProvider",
    "OllamaProvider",
    "get_llm_provider",
]
