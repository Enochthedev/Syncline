"""
Embedding generation utilities for vector search and semantic analysis.

This service provides text embedding generation using various providers
(OpenAI, local models) for semantic search and AI processing.
"""

import asyncio
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from config.config import settings
from .pii_redaction import get_pii_redaction_service
from .embedding.types import (
    EmbeddingProvider, EmbeddingRequest, EmbeddingResult,
    EmbeddingError, EmbeddingCache
)
from .embedding.providers import (
    OpenAIEmbeddingProvider, SentenceTransformersProvider, OllamaEmbeddingProvider
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings with multiple provider support.

    Provides caching, PII redaction, and batch processing capabilities.
    """

    def __init__(
        self,
        default_provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        cache_size: int = 10000,
        enable_pii_redaction: bool = True
    ):
        """Initialize the embedding service."""
        self.default_provider = default_provider
        self.enable_pii_redaction = enable_pii_redaction

        # Initialize providers lazily
        self.providers = {}
        self._provider_classes = {
            EmbeddingProvider.OPENAI: OpenAIEmbeddingProvider,
            EmbeddingProvider.SENTENCE_TRANSFORMERS: SentenceTransformersProvider,
            EmbeddingProvider.OLLAMA: OllamaEmbeddingProvider,
        }

        # Initialize cache
        self.cache = EmbeddingCache(max_size=cache_size)

        # Statistics
        self.stats = {
            'embeddings_generated': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processing_time': 0.0,
            'provider_usage': {},
            'pii_redactions': 0
        }

        logger.info(
            f"Embedding service initialized with provider: {default_provider}")

    def _get_provider(self, provider: EmbeddingProvider):
        """Get or create a provider instance."""
        if provider not in self.providers:
            if provider not in self._provider_classes:
                raise EmbeddingError(f"Unsupported provider: {provider}")

            try:
                self.providers[provider] = self._provider_classes[provider]()
            except Exception as e:
                raise EmbeddingError(
                    f"Failed to initialize {provider} provider: {e}")

        return self.providers[provider]

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        provider: Optional[EmbeddingProvider] = None,
        redact_pii: Optional[bool] = None,
        use_cache: bool = True
    ) -> EmbeddingResult:
        """
        Generate embedding for text.

        Args:
            text: Text to embed
            model: Model to use (provider-specific)
            provider: Embedding provider to use
            redact_pii: Whether to redact PII before embedding
            use_cache: Whether to use caching

        Returns:
            EmbeddingResult with embedding and metadata
        """
        start_time = datetime.utcnow()

        provider = provider or self.default_provider
        redact_pii = redact_pii if redact_pii is not None else self.enable_pii_redaction

        if not text or not text.strip():
            raise EmbeddingError("Empty text provided for embedding")

        # Apply PII redaction if enabled
        processed_text = text
        pii_redacted = False

        if redact_pii:
            pii_service = await get_pii_redaction_service()
            redaction_result = await pii_service.redact_text(text)
            processed_text = redaction_result.redacted_text
            pii_redacted = len(redaction_result.entities) > 0

            if pii_redacted:
                self.stats['pii_redactions'] += 1
                logger.debug(
                    f"Redacted {len(redaction_result.entities)} PII entities before embedding")

        # Check cache
        if use_cache:
            cached_result = self.cache.get(
                processed_text, model or "default", provider.value)
            if cached_result:
                self.stats['cache_hits'] += 1
                logger.debug("Retrieved embedding from cache")
                return cached_result
            else:
                self.stats['cache_misses'] += 1

        # Generate embedding
        try:
            embedding_provider = self._get_provider(provider)
            embedding = await embedding_provider.generate_embedding(processed_text, model)

            # Create result
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = EmbeddingResult(
                request_id=hashlib.sha256(
                    f"{processed_text}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16],
                text=processed_text,
                embedding=embedding,
                model=model or "default",
                provider=provider,
                dimensions=len(embedding),
                processing_time=processing_time,
                metadata={
                    'original_text_length': len(text),
                    'processed_text_length': len(processed_text),
                    'pii_redacted': pii_redacted,
                    'cache_used': use_cache
                }
            )

            # Cache result
            if use_cache:
                self.cache.put(result)

            # Update statistics
            self._update_stats(provider, processing_time)

            logger.debug(
                f"Generated {len(embedding)}-dimensional embedding "
                f"using {provider.value} in {processing_time:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        provider: Optional[EmbeddingProvider] = None,
        redact_pii: Optional[bool] = None,
        use_cache: bool = True,
        batch_size: int = 100
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed
            model: Model to use
            provider: Embedding provider
            redact_pii: Whether to redact PII
            use_cache: Whether to use caching
            batch_size: Maximum batch size for provider calls

        Returns:
            List of EmbeddingResult objects
        """
        if not texts:
            return []

        provider = provider or self.default_provider
        redact_pii = redact_pii if redact_pii is not None else self.enable_pii_redaction

        results = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Check cache and separate cached vs uncached
            cached_results = {}
            uncached_texts = []
            uncached_indices = []

            if use_cache:
                for j, text in enumerate(batch):
                    # Apply PII redaction for cache lookup
                    processed_text = text
                    if redact_pii:
                        pii_service = await get_pii_redaction_service()
                        redaction_result = await pii_service.redact_text(text)
                        processed_text = redaction_result.redacted_text

                    cached_result = self.cache.get(
                        processed_text, model or "default", provider.value)
                    if cached_result:
                        cached_results[i + j] = cached_result
                        self.stats['cache_hits'] += 1
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(i + j)
                        self.stats['cache_misses'] += 1
            else:
                uncached_texts = batch
                uncached_indices = list(range(i, i + len(batch)))

            # Generate embeddings for uncached texts
            if uncached_texts:
                uncached_results = await asyncio.gather(*[
                    self.generate_embedding(
                        text, model, provider, redact_pii, use_cache=False
                    )
                    for text in uncached_texts
                ], return_exceptions=True)

                # Cache successful results
                for result in uncached_results:
                    if isinstance(result, EmbeddingResult) and use_cache:
                        self.cache.put(result)

                # Combine with cached results
                for idx, result in zip(uncached_indices, uncached_results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Failed to generate embedding for text {idx}: {result}")
                        # Create error result
                        results.append(EmbeddingResult(
                            request_id=f"error_{idx}",
                            text=texts[idx],
                            embedding=[],
                            model=model or "default",
                            provider=provider,
                            dimensions=0,
                            metadata={'error': str(result)}
                        ))
                    else:
                        results.append(result)

            # Add cached results in correct order
            for idx in range(i, i + len(batch)):
                if idx in cached_results:
                    results.insert(idx, cached_results[idx])

        # Ensure results are in correct order
        results.sort(key=lambda r: texts.index(r.text)
                     if r.text in texts else float('inf'))

        return results

    def _update_stats(self, provider: EmbeddingProvider, processing_time: float) -> None:
        """Update processing statistics."""
        self.stats['embeddings_generated'] += 1
        self.stats['total_processing_time'] += processing_time

        provider_key = provider.value
        if provider_key not in self.stats['provider_usage']:
            self.stats['provider_usage'][provider_key] = 0
        self.stats['provider_usage'][provider_key] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics."""
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']

        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / total_requests
                if total_requests > 0 else 0.0
            ),
            'cache_size': self.cache.size(),
            'average_processing_time': (
                self.stats['total_processing_time'] /
                self.stats['embeddings_generated']
                if self.stats['embeddings_generated'] > 0 else 0.0
            ),
            'default_provider': self.default_provider.value,
            'pii_redaction_enabled': self.enable_pii_redaction
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the embedding service."""
        try:
            # Test embedding generation
            test_text = "This is a test message for health check"
            result = await self.generate_embedding(test_text, use_cache=False)

            return {
                'status': 'healthy',
                'test_successful': len(result.embedding) > 0,
                'embedding_dimensions': result.dimensions,
                'provider': result.provider.value,
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'test_successful': False,
                'stats': self.get_stats()
            }

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")


# Global embedding service instance
embedding_service = EmbeddingService()


async def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    return embedding_service
