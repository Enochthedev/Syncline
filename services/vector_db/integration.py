"""
Integration service for vector database with AI processing pipeline.

This module provides seamless integration between the vector database
and existing AI services for automatic embedding generation and storage.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass

from services.ai.embeddings import get_embedding_service
from services.message.normalizer import NormalizedMessage
from db.models.message import Message
from db.models.summary import Summary
from db.models.entity import Entity

from .chroma_client import get_vector_db
from .integration_helpers import (
    VectorDocumentFactory, VectorIntegrationUtils, VectorIntegrationValidator
)

logger = logging.getLogger(__name__)


@dataclass
class VectorIntegrationResult:
    """Result from vector integration operation."""
    success: bool
    document_id: Optional[str] = None
    error: Optional[str] = None
    processing_time: float = 0.0


class VectorIntegrationService:
    """
    Service for integrating vector database operations with AI processing.

    Automatically handles embedding generation and storage for messages,
    summaries, and entities as they are processed by the AI pipeline.
    """

    def __init__(self):
        """Initialize the integration service."""
        self.embedding_service = None
        self.vector_db = None

        # Statistics
        self.stats = {
            'messages_processed': 0,
            'summaries_processed': 0,
            'entities_processed': 0,
            'total_processing_time': 0.0,
            'errors': 0,
            'last_operation': None
        }

        logger.info("VectorIntegrationService initialized")

    async def initialize(self) -> None:
        """Initialize required services."""
        try:
            self.embedding_service = await get_embedding_service()
            self.vector_db = await get_vector_db()
            logger.info("VectorIntegrationService services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize VectorIntegrationService: {e}")
            raise

    async def process_message_for_vector_storage(
        self,
        message: Message,
        force_regenerate: bool = False
    ) -> VectorIntegrationResult:
        """Process a message for vector storage."""
        start_time = datetime.utcnow()

        try:
            # Validate message
            if not VectorIntegrationValidator.validate_message(message):
                return VectorIntegrationUtils.create_error_result("No text content available for embedding")

            # Extract text content
            text_content = VectorIntegrationUtils.extract_text_content(message)

            # Generate embedding
            embedding_result = await self.embedding_service.generate_embedding(
                text=text_content,
                use_cache=not force_regenerate
            )

            # Validate embedding result
            if not VectorIntegrationValidator.validate_embedding_result(embedding_result):
                return VectorIntegrationUtils.create_error_result("Failed to generate valid embedding")

            # Create vector document
            vector_doc = await VectorDocumentFactory.create_from_message(
                message, embedding_result.embedding, self.embedding_service
            )

            if not vector_doc:
                return VectorIntegrationUtils.create_error_result("Failed to create vector document")

            # Store in vector database
            success = await self.vector_db.store_document(vector_doc)
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)

            if success:
                self._update_stats('message', processing_time)
                return VectorIntegrationUtils.create_success_result(vector_doc.id, processing_time)
            else:
                self.stats['errors'] += 1
                return VectorIntegrationUtils.create_error_result(
                    "Failed to store document in vector database", processing_time
                )

        except Exception as e:
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)
            self.stats['errors'] += 1
            logger.error(
                f"Failed to process message {message.id} for vector storage: {e}")
            return VectorIntegrationUtils.create_error_result(str(e), processing_time)

    async def process_normalized_message_for_vector_storage(
        self,
        normalized_message: NormalizedMessage
    ) -> VectorIntegrationResult:
        """Process a normalized message for vector storage."""
        start_time = datetime.utcnow()

        try:
            # Validate normalized message
            if not VectorIntegrationValidator.validate_normalized_message(normalized_message):
                return VectorIntegrationUtils.create_error_result("No text content available for embedding")

            # Extract text content
            text_content = VectorIntegrationUtils.extract_normalized_text_content(
                normalized_message)

            # Generate embedding
            embedding_result = await self.embedding_service.generate_embedding(
                text=text_content,
                use_cache=True
            )

            # Validate embedding result
            if not VectorIntegrationValidator.validate_embedding_result(embedding_result):
                return VectorIntegrationUtils.create_error_result("Failed to generate valid embedding")

            # Create vector document
            vector_doc = await VectorDocumentFactory.create_from_normalized_message(
                normalized_message, embedding_result.embedding
            )

            if not vector_doc:
                return VectorIntegrationUtils.create_error_result("Failed to create vector document")

            # Store in vector database
            success = await self.vector_db.store_document(vector_doc)
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)

            if success:
                self._update_stats('message', processing_time)
                return VectorIntegrationUtils.create_success_result(vector_doc.id, processing_time)
            else:
                self.stats['errors'] += 1
                return VectorIntegrationUtils.create_error_result(
                    "Failed to store document in vector database", processing_time
                )

        except Exception as e:
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)
            self.stats['errors'] += 1
            logger.error(
                f"Failed to process normalized message for vector storage: {e}")
            return VectorIntegrationUtils.create_error_result(str(e), processing_time)

    async def process_summary_for_vector_storage(
        self,
        summary: Summary
    ) -> VectorIntegrationResult:
        """Process a summary for vector storage."""
        start_time = datetime.utcnow()

        try:
            # Validate summary
            if not VectorIntegrationValidator.validate_summary(summary):
                return VectorIntegrationUtils.create_error_result("Invalid summary content")

            # Generate embedding for summary content
            embedding_result = await self.embedding_service.generate_embedding(
                text=summary.content,
                use_cache=True
            )

            # Validate embedding result
            if not VectorIntegrationValidator.validate_embedding_result(embedding_result):
                return VectorIntegrationUtils.create_error_result("Failed to generate valid embedding")

            # Create vector document
            vector_doc = await VectorDocumentFactory.create_from_summary(
                summary, embedding_result.embedding
            )

            if not vector_doc:
                return VectorIntegrationUtils.create_error_result("Failed to create vector document")

            # Store in vector database
            success = await self.vector_db.store_document(vector_doc)
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)

            if success:
                self._update_stats('summary', processing_time)
                return VectorIntegrationUtils.create_success_result(vector_doc.id, processing_time)
            else:
                self.stats['errors'] += 1
                return VectorIntegrationUtils.create_error_result(
                    "Failed to store summary in vector database", processing_time
                )

        except Exception as e:
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)
            self.stats['errors'] += 1
            logger.error(
                f"Failed to process summary {summary.id} for vector storage: {e}")
            return VectorIntegrationUtils.create_error_result(str(e), processing_time)

    async def process_entity_for_vector_storage(
        self,
        entity: Entity
    ) -> VectorIntegrationResult:
        """Process an entity for vector storage."""
        start_time = datetime.utcnow()

        try:
            # Validate entity
            if not VectorIntegrationValidator.validate_entity(entity):
                return VectorIntegrationUtils.create_error_result("Invalid entity data")

            # Create text representation of entity
            text_content = VectorIntegrationUtils.create_entity_text_representation(
                entity)

            # Generate embedding
            embedding_result = await self.embedding_service.generate_embedding(
                text=text_content,
                use_cache=True
            )

            # Validate embedding result
            if not VectorIntegrationValidator.validate_embedding_result(embedding_result):
                return VectorIntegrationUtils.create_error_result("Failed to generate valid embedding")

            # Create vector document
            vector_doc = await VectorDocumentFactory.create_from_entity(
                entity, embedding_result.embedding
            )

            if not vector_doc:
                return VectorIntegrationUtils.create_error_result("Failed to create vector document")

            # Store in vector database
            success = await self.vector_db.store_document(vector_doc)
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)

            if success:
                self._update_stats('entity', processing_time)
                return VectorIntegrationUtils.create_success_result(vector_doc.id, processing_time)
            else:
                self.stats['errors'] += 1
                return VectorIntegrationUtils.create_error_result(
                    "Failed to store entity in vector database", processing_time
                )

        except Exception as e:
            processing_time = VectorIntegrationUtils.calculate_processing_time(
                start_time)
            self.stats['errors'] += 1
            logger.error(
                f"Failed to process entity {entity.id} for vector storage: {e}")
            return VectorIntegrationUtils.create_error_result(str(e), processing_time)

    async def remove_message_from_vector_storage(self, message_id: str) -> bool:
        """Remove a message from vector storage."""
        try:
            from .types import VectorCollectionType
            document_id = f"message_{message_id}"
            success = await self.vector_db.delete_document(
                document_id,
                VectorCollectionType.MESSAGES
            )

            if success:
                logger.debug(
                    f"Removed message {message_id} from vector storage")
            else:
                logger.warning(
                    f"Failed to remove message {message_id} from vector storage")

            return success

        except Exception as e:
            logger.error(
                f"Error removing message {message_id} from vector storage: {e}")
            return False

    async def update_message_in_vector_storage(
        self,
        message: Message,
        force_regenerate: bool = True
    ) -> VectorIntegrationResult:
        """Update a message in vector storage."""
        try:
            # Remove existing document
            await self.remove_message_from_vector_storage(str(message.id))

            # Add updated document
            return await self.process_message_for_vector_storage(message, force_regenerate)

        except Exception as e:
            logger.error(
                f"Failed to update message {message.id} in vector storage: {e}")
            return VectorIntegrationResult(
                success=False,
                error=str(e)
            )

    def _update_stats(self, operation_type: str, processing_time: float) -> None:
        """Update processing statistics."""
        if operation_type == 'message':
            self.stats['messages_processed'] += 1
        elif operation_type == 'summary':
            self.stats['summaries_processed'] += 1
        elif operation_type == 'entity':
            self.stats['entities_processed'] += 1

        self.stats['total_processing_time'] += processing_time
        self.stats['last_operation'] = datetime.utcnow()

    async def get_stats(self) -> Dict[str, Any]:
        """Get integration service statistics."""
        total_processed = (
            self.stats['messages_processed'] +
            self.stats['summaries_processed'] +
            self.stats['entities_processed']
        )

        return {
            **self.stats,
            'total_processed': total_processed,
            'average_processing_time': (
                self.stats['total_processing_time'] / max(total_processed, 1)
            ),
            'error_rate': (
                self.stats['errors'] / max(total_processed, 1)
            ) if total_processed > 0 else 0.0
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the integration service."""
        try:
            # Check if services are initialized
            if not self.embedding_service or not self.vector_db:
                return {
                    'status': 'unhealthy',
                    'error': 'Services not initialized'
                }

            # Test embedding generation
            embedding_health = await self.embedding_service.health_check()

            # Test vector database
            vector_db_health = await self.vector_db.health_check()

            # Overall health
            overall_healthy = (
                embedding_health.get('status') == 'healthy' and
                vector_db_health.get('status') == 'healthy'
            )

            return {
                'status': 'healthy' if overall_healthy else 'unhealthy',
                'embedding_service': embedding_health,
                'vector_database': vector_db_health,
                'stats': await self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global integration service instance
_integration_service = None


async def get_vector_integration_service() -> VectorIntegrationService:
    """Get the global vector integration service instance."""
    global _integration_service

    if _integration_service is None:
        _integration_service = VectorIntegrationService()
        await _integration_service.initialize()

    return _integration_service
