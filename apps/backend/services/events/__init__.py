"""
Event System Package

This package provides event-driven architecture components:
- Event type definitions
- Event bus for Redis Streams
- Event handlers and routing
- Consumer group management
- Dead letter queue for failed events
"""

from .types import (
    EventType,
    Event,
    ConnectionEvent,
    MessageEvent,
    ContactEvent,
    ThreadEvent,
    AIEvent,
)
from .handlers import (
    BaseEventHandler,
    EventRouter,
    EventDispatcher,
    get_dispatcher,
)
from .consumer_groups import (
    ConsumerInfo,
    ConsumerGroupManager,
    get_consumer_group_manager,
)
from .dead_letter_queue import (
    FailedEvent,
    DeadLetterQueue,
    get_dead_letter_queue,
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
