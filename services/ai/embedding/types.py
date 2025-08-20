"""
Type definitions for embedding services.

This module provides data classes and enums for embedding operations.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OLLAMA = "ollama"


@dataclass
class EmbeddingRequest:
    """Embedding generation request."""
    id: str
    text: str
    model: str
    provider: EmbeddingProvider
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EmbeddingResult:
    """Embedding generation result."""
    request_id: str
    text: str
    embedding: List[float]
    model: str
    provider: EmbeddingProvider
    dimensions: int
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class EmbeddingError(Exception):
    """Base exception for embedding errors."""
    pass


class EmbeddingProviderError(EmbeddingError):
    """Error from embedding provider."""
    pass


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""

    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, EmbeddingResult] = {}
        self.max_size = max_size
        self.access_times: Dict[str, datetime] = {}

    def _generate_key(self, text: str, model: str, provider: str) -> str:
        """Generate cache key for text, model, and provider combination."""
        content = f"{text}:{model}:{provider}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model: str, provider: str) -> Optional[EmbeddingResult]:
        """Get cached embedding result."""
        key = self._generate_key(text, model, provider)

        if key in self.cache:
            self.access_times[key] = datetime.utcnow()
            return self.cache[key]

        return None

    def put(self, result: EmbeddingResult) -> None:
        """Cache embedding result."""
        key = self._generate_key(
            result.text, result.model, result.provider.value)

        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = result
        self.access_times[key] = datetime.utcnow()

    def _evict_oldest(self) -> None:
        """Evict the oldest accessed entry."""
        if not self.access_times:
            return

        oldest_key = min(self.access_times.keys(),
                         key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.access_times.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)
