"""
Message normalizer service.

This module provides the MessageNormalizer class that coordinates
message normalization across different platforms using specialized parsers.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Type
from uuid import UUID

from db.models.raw_message import RawMessage
from .schema import Platform, UnifiedMessage
from .content_processor import ContentProcessor
from .parsers import (
    BasePlatformParser,
    GmailParser,
    SlackParser,
    DiscordParser,
    WhatsAppParser,
    TwitterParser,
    TelegramParser,
)

logger = logging.getLogger(__name__)


class MessageNormalizationError(Exception):
    """Exception raised when message normalization fails."""
    pass


class MessageNormalizer:
    """
    Main service for normalizing messages from different platforms.
    
    Coordinates the normalization process using platform-specific parsers
    and manages content processing.
    """
    
    def __init__(self):
        """Initialize the message normalizer with platform parsers."""
        self.content_processor = ContentProcessor()
        
        # Register platform parsers
        self._parsers: Dict[Platform, BasePlatformParser] = {
            Platform.GMAIL: GmailParser(self.content_processor),
            Platform.SLACK: SlackParser(self.content_processor),
            Platform.DISCORD: DiscordParser(self.content_processor),
            Platform.WHATSAPP: WhatsAppParser(self.content_processor),
            Platform.TWITTER: TwitterParser(self.content_processor),
            Platform.TELEGRAM: TelegramParser(self.content_processor),
        }
        
        # Statistics
        self.stats = {
            'messages_normalized': 0,
            'normalization_errors': 0,
            'last_normalization': None,
        }
        
        logger.info(
            f"MessageNormalizer initialized with {len(self._parsers)} platform parsers"
        )
    
    def normalize_message(
        self,
        raw_message: RawMessage,
        connection_id: UUID
    ) -> UnifiedMessage:
        """
        Normalize a single raw message to the unified format.
        
        Args:
            raw_message: Raw message from database
            connection_id: Connection ID for the message
            
        Returns:
            Normalized unified message
            
        Raises:
            MessageNormalizationError: If normalization fails
        """
        try:
            # Get platform parser
            platform = Platform(raw_message.platform)
            parser = self._parsers.get(platform)
            
            if not parser:
                raise MessageNormalizationError(
                    f"No parser available for platform: {platform}"
                )
            
            # Parse the message
            unified_message = parser.parse(
                raw_data=raw_message.raw_data,
                platform_message_id=raw_message.platform_message_id,
                collected_at=raw_message.created_at
            )
            
            # Update statistics
            self.stats['messages_normalized'] += 1
            self.stats['last_normalization'] = datetime.utcnow()
            
            logger.debug(
                f"Successfully normalized message {raw_message.id} "
                f"from {platform.value}"
            )
            
            return unified_message
        
        except Exception as e:
            self.stats['normalization_errors'] += 1
            logger.error(
                f"Failed to normalize message {raw_message.id}: {e}",
                exc_info=True
            )
            raise MessageNormalizationError(
                f"Normalization failed for message {raw_message.id}: {e}"
            ) from e
    
    def get_supported_platforms(self) -> list[Platform]:
        """Get list of supported platforms."""
        return list(self._parsers.keys())
    
    def get_stats(self) -> Dict:
        """Get normalization statistics."""
        total_messages = (
            self.stats['messages_normalized'] +
            self.stats['normalization_errors']
        )
        
        return {
            **self.stats,
            'success_rate': (
                self.stats['messages_normalized'] / max(total_messages, 1)
            ),
            'supported_platforms': [p.value for p in self.get_supported_platforms()],
        }


# Global normalizer instance
_message_normalizer: Optional[MessageNormalizer] = None


def get_message_normalizer() -> MessageNormalizer:
    """Get the global message normalizer instance."""
    global _message_normalizer
    
    if _message_normalizer is None:
        _message_normalizer = MessageNormalizer()
    
    return _message_normalizer
