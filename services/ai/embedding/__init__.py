"""
Embedding generation services.

This package contains all embedding functionality including
providers, caching, and vector operations.
"""

from .service import EmbeddingService, get_embedding_service
from .types import EmbeddingRequest, EmbeddingResult, EmbeddingProvider
from .cache import EmbeddingCache
from .providers import OpenAIEmbeddingProvider, OllamaEmbeddingProvider

__all__ = [
    'EmbeddingService',
    'get_embedding_service',
    'EmbeddingRequest',
    'EmbeddingResult',
    'EmbeddingProvider',
    'EmbeddingCache',
    'OpenAIEmbeddingProvider',
    'OllamaEmbeddingProvider'
]
