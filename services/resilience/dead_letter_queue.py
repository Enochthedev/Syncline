"""
Dead Letter Queue (DLQ) implementation for failed message processing.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from contextlib import asynccontextmanager

import redis.asyncio as redis
from db.redis_client import get_redis

logger = logging.getLogger(__name__)


class DLQMessageStatus(Enum):
    """Status of messages in the DLQ."""
    PENDING = "pending"
    RETRYING = "retrying"
    FAILED = "failed"
    POISON = "poison"
    RESOLVED = "resolved"


class DLQError(Exception):
    """Base exception for DLQ operations."""
    pass


@dataclass
class DLQMessage:
    """Message stored in the Dead Letter Queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_event: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    error_type: str = ""
    stack_trace: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    status: DLQMessageStatus = DLQMessageStatus.PENDING
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert DLQ message to dictionary for serialization."""
        return {
            'id': self.id,
            'original_event': self.original_event,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'stack_trace': self.stack_trace,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_retry_at': self.last_retry_at.isoformat() if self.last_retry_at else None,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DLQMessage':
        """Create DLQ message from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            original_event=data.get('original_event', {}),
            error_message=data.get('error_message', ''),
            error_type=data.get('error_type', ''),
            stack_trace=data.get('stack_trace'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            status=DLQMessageStatus(
                data.get('status', DLQMessageStatus.PENDING.value)),
            created_at=datetime.fromisoformat(data['created_at']),
            last_retry_at=datetime.fromisoformat(
                data['last_retry_at']) if data.get('last_retry_at') else None,
            next_retry_at=datetime.fromisoformat(
                data['next_retry_at']) if data.get('next_retry_at') else None,
            resolved_at=datetime.fromisoformat(
                data['resolved_at']) if data.get('resolved_at') else None,
            metadata=data.get('metadata', {})
        )

    def is_poison(self) -> bool:
        """Check if message should be considered poison."""
        return (
            self.retry_count >= self.max_retries or
            self.status == DLQMessageStatus.POISON
        )

    def calculate_next_retry(self, base_delay: float = 60.0, max_delay: float = 3600.0) -> datetime:
        """Calculate next retry time using exponential backoff."""
        delay = min(base_delay * (2 ** self.retry_count), max_delay)
        return datetime.now(timezone.utc) + timedelta(seconds=delay)


class DeadLetterQueue:
    """Dead Letter Queue implementation using Redis."""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        dlq_key_prefix: str = "dlq",
        retry_delay_base: float = 60.0,
        max_retry_delay: float = 3600.0,
        poison_threshold: int = 5
    ):
        self._redis = redis_client
        self._dlq_key_prefix = dlq_key_prefix
        self._retry_delay_base = retry_delay_base
        self._max_retry_delay = max_retry_delay
        self._poison_threshold = poison_threshold
        self._running = False
        self._retry_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the DLQ."""
        if not self._redis:
            self._redis = await get_redis()

        try:
            await self._redis.ping()
            logger.info("DeadLetterQueue initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeadLetterQueue: {e}")
            raise DLQError(f"Failed to initialize DLQ: {e}")

    async def add_message(
        self,
        event: Dict[str, Any],
        error: Exception,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a failed message to the DLQ."""
        try:
            import traceback

            dlq_message = DLQMessage(
                original_event=event,
                error_message=str(error),
                error_type=type(error).__name__,
                stack_trace=traceback.format_exc(),
                max_retries=max_retries,
                metadata=metadata or {}
            )

            # Calculate next retry time
            dlq_message.next_retry_at = dlq_message.calculate_next_retry(
                self._retry_delay_base, self._max_retry_delay
            )

            # Store in Redis
            key = f"{self._dlq_key_prefix}:messages:{dlq_message.id}"
            await self._redis.hset(key, mapping={
                'data': json.dumps(dlq_message.to_dict()),
                'status': dlq_message.status.value,
                'next_retry': dlq_message.next_retry_at.timestamp(),
                'created_at': dlq_message.created_at.timestamp()
            })

            # Add to retry queue if not poison
            if not dlq_message.is_poison():
                await self._redis.zadd(
                    f"{self._dlq_key_prefix}:retry_queue",
                    {dlq_message.id: dlq_message.next_retry_at.timestamp()}
                )

            # Add to status index
            await self._redis.sadd(
                f"{self._dlq_key_prefix}:status:{dlq_message.status.value}",
                dlq_message.id
            )

            logger.warning(f"Added message {dlq_message.id} to DLQ: {error}")
            return dlq_message.id

        except Exception as e:
            logger.error(f"Failed to add message to DLQ: {e}")
            raise DLQError(f"Failed to add message to DLQ: {e}")

    async def get_message(self, message_id: str) -> Optional[DLQMessage]:
        """Get a message from the DLQ by ID."""
        try:
            key = f"{self._dlq_key_prefix}:messages:{message_id}"
            data = await self._redis.hget(key, 'data')

            if not data:
                return None

            message_dict = json.loads(data)
            return DLQMessage.from_dict(message_dict)

        except Exception as e:
            logger.error(f"Failed to get DLQ message {message_id}: {e}")
            return None

    async def retry_message(
        self,
        message_id: str,
        handler: Callable[[Dict[str, Any]], Any]
    ) -> bool:
        """Retry processing a message from the DLQ."""
        try:
            message = await self.get_message(message_id)
            if not message:
                logger.error(f"DLQ message {message_id} not found")
                return False

            if message.is_poison():
                logger.warning(f"Message {message_id} is poison, cannot retry")
                await self._mark_as_poison(message)
                return False

            # Update retry status
            message.status = DLQMessageStatus.RETRYING
            message.retry_count += 1
            message.last_retry_at = datetime.now(timezone.utc)

            await self._update_message(message)

            try:
                # Attempt to process the message
                if asyncio.iscoroutinefunction(handler):
                    await handler(message.original_event)
                else:
                    handler(message.original_event)

                # Mark as resolved
                await self._mark_as_resolved(message)
                logger.info(f"Successfully retried DLQ message {message_id}")
                return True

            except Exception as retry_error:
                logger.error(
                    f"Retry failed for message {message_id}: {retry_error}")

                # Update error information
                import traceback
                message.error_message = str(retry_error)
                message.error_type = type(retry_error).__name__
                message.stack_trace = traceback.format_exc()

                if message.retry_count >= message.max_retries:
                    await self._mark_as_poison(message)
                else:
                    # Schedule next retry
                    message.status = DLQMessageStatus.PENDING
                    message.next_retry_at = message.calculate_next_retry(
                        self._retry_delay_base, self._max_retry_delay
                    )
                    await self._update_message(message)
                    await self._redis.zadd(
                        f"{self._dlq_key_prefix}:retry_queue",
                        {message_id: message.next_retry_at.timestamp()}
                    )

                return False

        except Exception as e:
            logger.error(f"Failed to retry message {message_id}: {e}")
            return False

    async def start_retry_processor(
        self,
        handler: Callable[[Dict[str, Any]], Any],
        check_interval: float = 60.0
    ) -> None:
        """Start the automatic retry processor."""
        if self._running:
            logger.warning("Retry processor is already running")
            return

        self._running = True
        self._retry_task = asyncio.create_task(
            self._retry_processor_loop(handler, check_interval)
        )
        logger.info("Started DLQ retry processor")

    async def stop_retry_processor(self) -> None:
        """Stop the automatic retry processor."""
        if not self._running:
            return

        self._running = False
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped DLQ retry processor")

    async def _retry_processor_loop(
        self,
        handler: Callable[[Dict[str, Any]], Any],
        check_interval: float
    ) -> None:
        """Main loop for the retry processor."""
        while self._running:
            try:
                # Get messages ready for retry
                now = datetime.now(timezone.utc).timestamp()
                ready_messages = await self._redis.zrangebyscore(
                    f"{self._dlq_key_prefix}:retry_queue",
                    0, now, withscores=False
                )

                for message_id in ready_messages:
                    message_id = message_id.decode()

                    # Remove from retry queue
                    await self._redis.zrem(
                        f"{self._dlq_key_prefix}:retry_queue",
                        message_id
                    )

                    # Attempt retry
                    await self.retry_message(message_id, handler)

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry processor loop: {e}")
                await asyncio.sleep(check_interval)

    async def _update_message(self, message: DLQMessage) -> None:
        """Update a message in the DLQ."""
        key = f"{self._dlq_key_prefix}:messages:{message.id}"

        # Update main data
        await self._redis.hset(key, mapping={
            'data': json.dumps(message.to_dict()),
            'status': message.status.value,
            'next_retry': message.next_retry_at.timestamp() if message.next_retry_at else 0
        })

        # Update status indexes
        for status in DLQMessageStatus:
            await self._redis.srem(
                f"{self._dlq_key_prefix}:status:{status.value}",
                message.id
            )

        await self._redis.sadd(
            f"{self._dlq_key_prefix}:status:{message.status.value}",
            message.id
        )

    async def _mark_as_resolved(self, message: DLQMessage) -> None:
        """Mark a message as resolved."""
        message.status = DLQMessageStatus.RESOLVED
        message.resolved_at = datetime.now(timezone.utc)
        await self._update_message(message)

    async def _mark_as_poison(self, message: DLQMessage) -> None:
        """Mark a message as poison."""
        message.status = DLQMessageStatus.POISON
        await self._update_message(message)

        # Remove from retry queue
        await self._redis.zrem(
            f"{self._dlq_key_prefix}:retry_queue",
            message.id
        )

        logger.warning(
            f"Marked message {message.id} as poison after {message.retry_count} retries")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        try:
            stats = {}

            # Count messages by status
            for status in DLQMessageStatus:
                count = await self._redis.scard(
                    f"{self._dlq_key_prefix}:status:{status.value}"
                )
                stats[f"{status.value}_count"] = count

            # Get retry queue size
            retry_queue_size = await self._redis.zcard(
                f"{self._dlq_key_prefix}:retry_queue"
            )
            stats['retry_queue_size'] = retry_queue_size

            # Get next retry time
            next_retry = await self._redis.zrange(
                f"{self._dlq_key_prefix}:retry_queue",
                0, 0, withscores=True
            )
            if next_retry:
                stats['next_retry_at'] = datetime.fromtimestamp(
                    next_retry[0][1], tz=timezone.utc
                ).isoformat()

            stats['processor_running'] = self._running
            return stats

        except Exception as e:
            logger.error(f"Failed to get DLQ statistics: {e}")
            return {}


# Global DLQ instance
dead_letter_queue = DeadLetterQueue()


async def get_dead_letter_queue() -> DeadLetterQueue:
    """Get the global DLQ instance."""
    return dead_letter_queue


async def initialize_dlq() -> None:
    """Initialize the global DLQ."""
    await dead_letter_queue.initialize()


@asynccontextmanager
async def dlq_context():
    """Context manager for DLQ lifecycle."""
    try:
        await initialize_dlq()
        yield dead_letter_queue
    finally:
        await dead_letter_queue.stop_retry_processor()
