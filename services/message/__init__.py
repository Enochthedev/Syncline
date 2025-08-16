"""
Message processing services.

This package contains all message-related functionality including
normalization, content processing, and schema definitions.
"""

from .normalizer import MessageNormalizer, get_message_normalizer
from .content_processor import ContentProcessor
from .schema import (
    RawMessage, NormalizedMessage, MessageContent, Attachment,
    Participant, Thread, Platform, ContentType, AttachmentType
)

__all__ = [
    'MessageNormalizer',
    'get_message_normalizer',
    'ContentProcessor',
    'RawMessage',
    'NormalizedMessage',
    'MessageContent',
    'Attachment',
    'Participant',
    'Thread',
    'Platform',
    'ContentType',
    'AttachmentType'
]
