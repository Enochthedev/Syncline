"""
Batch operation implementations for vector database processing.

This module provides the core batch processing logic for messages,
summaries, and entities in the vector database system.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from services.ai.embeddings import get_embedding_service
from db.models.message import Message
from db.models.summary import Summary
from db.models.entity import Entity
from db.session import get_async_session

from .types import VectorDocument, VectorMetadata, VectorCollectionType, VectorBatchResult
from .batch_config import BatchProcessingConfig, BatchProcessingResult

logger = logging.getLogger(__name__)


class BatchOperationHandler:
    """Handles batch operations for different data types."""

    def __init__(self, config: BatchProcessingConfig, embedding_service, vector_db):
        """Initialize batch operation handler."""
        self.config = config
        self.embedding_service = embedding_service
        self.vector_db = vector_db

    async def process_message_batch(self, messages: List[Message]) -> VectorBatchResult:
        """Process a batch of messages for embedding and storage."""
        try:
            # Extract text content from messages
            texts = []
            message_data = []

            for message in messages:
                # Use content_text or content_markdown as primary text
                text_content = message.content_text or message.content_markdown or ""

                if text_content.strip():
                    texts.append(text_content)
                    message_data.append(message)

            if not texts:
                return VectorBatchResult(
                    operation_type='add',
                    collection=VectorCollectionType.MESSAGES,
                    processed_count=len(messages),
                    success_count=0,
                    error_count=len(messages)
                )

            # Generate embeddings in batch
            embedding_results = await self.embedding_service.generate_embeddings_batch(
                texts=texts,
                batch_size=self.config.embedding_batch_size,
                use_cache=True
            )

            # Create vector documents
            vector_documents = []

            for i, (message, embedding_result) in enumerate(zip(message_data, embedding_results)):
                if hasattr(embedding_result, 'embedding') and embedding_result.embedding:
                    # Create metadata
                    metadata = VectorMetadata(
                        message_id=str(message.id),
                        thread_id=str(message.thread_id),
                        platform=message.platform,
                        sender=str(message.sender_id),
                        timestamp=message.timestamp,
                        content_type="message",
                        content_length=len(embedding_result.text)
                    )

                    vector_doc = VectorDocument(
                        id=f"message_{message.id}",
                        text=embedding_result.text,
                        embedding=embedding_result.embedding,
                        metadata=metadata,
                        collection=VectorCollectionType.MESSAGES
                    )

                    vector_documents.append(vector_doc)

            # Store in vector database
            if vector_documents:
                return await self.vector_db.store_documents_batch(vector_documents)
            else:
                return VectorBatchResult(
                    operation_type='add',
                    collection=VectorCollectionType.MESSAGES,
                    processed_count=len(messages),
                    success_count=0,
                    error_count=len(messages),
                    errors=["No valid embeddings generated"]
                )

        except Exception as e:
            logger.error(f"Message batch processing failed: {e}")
            return VectorBatchResult(
                operation_type='add',
                collection=VectorCollectionType.MESSAGES,
                processed_count=len(messages),
                success_count=0,
                error_count=len(messages),
                errors=[str(e)]
            )

    async def process_summaries_to_vectors(self, summaries: List[Summary]) -> List[VectorDocument]:
        """Convert summaries to vector documents."""
        vector_documents = []

        for summary in summaries:
            try:
                # Generate embedding for summary content
                embedding_result = await self.embedding_service.generate_embedding(
                    text=summary.content,
                    use_cache=True
                )

                # Create metadata
                metadata = VectorMetadata(
                    content_type="summary",
                    summary_type=summary.type,
                    summary_scope=summary.scope_type,
                    timeframe_start=summary.timeframe_start,
                    timeframe_end=summary.timeframe_end,
                    content_length=len(summary.content)
                )

                vector_doc = VectorDocument(
                    id=f"summary_{summary.id}",
                    text=summary.content,
                    embedding=embedding_result.embedding,
                    metadata=metadata,
                    collection=VectorCollectionType.SUMMARIES
                )

                vector_documents.append(vector_doc)

            except Exception as e:
                logger.error(f"Failed to process summary {summary.id}: {e}")

        return vector_documents

    async def process_entities_to_vectors(self, entities: List[Entity]) -> List[VectorDocument]:
        """Convert entities to vector documents."""
        vector_documents = []

        for entity in entities:
            try:
                # Create text representation of entity
                text_content = f"{entity.type}: {entity.value}"
                if entity.normalized_value and entity.normalized_value != entity.value:
                    text_content += f" ({entity.normalized_value})"

                # Generate embedding
                embedding_result = await self.embedding_service.generate_embedding(
                    text=text_content,
                    use_cache=True
                )

                # Create metadata
                metadata = VectorMetadata(
                    content_type="entity",
                    entity_type=entity.type,
                    entity_value=entity.value,
                    confidence=entity.confidence,
                    content_length=len(text_content)
                )

                vector_doc = VectorDocument(
                    id=f"entity_{entity.id}",
                    text=text_content,
                    embedding=embedding_result.embedding,
                    metadata=metadata,
                    collection=VectorCollectionType.ENTITIES
                )

                vector_documents.append(vector_doc)

            except Exception as e:
                logger.error(f"Failed to process entity {entity.id}: {e}")

        return vector_documents


class BatchDataFetcher:
    """Handles data fetching for batch processing."""

    def __init__(self, config: BatchProcessingConfig):
        """Initialize data fetcher with configuration."""
        self.config = config

    async def fetch_messages_batch(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """Fetch messages from database for processing."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                query = select(Message).offset(offset)

                # Apply filters from config
                if self.config.start_date:
                    query = query.where(Message.timestamp >=
                                        self.config.start_date)

                if self.config.end_date:
                    query = query.where(Message.timestamp <=
                                        self.config.end_date)

                if self.config.platforms:
                    query = query.where(
                        Message.platform.in_(self.config.platforms))

                if limit:
                    query = query.limit(limit)

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            return []

    async def fetch_summaries_batch(
        self,
        summary_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Summary]:
        """Fetch summaries from database for processing."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                query = select(Summary)

                if summary_type:
                    query = query.where(Summary.type == summary_type)

                if limit:
                    query = query.limit(limit)

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to fetch summaries: {e}")
            return []

    async def fetch_entities_batch(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Fetch entities from database for processing."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                query = select(Entity)

                if entity_type:
                    query = query.where(Entity.type == entity_type)

                if limit:
                    query = query.limit(limit)

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to fetch entities: {e}")
            return []
