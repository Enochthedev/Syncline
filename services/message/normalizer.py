"""
Message normalizer for converting platform-specific messages to unified schema.

This service handles the conversion of raw messages from different platforms
into the standardized NormalizedMessage format used throughout the MESH system.
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from .schema import (
    RawMessage, NormalizedMessage, MessageContent, Attachment, Participant, Thread,
    Platform, ContentType, AttachmentType
)
from .content_processor import ContentProcessor
from services.blob_storage import BlobStorageManager, get_default_storage_manager
from utils.mime_utils import clean_mime_type, resolve_mime_type, is_safe_mime_type

logger = logging.getLogger(__name__)


class MessageNormalizer:
    """
    Normalizes messages from different platforms into a unified format.

    This class handles the conversion of platform-specific message formats
    into the standardized NormalizedMessage schema.
    """

    def __init__(self, storage_manager: Optional[BlobStorageManager] = None):
        """Initialize the message normalizer."""
        self.storage_manager = storage_manager or get_default_storage_manager()
        self.content_processor = ContentProcessor()

    async def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """
        Normalize a raw message into the standard format.

        Args:
            raw_message: The raw message from a platform

        Returns:
            NormalizedMessage: Normalized message in standard format
        """
        try:
            # Generate unique ID for the message
            message_id = self._generate_message_id(raw_message)

            # Extract and normalize content
            content = await self._normalize_content(raw_message)

            # Process attachments
            attachments = await self._process_attachments(raw_message)

            # Extract participants
            participants = self._extract_participants(raw_message)

            # Extract thread information
            thread = self._extract_thread_info(raw_message)

            # Create normalized message
            normalized = NormalizedMessage(
                id=message_id,
                platform=raw_message.platform,
                platform_message_id=raw_message.platform_message_id,
                content=content,
                sender=participants.get('sender'),
                recipients=participants.get('recipients', []),
                timestamp=raw_message.timestamp or datetime.utcnow(),
                thread=thread,
                attachments=attachments,
                metadata=self._extract_metadata(raw_message),
                raw_data=raw_message.raw_data
            )

            logger.debug(
                f"Normalized message {message_id} from {raw_message.platform.value}")
            return normalized

        except Exception as e:
            logger.error(f"Failed to normalize message: {e}")
            raise

    async def _normalize_content(self, raw_message: RawMessage) -> MessageContent:
        """Extract and normalize message content."""
        content_data = raw_message.raw_data.get('content', {})

        # Determine content type and extract content
        if isinstance(content_data, str):
            # Simple text content
            return self.content_processor.standardize_content(
                content_data, ContentType.TEXT
            )
        elif isinstance(content_data, dict):
            # Structured content
            if 'html' in content_data:
                return self.content_processor.standardize_content(
                    content_data['html'], ContentType.HTML
                )
            elif 'markdown' in content_data:
                return self.content_processor.standardize_content(
                    content_data['markdown'], ContentType.MARKDOWN
                )
            elif 'text' in content_data:
                return self.content_processor.standardize_content(
                    content_data['text'], ContentType.TEXT
                )

        # Fallback to empty content
        return MessageContent()

    async def _process_attachments(self, raw_message: RawMessage) -> List[Attachment]:
        """Process and store message attachments."""
        attachments = []
        attachment_data = raw_message.raw_data.get('attachments', [])

        for attachment_info in attachment_data:
            try:
                attachment = await self._process_single_attachment(attachment_info)
                if attachment:
                    attachments.append(attachment)
            except Exception as e:
                logger.warning(f"Failed to process attachment: {e}")
                continue

        return attachments

    async def _process_single_attachment(self, attachment_info: Dict[str, Any]) -> Optional[Attachment]:
        """Process a single attachment."""
        # Extract attachment metadata
        filename = attachment_info.get('filename', 'unknown')
        mime_type = clean_mime_type(attachment_info.get('mime_type', ''))
        size = attachment_info.get('size', 0)

        # Validate attachment
        if not is_safe_mime_type(mime_type):
            logger.warning(f"Skipping unsafe attachment type: {mime_type}")
            return None

        # Determine attachment type
        attachment_type = self._determine_attachment_type(mime_type)

        # Store attachment data if present
        storage_path = None
        if 'data' in attachment_info:
            try:
                storage_path = await self.storage_manager.store_blob(
                    data=attachment_info['data'],
                    filename=filename,
                    mime_type=mime_type
                )
            except Exception as e:
                logger.error(f"Failed to store attachment {filename}: {e}")
                return None

        return Attachment(
            filename=filename,
            mime_type=mime_type,
            size=size,
            type=attachment_type,
            storage_path=storage_path,
            url=attachment_info.get('url'),
            metadata=attachment_info.get('metadata', {})
        )

    def _determine_attachment_type(self, mime_type: str) -> AttachmentType:
        """Determine attachment type from MIME type."""
        if mime_type.startswith('image/'):
            return AttachmentType.IMAGE
        elif mime_type.startswith('video/'):
            return AttachmentType.VIDEO
        elif mime_type.startswith('audio/'):
            return AttachmentType.AUDIO
        elif mime_type in ['application/pdf', 'text/plain', 'application/msword']:
            return AttachmentType.DOCUMENT
        else:
            return AttachmentType.OTHER

    def _extract_participants(self, raw_message: RawMessage) -> Dict[str, Any]:
        """Extract sender and recipients from raw message."""
        participants_data = raw_message.raw_data.get('participants', {})

        # Extract sender
        sender_data = participants_data.get('sender', {})
        sender = Participant(
            identifier=sender_data.get('id', ''),
            display_name=sender_data.get('name', ''),
            email=sender_data.get('email'),
            platform_specific_data=sender_data
        )

        # Extract recipients
        recipients = []
        for recipient_data in participants_data.get('recipients', []):
            recipient = Participant(
                identifier=recipient_data.get('id', ''),
                display_name=recipient_data.get('name', ''),
                email=recipient_data.get('email'),
                platform_specific_data=recipient_data
            )
            recipients.append(recipient)

        return {
            'sender': sender,
            'recipients': recipients
        }

    def _extract_thread_info(self, raw_message: RawMessage) -> Optional[Thread]:
        """Extract thread information from raw message."""
        thread_data = raw_message.raw_data.get('thread', {})

        if not thread_data:
            return None

        return Thread(
            id=thread_data.get('id', ''),
            subject=thread_data.get('subject', ''),
            participants=[],  # Will be populated separately
            message_count=thread_data.get('message_count', 1),
            platform_specific_data=thread_data
        )

    def _extract_metadata(self, raw_message: RawMessage) -> Dict[str, Any]:
        """Extract metadata from raw message."""
        metadata = raw_message.raw_data.get('metadata', {}).copy()

        # Add normalization metadata
        metadata.update({
            'normalized_at': datetime.utcnow().isoformat(),
            'platform': raw_message.platform.value,
            'original_format': raw_message.raw_data.get('format', 'unknown')
        })

        return metadata

    def _generate_message_id(self, raw_message: RawMessage) -> str:
        """Generate a unique ID for the message."""
        # Create a hash based on platform, platform message ID, and timestamp
        hash_input = f"{raw_message.platform.value}:{raw_message.platform_message_id}:{raw_message.timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    async def normalize_batch(self, raw_messages: List[RawMessage]) -> List[NormalizedMessage]:
        """Normalize a batch of raw messages."""
        normalized_messages = []

        for raw_message in raw_messages:
            try:
                normalized = await self.normalize_message(raw_message)
                normalized_messages.append(normalized)
            except Exception as e:
                logger.error(
                    f"Failed to normalize message {raw_message.platform_message_id}: {e}")
                continue

        logger.info(
            f"Normalized {len(normalized_messages)}/{len(raw_messages)} messages")
        return normalized_messages

    def get_stats(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        # This would be implemented with actual tracking
        return {
            'messages_processed': 0,
            'messages_failed': 0,
            'attachments_processed': 0,
            'storage_usage': 0
        }


# Global normalizer instance
_message_normalizer = None


async def get_message_normalizer() -> MessageNormalizer:
    """Get the global message normalizer instance."""
    global _message_normalizer
    if _message_normalizer is None:
        _message_normalizer = MessageNormalizer()
    return _message_normalizer
