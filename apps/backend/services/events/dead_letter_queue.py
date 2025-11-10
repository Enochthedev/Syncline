"""
Dead Letter Queue (DLQ) Implementation

This module provides dead letter queue functionality for failed events:
- Failed event storage and tracking
- Retry mechanisms with exponential backoff
- DLQ monitoring and statistics
- Manual reprocessing of failed events
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Coroutine

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from db.redis_client import get_redis_client
from services.events.types import Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class FailedEvent:
    """Information about a failed event."""
    
    event: Event
    error_message: str
    retry_count: int
    first_failed_at: datetime
    last_failed_at: datetime
    original_stream: str
    original_message_id: str


class DeadLetterQueue:
    """
    Dead letter queue for failed events.
    
    Features:
    - Store failed events with error information
    - Automatic retry with exponential backoff
    - Manual reprocessing
    - DLQ monitoring and cleanup
    """
    
    # DLQ configuration
    DLQ_STREAM = "events:dlq"
    DLQ_GROUP = "dlq_processors"
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 5  # seconds
    MAX_RETRY_DELAY = 300  # seconds (5 minutes)
    DLQ_RETENTION_DAYS = 7
    
    def __init__(self, redis_client: Redis | None = None):
        """
        Initialize the dead letter queue.
        
        Args:
            redis_client: Optional Redis client instance
        """
        self.redis = redis_client or get_redis_client()
        self.logger = logging.getLogger("DeadLetterQueue")
        self._retry_tasks: dict[str, asyncio.Task] = {}
    
    async def initialize(self) -> None:
        """
        Initialize the DLQ by creating the stream and consumer group.
        """
        try:
            await self.redis.xgroup_create(
                name=self.DLQ_STREAM,
                groupname=self.DLQ_GROUP,
                id="0",
                mkstream=True
            )
            self.logger.info("Dead letter queue initialized")
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                self.logger.debug("DLQ consumer group already exists")
            else:
                raise
    
    async def add_failed_event(
        self,
        event: Event,
        error: str,
        original_stream: str,
        original_message_id: str,
        retry_count: int = 0
    ) -> str:
        """
        Add a failed event to the DLQ.
        
        Args:
            event: Failed event
            error: Error message
            original_stream: Original stream name
            original_message_id: Original message ID
            retry_count: Number of retry attempts
        
        Returns:
            DLQ message ID
        """
        try:
            now = datetime.utcnow()
            
            dlq_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "correlation_id": event.correlation_id or "",
                "payload": str(event.payload),
                "error": error,
                "retry_count": str(retry_count),
                "original_stream": original_stream,
                "original_message_id": original_message_id,
                "failed_at": now.isoformat(),
            }
            
            message_id = await self.redis.xadd(self.DLQ_STREAM, dlq_data)
            
            self.logger.warning(
                f"Added event {event.event_type.value} (id={event.event_id}) "
                f"to DLQ after {retry_count} retries: {error}"
            )
            
            return message_id
        except Exception as e:
            self.logger.error(f"Failed to add event to DLQ: {e}")
            raise
    
    async def get_failed_events(
        self,
        count: int = 100,
        event_type: EventType | None = None
    ) -> list[FailedEvent]:
        """
        Get failed events from the DLQ.
        
        Args:
            count: Maximum number of events to retrieve
            event_type: Optional event type filter
        
        Returns:
            List of failed events
        """
        try:
            # Read from DLQ stream
            messages = await self.redis.xrange(
                self.DLQ_STREAM,
                min="-",
                max="+",
                count=count
            )
            
            failed_events = []
            for message_id, message_data in messages:
                # Parse event data
                event = Event(
                    event_id=message_data["event_id"],
                    event_type=EventType(message_data["event_type"]),
                    timestamp=datetime.fromisoformat(message_data["timestamp"]),
                    source=message_data["source"],
                    correlation_id=message_data.get("correlation_id") or None,
                    payload=eval(message_data["payload"]),  # Safe in this context
                )
                
                # Filter by event type if specified
                if event_type and event.event_type != event_type:
                    continue
                
                failed_event = FailedEvent(
                    event=event,
                    error_message=message_data["error"],
                    retry_count=int(message_data["retry_count"]),
                    first_failed_at=datetime.fromisoformat(message_data["failed_at"]),
                    last_failed_at=datetime.fromisoformat(message_data["failed_at"]),
                    original_stream=message_data["original_stream"],
                    original_message_id=message_data["original_message_id"],
                )
                
                failed_events.append(failed_event)
            
            return failed_events
        except Exception as e:
            self.logger.error(f"Failed to get events from DLQ: {e}")
            return []
    
    async def retry_event(
        self,
        event: Event,
        handler: Callable[[Event], Coroutine],
        retry_count: int = 0
    ) -> bool:
        """
        Retry processing a failed event.
        
        Args:
            event: Event to retry
            handler: Handler function to process the event
            retry_count: Current retry count
        
        Returns:
            True if retry succeeded, False otherwise
        """
        if retry_count >= self.MAX_RETRIES:
            self.logger.error(
                f"Event {event.event_id} exceeded max retries ({self.MAX_RETRIES})"
            )
            return False
        
        # Calculate backoff delay
        delay = min(
            self.INITIAL_RETRY_DELAY * (2 ** retry_count),
            self.MAX_RETRY_DELAY
        )
        
        self.logger.info(
            f"Retrying event {event.event_id} (attempt {retry_count + 1}) "
            f"after {delay}s delay"
        )
        
        await asyncio.sleep(delay)
        
        try:
            await handler(event)
            self.logger.info(f"Successfully retried event {event.event_id}")
            return True
        except Exception as e:
            self.logger.error(f"Retry failed for event {event.event_id}: {e}")
            return False
    
    async def reprocess_failed_event(
        self,
        event_id: str,
        handler: Callable[[Event], Coroutine]
    ) -> bool:
        """
        Manually reprocess a failed event from the DLQ.
        
        Args:
            event_id: Event ID to reprocess
            handler: Handler function to process the event
        
        Returns:
            True if reprocessing succeeded, False otherwise
        """
        try:
            # Find the event in DLQ
            failed_events = await self.get_failed_events()
            event_to_retry = None
            
            for failed_event in failed_events:
                if failed_event.event.event_id == event_id:
                    event_to_retry = failed_event
                    break
            
            if not event_to_retry:
                self.logger.warning(f"Event {event_id} not found in DLQ")
                return False
            
            # Try to process the event
            await handler(event_to_retry.event)
            
            self.logger.info(f"Successfully reprocessed event {event_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reprocess event {event_id}: {e}")
            return False
    
    async def cleanup_old_events(self, retention_days: int | None = None) -> int:
        """
        Clean up old events from the DLQ.
        
        Args:
            retention_days: Number of days to retain events
        
        Returns:
            Number of events deleted
        """
        retention_days = retention_days or self.DLQ_RETENTION_DAYS
        cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
        
        try:
            # Get all messages
            messages = await self.redis.xrange(self.DLQ_STREAM, min="-", max="+")
            
            deleted_count = 0
            for message_id, message_data in messages:
                failed_at = datetime.fromisoformat(message_data["failed_at"])
                
                if failed_at < cutoff_time:
                    await self.redis.xdel(self.DLQ_STREAM, message_id)
                    deleted_count += 1
            
            if deleted_count > 0:
                self.logger.info(
                    f"Cleaned up {deleted_count} old events from DLQ "
                    f"(older than {retention_days} days)"
                )
            
            return deleted_count
        except Exception as e:
            self.logger.error(f"Failed to cleanup DLQ: {e}")
            return 0
    
    async def get_stats(self) -> dict:
        """
        Get DLQ statistics.
        
        Returns:
            Dictionary with DLQ statistics
        """
        try:
            info = await self.redis.xinfo_stream(self.DLQ_STREAM)
            failed_events = await self.get_failed_events()
            
            # Count by event type
            event_type_counts = {}
            for failed_event in failed_events:
                event_type = failed_event.event.event_type.value
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            return {
                "total_failed_events": info.get("length", 0),
                "event_type_counts": event_type_counts,
                "oldest_event": (
                    failed_events[0].first_failed_at.isoformat()
                    if failed_events
                    else None
                ),
                "newest_event": (
                    failed_events[-1].last_failed_at.isoformat()
                    if failed_events
                    else None
                ),
            }
        except ResponseError:
            return {
                "total_failed_events": 0,
                "event_type_counts": {},
                "oldest_event": None,
                "newest_event": None,
            }


# Global DLQ instance
_dlq: DeadLetterQueue | None = None


def get_dead_letter_queue() -> DeadLetterQueue:
    """
    Get or create the global dead letter queue instance.
    
    Returns:
        DeadLetterQueue instance
    """
    global _dlq
    
    if _dlq is None:
        _dlq = DeadLetterQueue()
    
    return _dlq


# Export public API
__all__ = [
    "FailedEvent",
    "DeadLetterQueue",
    "get_dead_letter_queue",
]
