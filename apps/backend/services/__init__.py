"""
Services Package

This package contains business logic and orchestration services:
- Event bus for event-driven architecture
- Message processing services
- AI processing services
- Storage services
- Attachment handling
"""

from .attachment_handler import AttachmentHandler, get_default_attachment_handler
from .event_bus import EventBus, get_event_bus

__all__ = [
    "EventBus",
    "get_event_bus",
    "AttachmentHandler",
    "get_default_attachment_handler",
]
