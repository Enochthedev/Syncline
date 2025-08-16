"""
Embedding type definitions.

This module contains all data structures and enums used for
embedding generation and vector operations.
"""

import hashlib
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

    @classmethod
    def create(
        cls,
        text: str,
        model: str,
        provider: EmbeddingProvider,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'EmbeddingRequest':
        """Create a new embedding request with generated ID."""
        # Generate deterministic ID based on text and model
        content_hash = hashlib.sha256(
            f"{text}:{model}:{provider.value}".encode()).hexdigest()

        return cls(
            id=content_hash[:16],
            text=text,
            model=model,
            provider=provider,
            metadata=metadata or {}
        )


@dataclass
class EmbeddingResult:
    """Embedding generation result."""
    request_id: str
    text: str
    embedding: List[float]
    model: str
    provider: EmbeddingProvider
    dimensions: int = 0
    processing_time: float = 0.0
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Set dimensions after initialization."""
        if self.embedding and self.dimensions == 0:
            self.dimensions = len(self.embedding)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'request_id': self.request_id,
            'text': self.text,
            'embedding': self.embedding,
            'model': self.model,
            'provider': self.provider.value,
            'dimensions': self.dimensions,
            'processing_time': self.processing_time,
            'cached': self.cached,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingResult':
        """Create from dictionary."""
        return cls(
            request_id=data['request_id'],
            text=data['text'],
            embedding=data['embedding'],
            model=data['model'],
            provider=EmbeddingProvider(data['provider']),
            dimensions=data.get('dimensions', len(data['embedding'])),
            processing_time=data.get('processing_time', 0.0),
            cached=data.get('cached', False),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(
                data.get('created_at', datetime.utcnow().isoformat()))
        )


@dataclass
class BatchEmbeddingRequest:
    """Batch embedding generation request."""
    texts: List[str]
    model: str
    provider: EmbeddingProvider
    batch_size: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchEmbeddingResult:
    """Batch embedding generation result."""
    results: List[EmbeddingResult]
    total_processing_time: float = 0.0
    cached_count: int = 0
    generated_count: int = 0
    failed_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate counts after initialization."""
        self.cached_count = sum(1 for r in self.results if r.cached)
        self.generated_count = len(self.results) - self.cached_count
        # failed_count would be set separately based on exceptions
