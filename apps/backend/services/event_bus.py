"""
Event Bus Implementation using Redis Streams

This module provides an event-driven architecture using Redis Streams with:
- Producer pattern for publishing events
- Consumer pattern with consumer groups
- Automatic acknowledgment and error handling
- Dead letter queue for failed events
- Event routing and filtering
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from db.redis_client import get_redis_client
from services.events.types import Event, EventType

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for publishing and consuming events via Redis Streams.

    Features:
    - Reliable message delivery with consumer groups
    - Automatic acknowledgment
    - Dead letter queue for failed messages
    - Event filtering and routing
    """

    # Stream names
    MAIN_STREAM = "events:main"
    DLQ_STREAM = "events:dlq"

    # Consumer group configuration
    DEFAULT_CONSUMER_GROUP = "default"
    MAX_RETRIES = 3

    def __init__(self, redis_client: Redis | None = None):
        """
        Initialize the event bus.

        Args:
            redis_client: Optional Redis client instance
        """
        self.redis = redis_client or get_redis_client()
        self._consumers: dict[str, asyncio.Task] = {}
        self._running = False

    async def initialize(self) -> None:
        """
        Initialize the event bus by creating streams and consumer groups.

        This should be called during application startup.
        """
        try:
            # Create main stream consumer group
            await self._create_consumer_group(
                self.MAIN_STREAM, self.DEFAULT_CONSUMER_GROUP
            )

            # Create DLQ stream consumer group
            await self._create_consumer_group(
                self.DLQ_STREAM, self.DEFAULT_CONSUMER_GROUP
            )

            logger.info("Event bus initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize event bus: {e}")
            raise

    async def _create_consumer_group(
        self, stream: str, group: str, mkstream: bool = True
    ) -> None:
        """
        Create a consumer group for a stream.

        Args:
            stream: Stream name
            group: Consumer group name
            mkstream: Create stream if it doesn't exist
        """
        try:
            await self.redis.xgroup_create(
                name=stream, groupname=group, id="0", mkstream=mkstream
            )
            logger.info(f"Created consumer group '{group}' for stream '{stream}'")
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                logger.debug(f"Consumer group '{group}' already exists for '{stream}'")
            else:
                raise

    async def publish(self, event: Event, stream: str | None = None) -> str:
        """
        Publish an event to the event bus.

        Args:
            event: Event to publish
            stream: Optional stream name (defaults to MAIN_STREAM)

        Returns:
            Message ID from Redis Streams
        """
        stream = stream or self.MAIN_STREAM

        try:
            # Serialize event to JSON
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "correlation_id": event.correlation_id or "",
                "payload": json.dumps(event.payload),
            }

            # Add to stream
            message_id = await self.redis.xadd(stream, event_data)

            logger.debug(
                f"Published event {event.event_type.value} "
                f"(id={event.event_id}) to {stream}"
            )

            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def consume(
        self,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
        event_types: list[EventType] | None = None,
        consumer_name: str | None = None,
        group: str | None = None,
        stream: str | None = None,
        block_ms: int = 5000,
        count: int = 10,
    ) -> None:
        """
        Consume events from the event bus.

        Args:
            handler: Async function to handle events
            event_types: Optional list of event types to filter
            consumer_name: Consumer name (defaults to UUID)
            group: Consumer group name
            stream: Stream name
            block_ms: Block time in milliseconds
            count: Number of messages to read per batch
        """
        consumer_name = consumer_name or f"consumer-{uuid4().hex[:8]}"
        group = group or self.DEFAULT_CONSUMER_GROUP
        stream = stream or self.MAIN_STREAM

        logger.info(
            f"Starting consumer '{consumer_name}' in group '{group}' "
            f"for stream '{stream}'"
        )

        self._running = True

        try:
            while self._running:
                try:
                    # Read messages from stream
                    messages = await self.redis.xreadgroup(
                        groupname=group,
                        consumername=consumer_name,
                        streams={stream: ">"},
                        count=count,
                        block=block_ms,
                    )

                    if not messages:
                        continue

                    # Process messages
                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            await self._process_message(
                                message_id,
                                message_data,
                                handler,
                                event_types,
                                group,
                                stream,
                            )

                except asyncio.CancelledError:
                    logger.info(f"Consumer '{consumer_name}' cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}")
                    await asyncio.sleep(1)  # Brief pause before retry

        finally:
            self._running = False
            logger.info(f"Consumer '{consumer_name}' stopped")

    async def _process_message(
        self,
        message_id: str,
        message_data: dict,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
        event_types: list[EventType] | None,
        group: str,
        stream: str,
    ) -> None:
        """
        Process a single message from the stream.

        Args:
            message_id: Redis message ID
            message_data: Message data
            handler: Event handler function
            event_types: Optional event type filter
            group: Consumer group name
            stream: Stream name
        """
        try:
            # Deserialize event
            event = self._deserialize_event(message_data)

            # Filter by event type if specified
            if event_types and event.event_type not in event_types:
                await self.redis.xack(stream, group, message_id)
                return

            # Handle event
            await handler(event)

            # Acknowledge message
            await self.redis.xack(stream, group, message_id)

            logger.debug(
                f"Processed event {event.event_type.value} " f"(id={event.event_id})"
            )

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}", exc_info=True)

            # Move to dead letter queue after max retries
            await self._handle_failed_message(
                message_id, message_data, stream, group, str(e)
            )

    def _deserialize_event(self, message_data: dict) -> Event:
        """
        Deserialize event from Redis message data.

        Args:
            message_data: Raw message data from Redis

        Returns:
            Event instance
        """
        return Event(
            event_id=message_data["event_id"],
            event_type=EventType(message_data["event_type"]),
            timestamp=datetime.fromisoformat(message_data["timestamp"]),
            source=message_data["source"],
            correlation_id=message_data.get("correlation_id") or None,
            payload=json.loads(message_data["payload"]),
        )

    async def _handle_failed_message(
        self, message_id: str, message_data: dict, stream: str, group: str, error: str
    ) -> None:
        """
        Handle a failed message by moving it to the dead letter queue.

        Args:
            message_id: Redis message ID
            message_data: Message data
            stream: Stream name
            group: Consumer group name
            error: Error message
        """
        try:
            # Add error information
            dlq_data = {
                **message_data,
                "original_stream": stream,
                "original_message_id": message_id,
                "error": error,
                "failed_at": datetime.utcnow().isoformat(),
            }

            # Add to DLQ
            await self.redis.xadd(self.DLQ_STREAM, dlq_data)

            # Acknowledge original message
            await self.redis.xack(stream, group, message_id)

            logger.warning(f"Moved message {message_id} to DLQ due to error: {error}")

        except Exception as e:
            logger.error(f"Failed to handle failed message: {e}")

    async def start_consumer(
        self,
        consumer_id: str,
        handler: Callable[[Event], Coroutine[Any, Any, None]],
        event_types: list[EventType] | None = None,
        **kwargs,
    ) -> None:
        """
        Start a background consumer task.

        Args:
            consumer_id: Unique consumer identifier
            handler: Event handler function
            event_types: Optional event type filter
            **kwargs: Additional arguments for consume()
        """
        if consumer_id in self._consumers:
            logger.warning(f"Consumer '{consumer_id}' already running")
            return

        task = asyncio.create_task(
            self.consume(handler, event_types, consumer_id, **kwargs)
        )
        self._consumers[consumer_id] = task

        logger.info(f"Started consumer '{consumer_id}'")

    async def stop_consumer(self, consumer_id: str) -> None:
        """
        Stop a background consumer task.

        Args:
            consumer_id: Consumer identifier
        """
        if consumer_id not in self._consumers:
            logger.warning(f"Consumer '{consumer_id}' not found")
            return

        task = self._consumers[consumer_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        del self._consumers[consumer_id]
        logger.info(f"Stopped consumer '{consumer_id}'")

    async def stop_all_consumers(self) -> None:
        """Stop all background consumer tasks."""
        self._running = False

        for consumer_id in list(self._consumers.keys()):
            await self.stop_consumer(consumer_id)

        logger.info("Stopped all consumers")

    async def get_stream_info(self, stream: str | None = None) -> dict:
        """
        Get information about a stream.

        Args:
            stream: Stream name (defaults to MAIN_STREAM)

        Returns:
            Stream information dictionary
        """
        stream = stream or self.MAIN_STREAM

        try:
            info = await self.redis.xinfo_stream(stream)
            return info
        except ResponseError:
            return {}

    async def get_pending_count(
        self, stream: str | None = None, group: str | None = None
    ) -> int:
        """
        Get count of pending messages in a consumer group.

        Args:
            stream: Stream name
            group: Consumer group name

        Returns:
            Number of pending messages
        """
        stream = stream or self.MAIN_STREAM
        group = group or self.DEFAULT_CONSUMER_GROUP

        try:
            pending = await self.redis.xpending(stream, group)
            return pending.get("pending", 0) if pending else 0
        except ResponseError:
            return 0


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """
    Get or create the global event bus instance.

    Returns:
        EventBus instance
    """
    global _event_bus

    if _event_bus is None:
        _event_bus = EventBus()

    return _event_bus


# Export public API
__all__ = [
    "EventBus",
    "get_event_bus",
]
