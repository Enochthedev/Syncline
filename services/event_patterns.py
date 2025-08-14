"""
Common event patterns and utilities for the MESH event bus.

This module provides helper functions and patterns for working with
the event bus, including event factories and common handlers.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from services.event_bus import Event, EventType, EventPriority
from services.message_schema import NormalizedMessage, RawMessage, Platform

logger = logging.getLogger(__name__)


class EventFactory:
    """Factory for creating common event types."""

    @staticmethod
    def create_message_received_event(
        raw_message: RawMessage,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create a message received event."""
        return Event(
            type=EventType.MESSAGE_RECEIVED,
            data={
                'platform': raw_message.platform.value,
                'platform_message_id': raw_message.platform_message_id,
                'raw_data': raw_message.raw_data,
                'received_at': raw_message.received_at.isoformat()
            },
            metadata={
                'platform': raw_message.platform.value,
                'message_size': len(str(raw_message.raw_data))
            },
            correlation_id=correlation_id,
            source=source or f"{raw_message.platform.value}_connector",
            priority=EventPriority.HIGH
        )

    @staticmethod
    def create_message_normalized_event(
        normalized_message: NormalizedMessage,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create a message normalized event."""
        return Event(
            type=EventType.MESSAGE_NORMALIZED,
            data=normalized_message.to_dict(),
            metadata={
                'platform': normalized_message.platform.value,
                'thread_id': normalized_message.thread_id,
                'sender_id': normalized_message.sender.id,
                'has_attachments': normalized_message.has_attachments(),
                'attachment_count': normalized_message.get_attachment_count()
            },
            correlation_id=correlation_id,
            source=source or "message_normalizer",
            priority=EventPriority.NORMAL
        )

    @staticmethod
    def create_message_processed_event(
        message_id: str,
        processing_results: Dict[str, Any],
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create a message processed event."""
        return Event(
            type=EventType.MESSAGE_PROCESSED,
            data={
                'message_id': message_id,
                'processing_results': processing_results,
                'processed_at': datetime.utcnow().isoformat()
            },
            metadata={
                'entities_extracted': len(processing_results.get('entities', [])),
                'summary_generated': 'summary' in processing_results,
                'action_items_found': len(processing_results.get('action_items', []))
            },
            correlation_id=correlation_id,
            source=source or "ai_processing_engine",
            priority=EventPriority.NORMAL
        )

    @staticmethod
    def create_thread_updated_event(
        thread_id: str,
        update_type: str,
        update_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create a thread updated event."""
        return Event(
            type=EventType.THREAD_UPDATED,
            data={
                'thread_id': thread_id,
                'update_type': update_type,
                'update_data': update_data,
                'updated_at': datetime.utcnow().isoformat()
            },
            metadata={
                'update_type': update_type,
                'thread_id': thread_id
            },
            correlation_id=correlation_id,
            source=source or "thread_manager",
            priority=EventPriority.LOW
        )

    @staticmethod
    def create_entity_extracted_event(
        message_id: str,
        entities: list,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create an entity extracted event."""
        return Event(
            type=EventType.ENTITY_EXTRACTED,
            data={
                'message_id': message_id,
                'entities': entities,
                'extracted_at': datetime.utcnow().isoformat()
            },
            metadata={
                'entity_count': len(entities),
                'entity_types': list(set(entity.get('type') for entity in entities))
            },
            correlation_id=correlation_id,
            source=source or "entity_extraction_agent",
            priority=EventPriority.LOW
        )

    @staticmethod
    def create_summary_generated_event(
        summary_id: str,
        summary_type: str,
        scope_id: str,
        summary_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create a summary generated event."""
        return Event(
            type=EventType.SUMMARY_GENERATED,
            data={
                'summary_id': summary_id,
                'summary_type': summary_type,
                'scope_id': scope_id,
                'summary_data': summary_data,
                'generated_at': datetime.utcnow().isoformat()
            },
            metadata={
                'summary_type': summary_type,
                'scope_id': scope_id,
                'content_length': len(summary_data.get('content', ''))
            },
            correlation_id=correlation_id,
            source=source or "summary_generation_agent",
            priority=EventPriority.LOW
        )

    @staticmethod
    def create_error_event(
        error_type: str,
        error_message: str,
        error_context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        source: Optional[str] = None
    ) -> Event:
        """Create an error event."""
        return Event(
            type=EventType.ERROR_OCCURRED,
            data={
                'error_type': error_type,
                'error_message': error_message,
                'error_context': error_context,
                'occurred_at': datetime.utcnow().isoformat()
            },
            metadata={
                'error_type': error_type,
                'severity': error_context.get('severity', 'error')
            },
            correlation_id=correlation_id,
            source=source or "unknown",
            priority=EventPriority.CRITICAL
        )

    @staticmethod
    def create_health_check_event(
        component: str,
        status: str,
        details: Dict[str, Any],
        source: Optional[str] = None
    ) -> Event:
        """Create a health check event."""
        return Event(
            type=EventType.HEALTH_CHECK,
            data={
                'component': component,
                'status': status,
                'details': details,
                'checked_at': datetime.utcnow().isoformat()
            },
            metadata={
                'component': component,
                'status': status
            },
            source=source or component,
            priority=EventPriority.LOW
        )


class StreamNames:
    """Standard stream names for the MESH system."""

    # Core message processing streams
    RAW_MESSAGES = "mesh.messages.raw"
    NORMALIZED_MESSAGES = "mesh.messages.normalized"
    PROCESSED_MESSAGES = "mesh.messages.processed"

    # AI processing streams
    ENTITY_EXTRACTION = "mesh.ai.entities"
    SUMMARY_GENERATION = "mesh.ai.summaries"
    ACTION_ITEMS = "mesh.ai.action_items"

    # System streams
    THREAD_UPDATES = "mesh.threads.updates"
    PARTICIPANT_UPDATES = "mesh.participants.updates"
    ERRORS = "mesh.system.errors"
    HEALTH_CHECKS = "mesh.system.health"

    # Platform-specific streams
    GMAIL_EVENTS = "mesh.platforms.gmail"
    SLACK_EVENTS = "mesh.platforms.slack"
    DISCORD_EVENTS = "mesh.platforms.discord"
    WHATSAPP_EVENTS = "mesh.platforms.whatsapp"
    TWITTER_EVENTS = "mesh.platforms.twitter"
    TELEGRAM_EVENTS = "mesh.platforms.telegram"


class ConsumerGroups:
    """Standard consumer group names."""

    # Message processing groups
    MESSAGE_NORMALIZERS = "message_normalizers"
    AI_PROCESSORS = "ai_processors"
    ENTITY_EXTRACTORS = "entity_extractors"
    SUMMARY_GENERATORS = "summary_generators"

    # Storage groups
    DATABASE_WRITERS = "database_writers"
    VECTOR_INDEXERS = "vector_indexers"
    BLOB_PROCESSORS = "blob_processors"

    # Notification groups
    REAL_TIME_NOTIFIERS = "real_time_notifiers"
    WEBHOOK_DISPATCHERS = "webhook_dispatchers"

    # System groups
    ERROR_HANDLERS = "error_handlers"
    HEALTH_MONITORS = "health_monitors"
    AUDIT_LOGGERS = "audit_loggers"


class EventHandlers:
    """Common event handler utilities."""

    @staticmethod
    async def log_event_handler(event: Event) -> None:
        """Simple logging event handler for debugging."""
        logger.info(
            f"Event received: {event.type.value} "
            f"(ID: {event.id}, Source: {event.source})"
        )
        logger.debug(f"Event data: {event.data}")

    @staticmethod
    async def error_event_handler(event: Event) -> None:
        """Handler for error events."""
        if event.type == EventType.ERROR_OCCURRED:
            error_type = event.data.get('error_type', 'unknown')
            error_message = event.data.get('error_message', 'No message')
            error_context = event.data.get('error_context', {})

            logger.error(
                f"Error event: {error_type} - {error_message}",
                extra={
                    'event_id': event.id,
                    'correlation_id': event.correlation_id,
                    'source': event.source,
                    'context': error_context
                }
            )

    @staticmethod
    async def health_check_handler(event: Event) -> None:
        """Handler for health check events."""
        if event.type == EventType.HEALTH_CHECK:
            component = event.data.get('component', 'unknown')
            status = event.data.get('status', 'unknown')

            if status == 'healthy':
                logger.debug(f"Health check: {component} is healthy")
            else:
                logger.warning(
                    f"Health check: {component} is {status}",
                    extra={
                        'component': component,
                        'details': event.data.get('details', {})
                    }
                )


def get_correlation_id_from_message(message: NormalizedMessage) -> str:
    """Generate a correlation ID from a normalized message."""
    return f"{message.platform.value}:{message.platform_message_id}"


def get_stream_name_for_platform(platform: Platform) -> str:
    """Get the appropriate stream name for a platform."""
    stream_mapping = {
        Platform.GMAIL: StreamNames.GMAIL_EVENTS,
        Platform.SLACK: StreamNames.SLACK_EVENTS,
        Platform.DISCORD: StreamNames.DISCORD_EVENTS,
        Platform.WHATSAPP: StreamNames.WHATSAPP_EVENTS,
        Platform.TWITTER: StreamNames.TWITTER_EVENTS,
        Platform.TELEGRAM: StreamNames.TELEGRAM_EVENTS,
    }
    return stream_mapping.get(platform, StreamNames.RAW_MESSAGES)


def should_prioritize_event(event: Event) -> bool:
    """Determine if an event should be prioritized."""
    high_priority_types = {
        EventType.MESSAGE_RECEIVED,
        EventType.ERROR_OCCURRED
    }

    return (
        event.type in high_priority_types or
        event.priority in {EventPriority.HIGH, EventPriority.CRITICAL}
    )
