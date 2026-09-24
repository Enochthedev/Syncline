"""
Embedding Service

Generates and manages vector embeddings for semantic search:
- Text embedding generation using Ollama
- Batch processing for efficiency
- Storage in ChromaDB and PostgreSQL
- Embedding retrieval and management
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.embedding import Embedding
from db.models.message import Message
from services.ai.providers import LLMProvider, get_llm_provider
from services.vector_db.chroma_client import ChromaDBClient, get_chroma_client

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and managing embeddings.

    Provides functionality for:
    - Generating embeddings for messages
    - Batch processing for efficiency
    - Storing embeddings in both ChromaDB and PostgreSQL
    - Retrieving and managing embeddings
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        chroma_client: Optional[ChromaDBClient] = None,
        batch_size: Optional[int] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize embedding service.

        Args:
            llm_provider: LLM provider for embeddings
            chroma_client: ChromaDB client
            batch_size: Batch size for processing
            embedding_model: Model name for embeddings
        """
        self.llm_provider = llm_provider or get_llm_provider()
        self.chroma_client = chroma_client or get_chroma_client()
        self.batch_size = batch_size or settings.AI_BATCH_SIZE
        self.embedding_model = embedding_model or settings.DEFAULT_EMBEDDING_MODEL

        logger.info(
            f"Initialized EmbeddingService with model {self.embedding_model}, "
            f"batch_size={self.batch_size}"
        )

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            model: Model name (uses default if not specified)

        Returns:
            Embedding vector
        """
        model = model or self.embedding_model

        try:
            # Generate embedding using LLM provider
            embeddings = await self.llm_provider.embed(text, model=model)

            # Return first embedding (single text)
            if embeddings and len(embeddings) > 0:
                return embeddings[0]

            logger.error("No embedding returned from provider")
            return []

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def generate_embeddings_batch(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed
            model: Model name (uses default if not specified)

        Returns:
            List of embedding vectors
        """
        model = model or self.embedding_model

        try:
            # Generate embeddings using LLM provider
            embeddings = await self.llm_provider.embed(texts, model=model)

            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    async def embed_message(
        self,
        message: Message,
        db: AsyncSession,
        force_regenerate: bool = False,
    ) -> Optional[Embedding]:
        """
        Generate and store embedding for a message.

        Args:
            message: Message to embed
            db: Database session
            force_regenerate: Force regeneration if embedding exists

        Returns:
            Embedding object or None if failed
        """
        try:
            # Check if embedding already exists
            if not force_regenerate and message.embeddings:
                logger.debug(f"Embedding already exists for message {message.id}")
                return message.embeddings

            # Extract text content from message
            text = self._extract_text_from_message(message)

            if not text:
                logger.warning(f"No text content in message {message.id}")
                return None

            # Generate embedding
            vector = await self.generate_embedding(text)

            if not vector:
                logger.error(f"Failed to generate embedding for message {message.id}")
                return None

            # Store in PostgreSQL
            if message.embeddings and force_regenerate:
                # Update existing embedding
                message.embeddings.vector = vector
                message.embeddings.model = self.embedding_model
                embedding = message.embeddings
            else:
                # Create new embedding
                embedding = Embedding(
                    message_id=message.id,
                    vector=vector,
                    model=self.embedding_model,
                )
                db.add(embedding)

            await db.commit()
            await db.refresh(embedding)

            # Store in ChromaDB
            await self._store_in_chromadb(
                message_id=str(message.id),
                text=text,
                embedding=vector,
                metadata={
                    "platform": message.platform,
                    "timestamp": message.timestamp.isoformat(),
                    "thread_id": message.thread_id,
                },
            )

            logger.info(f"Generated and stored embedding for message {message.id}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to embed message {message.id}: {e}")
            await db.rollback()
            return None

    async def embed_messages_batch(
        self,
        messages: list[Message],
        db: AsyncSession,
        force_regenerate: bool = False,
    ) -> list[Optional[Embedding]]:
        """
        Generate and store embeddings for multiple messages in batch.

        Args:
            messages: List of messages to embed
            db: Database session
            force_regenerate: Force regeneration if embeddings exist

        Returns:
            List of embedding objects (None for failed)
        """
        try:
            # Filter messages that need embeddings
            messages_to_embed = []
            for message in messages:
                if force_regenerate or not message.embeddings:
                    messages_to_embed.append(message)

            if not messages_to_embed:
                logger.debug("All messages already have embeddings")
                return [msg.embeddings for msg in messages]

            logger.info(f"Embedding {len(messages_to_embed)} messages in batch")

            # Extract texts
            texts = [self._extract_text_from_message(msg) for msg in messages_to_embed]

            # Filter out empty texts
            valid_indices = [i for i, text in enumerate(texts) if text]
            valid_texts = [texts[i] for i in valid_indices]
            valid_messages = [messages_to_embed[i] for i in valid_indices]

            if not valid_texts:
                logger.warning("No valid texts to embed")
                return [None] * len(messages)

            # Generate embeddings in batch
            vectors = await self.generate_embeddings_batch(valid_texts)

            # Store embeddings
            embeddings = []
            for message, vector in zip(valid_messages, vectors):
                if message.embeddings and force_regenerate:
                    # Update existing
                    message.embeddings.vector = vector
                    message.embeddings.model = self.embedding_model
                    embedding = message.embeddings
                else:
                    # Create new
                    embedding = Embedding(
                        message_id=message.id,
                        vector=vector,
                        model=self.embedding_model,
                    )
                    db.add(embedding)

                embeddings.append(embedding)

            await db.commit()

            # Refresh embeddings
            for embedding in embeddings:
                await db.refresh(embedding)

            # Store in ChromaDB in batch
            await self._store_batch_in_chromadb(
                message_ids=[str(msg.id) for msg in valid_messages],
                texts=valid_texts,
                embeddings=vectors,
                metadatas=[
                    {
                        "platform": msg.platform,
                        "timestamp": msg.timestamp.isoformat(),
                        "thread_id": msg.thread_id,
                    }
                    for msg in valid_messages
                ],
            )

            logger.info(f"Successfully embedded {len(embeddings)} messages")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to embed messages batch: {e}")
            await db.rollback()
            return [None] * len(messages)

    async def get_embedding(
        self,
        message_id: UUID,
        db: AsyncSession,
    ) -> Optional[Embedding]:
        """
        Get embedding for a message.

        Args:
            message_id: Message ID
            db: Database session

        Returns:
            Embedding object or None if not found
        """
        try:
            result = await db.execute(
                select(Embedding).where(Embedding.message_id == message_id)
            )
            embedding = result.scalar_one_or_none()
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding for message {message_id}: {e}")
            return None

    async def delete_embedding(
        self,
        message_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        Delete embedding for a message.

        Args:
            message_id: Message ID
            db: Database session

        Returns:
            True if successful
        """
        try:
            # Delete from PostgreSQL
            embedding = await self.get_embedding(message_id, db)
            if embedding:
                await db.delete(embedding)
                await db.commit()

            # Delete from ChromaDB
            self.chroma_client.delete_documents(ids=[str(message_id)])

            logger.info(f"Deleted embedding for message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete embedding for message {message_id}: {e}")
            await db.rollback()
            return False

    async def process_unembedded_messages(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
    ) -> int:
        """
        Process messages that don't have embeddings yet.

        Args:
            db: Database session
            limit: Maximum number of messages to process

        Returns:
            Number of messages processed
        """
        try:
            # Find messages without embeddings
            query = (
                select(Message)
                .outerjoin(Embedding)
                .where(Embedding.id.is_(None))
                .order_by(Message.created_at.desc())
            )

            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            messages = result.scalars().all()

            if not messages:
                logger.info("No unembedded messages found")
                return 0

            logger.info(f"Found {len(messages)} messages without embeddings")

            # Process in batches
            processed = 0
            for i in range(0, len(messages), self.batch_size):
                batch = messages[i : i + self.batch_size]
                embeddings = await self.embed_messages_batch(batch, db)
                processed += sum(1 for e in embeddings if e is not None)

            logger.info(f"Processed {processed} messages")
            return processed

        except Exception as e:
            logger.error(f"Failed to process unembedded messages: {e}")
            return 0

    def _extract_text_from_message(self, message: Message) -> str:
        """
        Extract text content from message for embedding.

        Args:
            message: Message object

        Returns:
            Text content
        """
        try:
            content = message.content

            # Try to get text content
            if isinstance(content, dict):
                text = content.get("text", "")

                # If no plain text, try HTML
                if not text:
                    text = content.get("html", "")

                return text.strip()

            # If content is a string, use it directly
            if isinstance(content, str):
                return content.strip()

            return ""

        except Exception as e:
            logger.error(f"Failed to extract text from message {message.id}: {e}")
            return ""

    async def _store_in_chromadb(
        self,
        message_id: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> bool:
        """
        Store embedding in ChromaDB.

        Args:
            message_id: Message ID
            text: Message text
            embedding: Embedding vector
            metadata: Message metadata

        Returns:
            True if successful
        """
        try:
            self.chroma_client.add_documents(
                documents=[text],
                ids=[message_id],
                embeddings=[embedding],
                metadatas=[metadata],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding in ChromaDB: {e}")
            return False

    async def _store_batch_in_chromadb(
        self,
        message_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> bool:
        """
        Store embeddings in ChromaDB in batch.

        Args:
            message_ids: List of message IDs
            texts: List of message texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts

        Returns:
            True if successful
        """
        try:
            self.chroma_client.add_documents(
                documents=texts,
                ids=message_ids,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store batch embeddings in ChromaDB: {e}")
            return False

    async def health_check(self) -> dict[str, bool]:
        """
        Check health of embedding service components.

        Returns:
            Dictionary with health status of each component
        """
        health = {
            "llm_provider": False,
            "chroma_client": False,
        }

        try:
            # Check LLM provider
            health["llm_provider"] = await self.llm_provider.health_check()
        except Exception as e:
            logger.error(f"LLM provider health check failed: {e}")

        try:
            # Check ChromaDB
            health["chroma_client"] = self.chroma_client.health_check()
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")

        return health


# Global service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.

    Returns:
        Embedding service
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service


__all__ = [
    "EmbeddingService",
    "get_embedding_service",
]
