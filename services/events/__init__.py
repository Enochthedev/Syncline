"""
Event-driven messaging infrastructure for the MESH system.

This package contains all event-related functionality including
the event bus, event types, and event processing patterns.
"""

from .event_bus import EventBus, get_event_bus
from .types import Event, EventType, EventPriority
from .patterns import EventProcessor, EventHandler

__all__ = [
    'EventBus',
    'get_event_bus',
    'Event',
    'EventType',
    'EventPriority',
    'EventProcessor',
    'EventHandler'
]
