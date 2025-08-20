"""
Main message normalizer service.

This module provides the primary MessageNormalizer class that coordinates
message normalization across different platforms using specialized handlers.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import asyncio

from services.message_schema import RawMessage, NormalizedMessage, Platform
from services.blob_storage import BlobStorageManager, get_default_storage_manager
from .platform_handlers import get_platform_registry, PlatformHandlerRegistry
from .content_processor import ContentProcessor

logger = logging.getLogger(__name__)


class MessageNormalizationError(Exception):
    """Exception raised when message normalization fails."""
    pass


class MessageNormalizer:
    """
    Main service for normalizing messages from different platforms.

    Coordinates the normalization process using platform-specific handlers
    and manages content processing, attachment handling, and deduplication.
    """

    def __init__(
        self,
        storage_manager: Optional[BlobStorageManager] = None,
        platform_registry: Optional[PlatformHandlerRegistry] = None
    ):
        """
        Initialize the message normalizer.

        Args:
            storage_manager: Storage manager for handling attachments
            platform_registry: Registry of platform-specific handlers
        """
        self.storage_manager = storage_manager or get_default_storage_manager()
        self.platform_registry = platform_registry or get_platform_registry()

        # Statistics
        self.stats = {
            'messages_normalized': 0,
            'normalization_errors': 0,
            'attachments_processed': 0,
            'duplicate_messages_detected': 0,
            'processing_time_total': 0.0,
            'last_normalization': None
        }

        # Deduplication cache (in production, this should be persistent)
        self._message_hashes: Set[str] = set()

        logger.info("MessageNormalizer initialized")

    async def normalize_message(self, raw_message: RawMessage) -> Optional[NormalizedMessage]:
        """
        Normalize a single raw message to the unified format.

        Args:
            raw_message: Raw message from a platform

        Returns:
            Normalized message or None if normalization fails
        """
        start_time = datetime.utcnow()

        try:
            # Validate input
            if not self._validate_raw_message(raw_message):
                logger.warning(f"Invalid raw message: {raw_message.id}")
                return None

            # Check for duplicates
            if await self._is_duplicate_message(raw_message):
                logger.debug(f"Duplicate message detected: {raw_message.id}")
                self.stats['duplicate_messages_detected'] += 1
                return None

            # Get platform handler
            handler = self.platform_registry.get_handler(raw_message.platform)
            if not handler:
                raise MessageNormalizationError(
                    f"No handler available for platform: {raw_message.platform}"
                )

            # Normalize the message
            normalized_message = handler.normalize_message(raw_message)

            # Process attachments if present
            if normalized_message.attachments:
                await self._process_attachments(normalized_message)
                self.stats['attachments_processed'] += len(
                    normalized_message.attachments)

            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(processing_time, success=True)

            # Add to deduplication cache
            content_hash = normalized_message.content.content_hash
            if content_hash:
                self._message_hashes.add(content_hash)

            logger.debug(
                f"Successfully normalized message {raw_message.id} in {processing_time:.3f}s")
            return normalized_message

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(processing_time, success=False)

            logger.error(f"Failed to normalize message {raw_message.id}: {e}")
            raise MessageNormalizationError(
                f"Normalization failed: {e}") from e

    async def normalize_messages_batch(
        self,
        raw_messages: List[RawMessage],
        max_concurrent: int = 10
    ) -> List[NormalizedMessage]:
        """
        Normalize multiple messages concurrently.

        Args:
            raw_messages: List of raw messages to normalize
            max_concurrent: Maximum number of concurrent normalizations

        Returns:
            List of successfully normalized messages
        """
        if not raw_messages:
            return []

        logger.info(
            f"Starting batch normalization of {len(raw_messages)} messages")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def normalize_with_semaphore(raw_message: RawMessage) -> Optional[NormalizedMessage]:
            async with semaphore:
                try:
                    return await self.normalize_message(raw_message)
                except Exception as e:
                    logger.error(
                        f"Batch normalization failed for message {raw_message.id}: {e}")
                    return None

        # Process messages concurrently
        tasks = [normalize_with_semaphore(msg) for msg in raw_messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        normalized_messages = []
        for result in results:
            if isinstance(result, NormalizedMessage):
                normalized_messages.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Batch normalization exception: {result}")

        logger.info(
            f"Batch normalization completed: {len(normalized_messages)}/{len(raw_messages)} successful")
        return normalized_messages

    def _validate_raw_message(self, raw_message: RawMessage) -> bool:
        """Validate that a raw message has required fields."""
        if not raw_message.id:
            return False

        if not raw_message.platform:
            return False

        if not raw_message.platform_data:
            return False

        return True

    async def _is_duplicate_message(self, raw_message: RawMessage) -> bool:
        """Check if a message is a duplicate based on content hash."""
        try:
            # Extract content for hashing
            content_data = raw_message.platform_data.get('content', {})
            text_content = content_data.get('text', '')

            if not text_content:
                return False  # Can't determine duplicates without content

            # Calculate content hash
            content_hash = ContentProcessor.calculate_content_hash(
                text_content)

            # Check if we've seen this hash before
            return content_hash in self._message_hashes

        except Exception as e:
            logger.warning(
                f"Duplicate detection failed for message {raw_message.id}: {e}")
            return False

    async def _process_attachments(self, normalized_message: NormalizedMessage) -> None:
        """Process and store attachments for a normalized message."""
        if not normalized_message.attachments:
            return

        for attachment in normalized_message.attachments:
            try:
                # Download and store attachment if it has a URL
                if attachment.url and not attachment.local_path:
                    local_path = await self.storage_manager.store_from_url(
                        attachment.url,
                        f"{normalized_message.platform.value}/{normalized_message.id}/{attachment.filename}"
                    )
                    attachment.local_path = local_path
                    logger.debug(
                        f"Stored attachment {attachment.filename} at {local_path}")

            except Exception as e:
                logger.warning(
                    f"Failed to process attachment {attachment.filename}: {e}")
                continue

    def _update_stats(self, processing_time: float, success: bool) -> None:
        """Update normalization statistics."""
        if success:
            self.stats['messages_normalized'] += 1
        else:
            self.stats['normalization_errors'] += 1

        self.stats['processing_time_total'] += processing_time
        self.stats['last_normalization'] = datetime.utcnow()

    def get_stats(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        total_messages = self.stats['messages_normalized'] + \
            self.stats['normalization_errors']

        return {
            **self.stats,
            'success_rate': (
                self.stats['messages_normalized'] / max(total_messages, 1)
            ),
            'average_processing_time': (
                self.stats['processing_time_total'] /
                max(self.stats['messages_normalized'], 1)
            ),
            'supported_platforms': [p.value for p in self.platform_registry.get_supported_platforms()]
        }

    def clear_deduplication_cache(self) -> None:
        """Clear the deduplication cache."""
        self._message_hashes.clear()
        logger.info("Deduplication cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the normalizer."""
        try:
            # Check if platform handlers are available
            supported_platforms = self.platform_registry.get_supported_platforms()

            # Check storage manager
            storage_healthy = await self.storage_manager.health_check() if hasattr(self.storage_manager, 'health_check') else True

            return {
                'status': 'healthy' if storage_healthy else 'degraded',
                'supported_platforms': [p.value for p in supported_platforms],
                'platform_count': len(supported_platforms),
                'storage_healthy': storage_healthy,
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global normalizer instance
_message_normalizer = None


def get_message_normalizer() -> MessageNormalizer:
    """Get the global message normalizer instance."""
    global _message_normalizer

    if _message_normalizer is None:
        _message_normalizer = MessageNormalizer()

    return _message_normalizer
