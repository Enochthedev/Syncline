"""
Helper functions and utilities for vector database integration.

This module provides utility functions for processing different data types
and converting them to vector documents for storage.
"""

import logging
from datetime import datetime
from typing import Optional

from services.message.normalizer import NormalizedMessage
from db.models.message import Message
from db.models.summary import Summary
from db.models.entity import Entity

from .types import VectorDocument, VectorMetadata, VectorCollectionType

logger = logging.getLogger(__name__)


class VectorDocumentFactory:
    """Factory for creating vector documents from different data types."""

    @staticmethod
    async def create_from_message(
        message: Message,
        embedding: list,
        embedding_service
    ) -> Optional[VectorDocument]:
        """Create vector document from Message object."""
        try:
            # Extract text content
            text_content = message.content_text or message.content_markdown or ""

            if not text_content.strip():
                return None

            # Create metadata
            metadata = VectorMetadata(
                message_id=str(message.id),
                thread_id=str(message.thread_id),
                platform=message.platform,
                sender=str(message.sender_id),
                timestamp=message.timestamp,
                content_type="message",
                content_length=len(text_content)
            )

            # Create vector document
            return VectorDocument(
                id=f"message_{message.id}",
                text=text_content,
                embedding=embedding,
                metadata=metadata,
                collection=VectorCollectionType.MESSAGES
            )

        except Exception as e:
            logger.error(
                f"Failed to create vector document from message {message.id}: {e}")
            return None

    @staticmethod
    async def create_from_normalized_message(
        normalized_message: NormalizedMessage,
        embedding: list
    ) -> Optional[VectorDocument]:
        """Create vector document from NormalizedMessage object."""
        try:
            # Extract text content
            text_content = normalized_message.content.text or ""

            if not text_content.strip():
                return None

            # Create metadata
            metadata = VectorMetadata(
                message_id=normalized_message.id,
                thread_id=normalized_message.thread_id,
                platform=normalized_message.platform,
                sender=normalized_message.sender.email or normalized_message.sender.display_name,
                timestamp=normalized_message.timestamp,
                content_type="message",
                content_length=len(text_content)
            )

            # Create vector document
            return VectorDocument(
                id=f"message_{normalized_message.id}",
                text=text_content,
                embedding=embedding,
                metadata=metadata,
                collection=VectorCollectionType.MESSAGES
            )

        except Exception as e:
            logger.error(
                f"Failed to create vector document from normalized message: {e}")
            return None

    @staticmethod
    async def create_from_summary(
        summary: Summary,
        embedding: list
    ) -> Optional[VectorDocument]:
        """Create vector document from Summary object."""
        try:
            # Create metadata
            metadata = VectorMetadata(
                content_type="summary",
                summary_type=summary.type,
                summary_scope=summary.scope_type,
                timeframe_start=summary.timeframe_start,
                timeframe_end=summary.timeframe_end,
                content_length=len(summary.content)
            )

            # Add scope-specific metadata
            if summary.scope_id:
                if summary.scope_type == "thread":
                    metadata.thread_id = str(summary.scope_id)
                elif summary.scope_type == "contact":
                    metadata.sender = str(summary.scope_id)

            # Create vector document
            return VectorDocument(
                id=f"summary_{summary.id}",
                text=summary.content,
                embedding=embedding,
                metadata=metadata,
                collection=VectorCollectionType.SUMMARIES
            )

        except Exception as e:
            logger.error(
                f"Failed to create vector document from summary {summary.id}: {e}")
            return None

    @staticmethod
    async def create_from_entity(
        entity: Entity,
        embedding: list
    ) -> Optional[VectorDocument]:
        """Create vector document from Entity object."""
        try:
            # Create text representation of entity
            text_content = f"{entity.type}: {entity.value}"
            if entity.normalized_value and entity.normalized_value != entity.value:
                text_content += f" ({entity.normalized_value})"

            # Create metadata
            metadata = VectorMetadata(
                content_type="entity",
                entity_type=entity.type,
                entity_value=entity.value,
                confidence=entity.confidence,
                content_length=len(text_content)
            )

            # Create vector document
            return VectorDocument(
                id=f"entity_{entity.id}",
                text=text_content,
                embedding=embedding,
                metadata=metadata,
                collection=VectorCollectionType.ENTITIES
            )

        except Exception as e:
            logger.error(
                f"Failed to create vector document from entity {entity.id}: {e}")
            return None


class VectorIntegrationUtils:
    """Utility functions for vector integration operations."""

    @staticmethod
    def extract_text_content(message: Message) -> Optional[str]:
        """Extract text content from message."""
        text_content = message.content_text or message.content_markdown or ""
        return text_content.strip() if text_content else None

    @staticmethod
    def extract_normalized_text_content(normalized_message: NormalizedMessage) -> Optional[str]:
        """Extract text content from normalized message."""
        text_content = normalized_message.content.text or ""
        return text_content.strip() if text_content else None

    @staticmethod
    def create_entity_text_representation(entity: Entity) -> str:
        """Create text representation for entity embedding."""
        text_content = f"{entity.type}: {entity.value}"
        if entity.normalized_value and entity.normalized_value != entity.value:
            text_content += f" ({entity.normalized_value})"
        return text_content

    @staticmethod
    def calculate_processing_time(start_time: datetime) -> float:
        """Calculate processing time from start time."""
        return (datetime.utcnow() - start_time).total_seconds()

    @staticmethod
    def create_error_result(error_message: str, processing_time: float = 0.0):
        """Create error result for integration operations."""
        from .integration import VectorIntegrationResult
        return VectorIntegrationResult(
            success=False,
            error=error_message,
            processing_time=processing_time
        )

    @staticmethod
    def create_success_result(document_id: str, processing_time: float):
        """Create success result for integration operations."""
        from .integration import VectorIntegrationResult
        return VectorIntegrationResult(
            success=True,
            document_id=document_id,
            processing_time=processing_time
        )


class VectorIntegrationValidator:
    """Validation utilities for vector integration."""

    @staticmethod
    def validate_message(message: Message) -> bool:
        """Validate message for vector processing."""
        if not message:
            return False

        text_content = VectorIntegrationUtils.extract_text_content(message)
        return text_content is not None and len(text_content) > 0

    @staticmethod
    def validate_normalized_message(normalized_message: NormalizedMessage) -> bool:
        """Validate normalized message for vector processing."""
        if not normalized_message:
            return False

        text_content = VectorIntegrationUtils.extract_normalized_text_content(
            normalized_message)
        return text_content is not None and len(text_content) > 0

    @staticmethod
    def validate_summary(summary: Summary) -> bool:
        """Validate summary for vector processing."""
        if not summary or not summary.content:
            return False

        return len(summary.content.strip()) > 0

    @staticmethod
    def validate_entity(entity: Entity) -> bool:
        """Validate entity for vector processing."""
        if not entity or not entity.value:
            return False

        return len(entity.value.strip()) > 0

    @staticmethod
    def validate_embedding_result(embedding_result) -> bool:
        """Validate embedding result."""
        return (
            embedding_result and
            hasattr(embedding_result, 'embedding') and
            embedding_result.embedding and
            len(embedding_result.embedding) > 0
        )
