"""
Event-driven messaging infrastructure using Redis Streams.

This module provides the core event bus functionality for the MESH system,
enabling reliable message processing with producer/consumer patterns.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import asynccontextmanager

import redis.asyncio as redis
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


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
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'data': self.data,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'correlation_id': self.correlation_id,
            'source': self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=EventType(data['type']),
            data=data.get('data', {}),
            metadata=data.get('metadata', {}),
            timestamp=datetime.fromisoformat(data['timestamp']),
            priority=EventPriority(
                data.get('priority', EventPriority.NORMAL.value)),
            correlation_id=data.get('correlation_id'),
            source=data.get('source')
        )


@dataclass
class ConsumerConfig:
    """Configuration for event consumers."""
    group_name: str
    consumer_name: str
    stream_name: str
    batch_size: int = 10
    block_time: int = 1000  # milliseconds
    auto_ack: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


class EventBusError(Exception):
    """Base exception for event bus errors."""
    pass


class EventSerializationError(EventBusError):
    """Error during event serialization/deserialization."""
    pass


class EventPublishError(EventBusError):
    """Error during event publishing."""
    pass


class EventConsumerError(EventBusError):
    """Error during event consumption."""
    pass


class EventBus:
    """
    Redis Streams-based event bus for reliable message processing.

    Provides producer/consumer patterns with consumer groups for
    reliable message delivery and processing guarantees.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._consumers: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def initialize(self) -> None:
        """Initialize the event bus."""
        if not self._redis:
            self._redis = await get_redis()

        # Test Redis connection
        try:
            await self._redis.ping()
            logger.info("EventBus initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EventBus: {e}")
            raise EventBusError(f"Failed to initialize EventBus: {e}")

    async def publish(
        self,
        stream_name: str,
        event: Event,
        max_length: Optional[int] = 10000
    ) -> str:
        """
        Publish an event to a Redis stream.

        Args:
            stream_name: Name of the stream to publish to
            event: Event to publish
            max_length: Maximum stream length (for memory management)

        Returns:
            Message ID from Redis

        Raises:
            EventPublishError: If publishing fails
        """
        try:
            # Serialize event data
            serialized_data = self._serialize_event(event)

            # Add to stream with optional max length
            kwargs = {'fields': serialized_data}
            if max_length:
                kwargs['maxlen'] = max_length
                kwargs['approximate'] = True

            message_id = await self._redis.xadd(stream_name, **kwargs)

            logger.debug(
                f"Published event {event.id} to stream {stream_name} "
                f"with message ID {message_id}"
            )

            return message_id

        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}")
            raise EventPublishError(f"Failed to publish event: {e}")

    async def create_consumer_group(
        self,
        stream_name: str,
        group_name: str,
        start_id: str = "0"
    ) -> bool:
        """
        Create a consumer group for a stream.

        Args:
            stream_name: Name of the stream
            group_name: Name of the consumer group
            start_id: Starting message ID (0 for beginning, $ for new messages)

        Returns:
            True if group was created, False if it already exists
        """
        try:
            await self._redis.xgroup_create(
                stream_name, group_name, start_id, mkstream=True
            )
            logger.info(
                f"Created consumer group {group_name} for stream {stream_name}")
            return True

        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {group_name} already exists")
                return False
            else:
                logger.error(f"Failed to create consumer group: {e}")
                raise EventBusError(f"Failed to create consumer group: {e}")

    async def subscribe(
        self,
        config: ConsumerConfig,
        handler: Callable[[Event], Any]
    ) -> None:
        """
        Subscribe to events with a consumer group.

        Args:
            config: Consumer configuration
            handler: Async function to handle events
        """
        # Ensure consumer group exists
        await self.create_consumer_group(config.stream_name, config.group_name)

        # Store consumer configuration
        consumer_key = f"{config.group_name}:{config.consumer_name}"
        self._consumers[consumer_key] = {
            'config': config,
            'handler': handler,
            'running': False
        }

        logger.info(
            f"Subscribed consumer {config.consumer_name} to group "
            f"{config.group_name} on stream {config.stream_name}"
        )

    async def start_consumers(self) -> None:
        """Start all registered consumers."""
        if self._running:
            logger.warning("Consumers are already running")
            return

        self._running = True

        for consumer_key, consumer_info in self._consumers.items():
            if not consumer_info['running']:
                task = asyncio.create_task(
                    self._run_consumer(consumer_key, consumer_info)
                )
                self._tasks.append(task)
                consumer_info['running'] = True

        logger.info(f"Started {len(self._tasks)} consumer tasks")

    async def stop_consumers(self) -> None:
        """Stop all running consumers."""
        if not self._running:
            return

        self._running = False

        # Cancel all consumer tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Reset state
        self._tasks.clear()
        for consumer_info in self._consumers.values():
            consumer_info['running'] = False

        logger.info("Stopped all consumers")

    async def _run_consumer(self, consumer_key: str, consumer_info: Dict[str, Any]) -> None:
        """Run a single consumer in a loop."""
        config: ConsumerConfig = consumer_info['config']
        handler: Callable = consumer_info['handler']

        logger.info(f"Starting consumer {consumer_key}")

        while self._running:
            try:
                # Read messages from stream
                messages = await self._redis.xreadgroup(
                    config.group_name,
                    config.consumer_name,
                    {config.stream_name: '>'},
                    count=config.batch_size,
                    block=config.block_time
                )

                if not messages:
                    continue

                # Process messages
                for stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_message(
                            config, handler, stream_name, message_id, fields
                        )

            except asyncio.CancelledError:
                logger.info(f"Consumer {consumer_key} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer {consumer_key}: {e}")
                await asyncio.sleep(config.retry_delay)

    async def _process_message(
        self,
        config: ConsumerConfig,
        handler: Callable,
        stream_name: str,
        message_id: str,
        fields: Dict[str, str]
    ) -> None:
        """Process a single message."""
        try:
            # Deserialize event
            event = self._deserialize_event(fields)

            logger.debug(
                f"Processing event {event.id} from stream {stream_name} "
                f"(message ID: {message_id})"
            )

            # Call handler
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

            # Acknowledge message if auto-ack is enabled
            if config.auto_ack:
                await self._redis.xack(config.stream_name, config.group_name, message_id)
                logger.debug(f"Acknowledged message {message_id}")

        except Exception as e:
            logger.error(
                f"Failed to process message {message_id} from stream {stream_name}: {e}"
            )

            # TODO: Implement retry logic and dead letter queue
            # For now, we'll acknowledge the message to prevent infinite retries
            if config.auto_ack:
                await self._redis.xack(config.stream_name, config.group_name, message_id)

    def _serialize_event(self, event: Event) -> Dict[str, str]:
        """Serialize event to Redis stream format."""
        try:
            event_dict = event.to_dict()

            # Convert all values to strings for Redis
            serialized = {}
            for key, value in event_dict.items():
                if isinstance(value, (dict, list)):
                    serialized[key] = json.dumps(value)
                else:
                    serialized[key] = str(value)

            return serialized

        except Exception as e:
            raise EventSerializationError(f"Failed to serialize event: {e}")

    def _deserialize_event(self, fields: Dict[str, str]) -> Event:
        """Deserialize event from Redis stream format."""
        try:
            # Convert string values back to appropriate types
            event_dict = {}
            for key, value in fields.items():
                if key in ['data', 'metadata']:
                    event_dict[key] = json.loads(value) if value else {}
                elif key == 'timestamp':
                    event_dict[key] = value  # Will be parsed in from_dict
                else:
                    event_dict[key] = value

            return Event.from_dict(event_dict)

        except Exception as e:
            raise EventSerializationError(f"Failed to deserialize event: {e}")

    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about a stream."""
        try:
            info = await self._redis.xinfo_stream(stream_name)
            return info
        except redis.ResponseError:
            return {}

    async def get_consumer_group_info(
        self, stream_name: str, group_name: str
    ) -> Dict[str, Any]:
        """Get information about a consumer group."""
        try:
            groups = await self._redis.xinfo_groups(stream_name)
            for group in groups:
                if group['name'] == group_name:
                    return group
            return {}
        except redis.ResponseError:
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the event bus."""
        try:
            # Test Redis connection
            await self._redis.ping()

            # Get consumer status
            consumer_status = {}
            for consumer_key, consumer_info in self._consumers.items():
                consumer_status[consumer_key] = {
                    'running': consumer_info['running'],
                    'config': {
                        'group_name': consumer_info['config'].group_name,
                        'stream_name': consumer_info['config'].stream_name,
                        'batch_size': consumer_info['config'].batch_size
                    }
                }

            return {
                'status': 'healthy',
                'redis_connected': True,
                'consumers_running': self._running,
                'consumer_count': len(self._consumers),
                'active_tasks': len(self._tasks),
                'consumers': consumer_status
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'redis_connected': False,
                'consumers_running': self._running
            }


# Global event bus instance
event_bus = EventBus()


async def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return event_bus


async def initialize_event_bus() -> None:
    """Initialize the global event bus."""
    await event_bus.initialize()


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus."""
    await event_bus.stop_consumers()


@asynccontextmanager
async def event_bus_context():
    """Context manager for event bus lifecycle."""
    try:
        await initialize_event_bus()
        yield event_bus
    finally:
        await shutdown_event_bus()
