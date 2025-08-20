"""
Embedding services for the MESH AI system.

This package provides text embedding generation using various providers
with caching and batch processing capabilities.
"""

from .providers import OpenAIEmbeddingProvider, SentenceTransformersProvider
from .types import EmbeddingRequest, EmbeddingResult, EmbeddingProvider, EmbeddingCache

__all__ = [
    'OpenAIEmbeddingProvider',
    'SentenceTransformersProvider',
    'EmbeddingRequest',
    'EmbeddingResult',
    'EmbeddingProvider',
    'EmbeddingCache'
]
