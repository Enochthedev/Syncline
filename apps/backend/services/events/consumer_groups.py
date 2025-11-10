"""
Consumer Group Management

This module provides utilities for managing Redis Streams consumer groups:
- Consumer group lifecycle management
- Consumer registration and tracking
- Load balancing across consumers
- Consumer health monitoring
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Coroutine

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from db.redis_client import get_redis_client
from services.events.types import Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class ConsumerInfo:
    """Information about a consumer."""
    
    consumer_id: str
    group_name: str
    stream_name: str
    event_types: list[EventType] | None
    started_at: datetime
    is_active: bool = True
    messages_processed: int = 0
    errors: int = 0


class ConsumerGroupManager:
    """
    Manages consumer groups for Redis Streams.
    
    Features:
    - Consumer registration and tracking
    - Consumer group creation and deletion
    - Consumer health monitoring
    - Load balancing
    """
    
    def __init__(self, redis_client: Redis | None = None):
        """
        Initialize the consumer group manager.
        
        Args:
            redis_client: Optional Redis client instance
        """
        self.redis = redis_client or get_redis_client()
        self.consumers: dict[str, ConsumerInfo] = {}
        self.logger = logging.getLogger("ConsumerGroupManager")
    
    async def create_group(
        self,
        stream: str,
        group: str,
        start_id: str = "0",
        mkstream: bool = True
    ) -> bool:
        """
        Create a consumer group for a stream.
        
        Args:
            stream: Stream name
            group: Consumer group name
            start_id: Starting message ID (0 for beginning, $ for new messages)
            mkstream: Create stream if it doesn't exist
        
        Returns:
            True if group was created, False if it already exists
        """
        try:
            await self.redis.xgroup_create(
                name=stream,
                groupname=group,
                id=start_id,
                mkstream=mkstream
            )
            self.logger.info(f"Created consumer group '{group}' for stream '{stream}'")
            return True
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                self.logger.debug(f"Consumer group '{group}' already exists for '{stream}'")
                return False
            else:
                self.logger.error(f"Failed to create consumer group: {e}")
                raise
    
    async def delete_group(self, stream: str, group: str) -> bool:
        """
        Delete a consumer group.
        
        Args:
            stream: Stream name
            group: Consumer group name
        
        Returns:
            True if group was deleted, False if it didn't exist
        """
        try:
            result = await self.redis.xgroup_destroy(stream, group)
            if result:
                self.logger.info(f"Deleted consumer group '{group}' from stream '{stream}'")
            return bool(result)
        except ResponseError as e:
            self.logger.error(f"Failed to delete consumer group: {e}")
            return False
    
    async def list_groups(self, stream: str) -> list[dict]:
        """
        List all consumer groups for a stream.
        
        Args:
            stream: Stream name
        
        Returns:
            List of consumer group information dictionaries
        """
        try:
            groups = await self.redis.xinfo_groups(stream)
            return groups
        except ResponseError:
            return []
    
    async def list_consumers(self, stream: str, group: str) -> list[dict]:
        """
        List all consumers in a consumer group.
        
        Args:
            stream: Stream name
            group: Consumer group name
        
        Returns:
            List of consumer information dictionaries
        """
        try:
            consumers = await self.redis.xinfo_consumers(stream, group)
            return consumers
        except ResponseError:
            return []
    
    def register_consumer(
        self,
        consumer_id: str,
        group_name: str,
        stream_name: str,
        event_types: list[EventType] | None = None
    ) -> None:
        """
        Register a consumer for tracking.
        
        Args:
            consumer_id: Unique consumer identifier
            group_name: Consumer group name
            stream_name: Stream name
            event_types: Optional list of event types to filter
        """
        if consumer_id in self.consumers:
            self.logger.warning(f"Consumer '{consumer_id}' already registered")
            return
        
        consumer_info = ConsumerInfo(
            consumer_id=consumer_id,
            group_name=group_name,
            stream_name=stream_name,
            event_types=event_types,
            started_at=datetime.utcnow(),
            is_active=True,
        )
        
        self.consumers[consumer_id] = consumer_info
        self.logger.info(f"Registered consumer '{consumer_id}' in group '{group_name}'")
    
    def unregister_consumer(self, consumer_id: str) -> None:
        """
        Unregister a consumer.
        
        Args:
            consumer_id: Consumer identifier
        """
        if consumer_id in self.consumers:
            del self.consumers[consumer_id]
            self.logger.info(f"Unregistered consumer '{consumer_id}'")
        else:
            self.logger.warning(f"Consumer '{consumer_id}' not found")
    
    def get_consumer_info(self, consumer_id: str) -> ConsumerInfo | None:
        """
        Get information about a consumer.
        
        Args:
            consumer_id: Consumer identifier
        
        Returns:
            ConsumerInfo if found, None otherwise
        """
        return self.consumers.get(consumer_id)
    
    def update_consumer_stats(
        self,
        consumer_id: str,
        messages_processed: int = 0,
        errors: int = 0
    ) -> None:
        """
        Update consumer statistics.
        
        Args:
            consumer_id: Consumer identifier
            messages_processed: Number of messages processed
            errors: Number of errors encountered
        """
        if consumer_id in self.consumers:
            consumer = self.consumers[consumer_id]
            consumer.messages_processed += messages_processed
            consumer.errors += errors
    
    def mark_consumer_inactive(self, consumer_id: str) -> None:
        """
        Mark a consumer as inactive.
        
        Args:
            consumer_id: Consumer identifier
        """
        if consumer_id in self.consumers:
            self.consumers[consumer_id].is_active = False
            self.logger.info(f"Marked consumer '{consumer_id}' as inactive")
    
    def get_active_consumers(self, group_name: str | None = None) -> list[ConsumerInfo]:
        """
        Get all active consumers.
        
        Args:
            group_name: Optional group name to filter by
        
        Returns:
            List of active consumer information
        """
        consumers = [
            c for c in self.consumers.values()
            if c.is_active
        ]
        
        if group_name:
            consumers = [c for c in consumers if c.group_name == group_name]
        
        return consumers
    
    async def get_pending_messages(
        self,
        stream: str,
        group: str,
        consumer: str | None = None
    ) -> list[dict]:
        """
        Get pending messages for a consumer or group.
        
        Args:
            stream: Stream name
            group: Consumer group name
            consumer: Optional consumer name
        
        Returns:
            List of pending message information
        """
        try:
            if consumer:
                # Get pending for specific consumer
                pending = await self.redis.xpending_range(
                    stream,
                    group,
                    min="-",
                    max="+",
                    count=100,
                    consumername=consumer
                )
            else:
                # Get pending for entire group
                pending = await self.redis.xpending(stream, group)
            
            return pending if pending else []
        except ResponseError:
            return []
    
    async def claim_pending_messages(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int = 60000
    ) -> list:
        """
        Claim pending messages that have been idle too long.
        
        This is useful for recovering from consumer failures.
        
        Args:
            stream: Stream name
            group: Consumer group name
            consumer: Consumer name to claim messages for
            min_idle_time: Minimum idle time in milliseconds
        
        Returns:
            List of claimed messages
        """
        try:
            # Get pending messages
            pending = await self.redis.xpending_range(
                stream,
                group,
                min="-",
                max="+",
                count=100
            )
            
            if not pending:
                return []
            
            # Claim messages that are idle
            message_ids = [msg["message_id"] for msg in pending]
            claimed = await self.redis.xclaim(
                stream,
                group,
                consumer,
                min_idle_time,
                message_ids
            )
            
            if claimed:
                self.logger.info(
                    f"Claimed {len(claimed)} pending messages for consumer '{consumer}'"
                )
            
            return claimed
        except ResponseError as e:
            self.logger.error(f"Failed to claim pending messages: {e}")
            return []
    
    def get_stats(self) -> dict:
        """
        Get consumer group manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        active_consumers = [c for c in self.consumers.values() if c.is_active]
        total_processed = sum(c.messages_processed for c in self.consumers.values())
        total_errors = sum(c.errors for c in self.consumers.values())
        
        return {
            "total_consumers": len(self.consumers),
            "active_consumers": len(active_consumers),
            "total_messages_processed": total_processed,
            "total_errors": total_errors,
            "error_rate": (
                total_errors / total_processed
                if total_processed > 0
                else 0.0
            ),
        }


# Global consumer group manager instance
_manager: ConsumerGroupManager | None = None


def get_consumer_group_manager() -> ConsumerGroupManager:
    """
    Get or create the global consumer group manager.
    
    Returns:
        ConsumerGroupManager instance
    """
    global _manager
    
    if _manager is None:
        _manager = ConsumerGroupManager()
    
    return _manager


# Export public API
__all__ = [
    "ConsumerInfo",
    "ConsumerGroupManager",
    "get_consumer_group_manager",
]
