"""
Event type definitions for the MESH system.

This module contains all event types, priorities, and data structures
used throughout the event-driven architecture.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class EventType(str, Enum):
    """Event types for the MESH system."""
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_NORMALIZED = "message.normalized"
    MESSAGE_PROCESSED = "message.processed"
    THREAD_UPDATED = "thread.updated"
    PARTICIPANT_UPDATED = "participant.updated"
    ENTITY_EXTRACTED = "entity.extracted"
    SUMMARY_GENERATED = "summary.generated"
    ERROR_OCCURRED = "error.occurred"
    HEALTH_CHECK = "health.check"


class EventPriority(str, Enum):
    """Event priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Event:
    """Event data structure for the event bus."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.MESSAGE_RECEIVED
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'data': self.data,
            'priority': self.priority.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=EventType(data.get('type', EventType.MESSAGE_RECEIVED)),
            data=data.get('data', {}),
            priority=EventPriority(data.get('priority', EventPriority.NORMAL)),
            source=data.get('source', 'unknown'),
            timestamp=datetime.fromisoformat(
                data.get('timestamp', datetime.utcnow().isoformat())),
            correlation_id=data.get('correlation_id', ''),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            metadata=data.get('metadata', {})
        )
