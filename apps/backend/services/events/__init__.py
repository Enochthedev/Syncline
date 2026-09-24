"""
Event System Package

This package provides event-driven architecture components:
- Event type definitions
- Event bus for Redis Streams
- Event handlers and routing
- Consumer group management
- Dead letter queue for failed events
"""

from .consumer_groups import (
    ConsumerGroupManager,
    ConsumerInfo,
    get_consumer_group_manager,
)
from .dead_letter_queue import (
    DeadLetterQueue,
    FailedEvent,
    get_dead_letter_queue,
)
from .handlers import (
    BaseEventHandler,
    EventDispatcher,
    EventRouter,
    get_dispatcher,
)
from .types import (
    AIEvent,
    ConnectionEvent,
    ContactEvent,
    Event,
    EventType,
    MessageEvent,
    ThreadEvent,
)

__all__ = [
    # Event types
    "EventType",
    "Event",
    "ConnectionEvent",
    "MessageEvent",
    "ContactEvent",
    "ThreadEvent",
    "AIEvent",
    # Event handlers
    "BaseEventHandler",
    "EventRouter",
    "EventDispatcher",
    "get_dispatcher",
    # Consumer groups
    "ConsumerInfo",
    "ConsumerGroupManager",
    "get_consumer_group_manager",
    # Dead letter queue
    "FailedEvent",
    "DeadLetterQueue",
    "get_dead_letter_queue",
]
