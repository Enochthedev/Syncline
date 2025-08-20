"""
Embedding provider implementations.

This module provides concrete implementations for different embedding
providers including OpenAI and local sentence transformers.
"""

import asyncio
import logging
from typing import List, Optional

import openai
from openai import AsyncOpenAI

from config.config import settings
from .types import EmbeddingProviderError

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.default_model = settings.DEFAULT_EMBEDDING_MODEL

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """Generate embedding using OpenAI API."""
        model = model or self.default_model

        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise EmbeddingProviderError(f"OpenAI embedding failed: {e}")

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        model = model or self.default_model

        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=model
            )

            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise EmbeddingProviderError(f"OpenAI batch embedding failed: {e}")


class SentenceTransformersProvider:
    """Sentence Transformers embedding provider (local)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    async def _load_model(self):
        """Load the sentence transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(
                    f"Loaded SentenceTransformers model: {self.model_name}")
            except ImportError:
                raise EmbeddingProviderError(
                    "sentence-transformers package not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                raise EmbeddingProviderError(
                    f"Failed to load model {self.model_name}: {e}")

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generate embedding using SentenceTransformers."""
        await self._load_model()

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self._model.encode, text
            )

            return embedding.tolist()

        except Exception as e:
            logger.error(
                f"SentenceTransformers embedding generation failed: {e}")
            raise EmbeddingProviderError(
                f"SentenceTransformers embedding failed: {e}")

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        await self._load_model()

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, self._model.encode, texts
            )

            return embeddings.tolist()

        except Exception as e:
            logger.error(
                f"SentenceTransformers batch embedding generation failed: {e}")
            raise EmbeddingProviderError(
                f"SentenceTransformers batch embedding failed: {e}")


class OllamaEmbeddingProvider:
    """Ollama embedding provider for local models."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "nomic-embed-text"):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generate embedding using Ollama API."""
        model = model or self.model_name

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text
                    }
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["embedding"]

        except Exception as e:
            logger.error(f"Ollama embedding generation failed: {e}")
            raise EmbeddingProviderError(f"Ollama embedding failed: {e}")

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts using Ollama."""
        # Ollama doesn't support batch embeddings, so we'll process sequentially
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text, model)
            embeddings.append(embedding)
        return embeddings
