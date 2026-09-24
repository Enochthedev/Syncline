"""
Message processing services.

This package provides message normalization, content processing,
and schema validation for messages from different platforms.
"""

from .content_processor import ContentProcessor
from .normalizer import MessageNormalizer, get_message_normalizer
from .schema import (
    ContentFormat,
    MessageAttachment,
    MessageContent,
    MessageRecipient,
    MessageSender,
    Platform,
    UnifiedMessage,
)

__all__ = [
    # Schema
    "Platform",
    "ContentFormat",
    "MessageContent",
    "MessageSender",
    "MessageRecipient",
    "MessageAttachment",
    "UnifiedMessage",
    # Content Processor
    "ContentProcessor",
    # Normalizer
    "MessageNormalizer",
    "get_message_normalizer",
]
