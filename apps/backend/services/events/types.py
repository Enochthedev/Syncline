"""
Event Type Definitions

This module defines all event types used in the event-driven architecture.
Events are published to Redis Streams and consumed by various handlers.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """
    Enumeration of all event types in the system.
    
    Events are organized by stage:
    - CONNECTION: Platform connection lifecycle
    - COLLECTION: Message collection from platforms
    - CLEANING: Message normalization
    - MATCHING: Contact and thread matching
    - AI: AI processing and analysis
    """
    
    # Connection Stage Events
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_FAILED = "connection.failed"
    CONNECTION_REFRESHED = "connection.refreshed"
    CONNECTION_REVOKED = "connection.revoked"
    
    # Collection Stage Events
    MESSAGE_COLLECTED = "collection.message_collected"
    COLLECTION_STARTED = "collection.started"
    COLLECTION_COMPLETED = "collection.completed"
    COLLECTION_ERROR = "collection.error"
    
    # Cleaning Stage Events
    MESSAGE_NORMALIZED = "cleaning.message_normalized"
    NORMALIZATION_FAILED = "cleaning.normalization_failed"
    ATTACHMENT_DOWNLOADED = "cleaning.attachment_downloaded"
    
    # Matching Stage Events
    CONTACT_MATCHED = "matching.contact_matched"
    CONTACT_CREATED = "matching.contact_created"
    CONTACT_MERGED = "matching.contact_merged"
    THREAD_CREATED = "matching.thread_created"
    THREAD_UPDATED = "matching.thread_updated"
    
    # AI Stage Events
    EMBEDDING_GENERATED = "ai.embedding_generated"
    ENTITIES_EXTRACTED = "ai.entities_extracted"
    SUMMARY_GENERATED = "ai.summary_generated"
    AI_PROCESSING_FAILED = "ai.processing_failed"
    
    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_CHECK = "system.health_check"


class Event(BaseModel):
    """
    Base event model for all events in the system.
    
    All events share these common fields and can include
    additional stage-specific data in the payload.
    """
    
    event_id: str = Field(description="Unique event identifier")
    event_type: EventType = Field(description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    source: str = Field(description="Source service/component that generated the event")
    correlation_id: str | None = Field(default=None, description="Correlation ID for tracing")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ConnectionEvent(Event):
    """
    Event for platform connection lifecycle.
    
    Payload fields:
    - connection_id: UUID of the platform connection
    - platform: Platform name (gmail, slack, etc.)
    - user_id: UUID of the user
    - status: Connection status
    - error: Error message (if failed)
    """
    
    event_type: EventType = Field(
        default=EventType.CONNECTION_ESTABLISHED,
        description="Connection event type"
    )
    
    @property
    def connection_id(self) -> UUID | None:
        """Get connection ID from payload."""
        conn_id = self.payload.get("connection_id")
        return UUID(conn_id) if conn_id else None
    
    @property
    def platform(self) -> str | None:
        """Get platform from payload."""
        return self.payload.get("platform")
    
    @property
    def user_id(self) -> UUID | None:
        """Get user ID from payload."""
        user_id = self.payload.get("user_id")
        return UUID(user_id) if user_id else None


class MessageEvent(Event):
    """
    Event for message collection and processing.
    
    Payload fields:
    - message_id: UUID of the message
    - raw_message_id: UUID of the raw message (if applicable)
    - connection_id: UUID of the platform connection
    - platform: Platform name
    - platform_message_id: Platform-specific message ID
    - thread_id: Thread identifier
    - error: Error message (if failed)
    """
    
    event_type: EventType = Field(
        default=EventType.MESSAGE_COLLECTED,
        description="Message event type"
    )
    
    @property
    def message_id(self) -> UUID | None:
        """Get message ID from payload."""
        msg_id = self.payload.get("message_id")
        return UUID(msg_id) if msg_id else None
    
    @property
    def connection_id(self) -> UUID | None:
        """Get connection ID from payload."""
        conn_id = self.payload.get("connection_id")
        return UUID(conn_id) if conn_id else None
    
    @property
    def platform(self) -> str | None:
        """Get platform from payload."""
        return self.payload.get("platform")


class ContactEvent(Event):
    """
    Event for contact matching and management.
    
    Payload fields:
    - contact_id: UUID of the contact
    - merged_contact_ids: List of merged contact UUIDs (if merged)
    - platform_identities: Dict of platform identities
    - confidence_score: Matching confidence score
    """
    
    event_type: EventType = Field(
        default=EventType.CONTACT_MATCHED,
        description="Contact event type"
    )
    
    @property
    def contact_id(self) -> UUID | None:
        """Get contact ID from payload."""
        contact_id = self.payload.get("contact_id")
        return UUID(contact_id) if contact_id else None


class ThreadEvent(Event):
    """
    Event for thread creation and updates.
    
    Payload fields:
    - thread_id: UUID of the thread
    - platform: Platform name
    - platform_thread_id: Platform-specific thread ID
    - contact_id: UUID of the primary contact
    - participant_ids: List of participant UUIDs
    - message_count: Number of messages in thread
    """
    
    event_type: EventType = Field(
        default=EventType.THREAD_CREATED,
        description="Thread event type"
    )
    
    @property
    def thread_id(self) -> UUID | None:
        """Get thread ID from payload."""
        thread_id = self.payload.get("thread_id")
        return UUID(thread_id) if thread_id else None
    
    @property
    def contact_id(self) -> UUID | None:
        """Get contact ID from payload."""
        contact_id = self.payload.get("contact_id")
        return UUID(contact_id) if contact_id else None


class AIEvent(Event):
    """
    Event for AI processing and analysis.
    
    Payload fields:
    - message_id: UUID of the message (if applicable)
    - thread_id: UUID of the thread (if applicable)
    - embedding_id: UUID of the embedding
    - entity_count: Number of entities extracted
    - summary_id: UUID of the summary
    - model: AI model used
    - processing_time_ms: Processing time in milliseconds
    - error: Error message (if failed)
    """
    
    event_type: EventType = Field(
        default=EventType.EMBEDDING_GENERATED,
        description="AI event type"
    )
    
    @property
    def message_id(self) -> UUID | None:
        """Get message ID from payload."""
        msg_id = self.payload.get("message_id")
        return UUID(msg_id) if msg_id else None
    
    @property
    def thread_id(self) -> UUID | None:
        """Get thread ID from payload."""
        thread_id = self.payload.get("thread_id")
        return UUID(thread_id) if thread_id else None


# Export all event types
__all__ = [
    "EventType",
    "Event",
    "ConnectionEvent",
    "MessageEvent",
    "ContactEvent",
    "ThreadEvent",
    "AIEvent",
]
