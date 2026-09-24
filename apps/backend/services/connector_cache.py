"""
Connector Cache Service

Manages lifecycle of platform connector instances to prevent resource
exhaustion from creating too many connector objects.

Features:
- Per-connection-id caching
- TTL-based expiry
- Maximum connections limit
- Automatic cleanup of stale connectors
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Type
from uuid import UUID

from integrations.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class CachedConnector:
    """
    Wrapper for a cached connector instance with metadata.
    """

    def __init__(self, connector: BaseConnector, ttl_seconds: int = 3600):
        """
        Initialize cached connector.

        Args:
            connector: The connector instance
            ttl_seconds: Time to live in seconds (default: 1 hour)
        """
        self.connector = connector
        self.created_at = datetime.now(timezone.utc)
        self.last_accessed_at = datetime.now(timezone.utc)
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """
        Check if this cached connector has expired.

        Returns:
            True if connector should be evicted
        """
        age = datetime.now(timezone.utc) - self.created_at
        return age.total_seconds() > self.ttl_seconds

    def touch(self) -> None:
        """Mark this connector as recently accessed."""
        self.last_accessed_at = datetime.now(timezone.utc)
        self.access_count += 1


class ConnectorCache:
    """
    Cache for connector instances with lifecycle management.

    Prevents creating multiple connector instances for the same connection,
    which causes resource exhaustion (Matrix connection leaks, memory bloat).

    Example:
        cache = ConnectorCache(max_size=100, default_ttl=3600)

        # Get or create connector
        connector = await cache.get_or_create(
            connection_id=conn_id,
            connector_class=WhatsAppConnector,
            credentials=creds
        )

        # Cleanup expired connectors
        await cache.cleanup_expired()
    """

    def __init__(
        self, max_size: int = 100, default_ttl: int = 3600, cleanup_interval: int = 300
    ):
        """
        Initialize connector cache.

        Args:
            max_size: Maximum number of cached connectors
            default_ttl: Default time-to-live in seconds (default: 1 hour)
            cleanup_interval: How often to run cleanup in seconds (default: 5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        # Cache storage: connection_id -> CachedConnector
        self._cache: Dict[UUID, CachedConnector] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """
        Start background cleanup task.

        Call this during application startup.
        """
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._background_cleanup())
            logger.info("Connector cache background cleanup started")

    async def stop(self) -> None:
        """
        Stop background cleanup and disconnect all cached connectors.

        Call this during application shutdown.
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Disconnect all connectors
        await self.clear()
        logger.info("Connector cache stopped and cleared")

    async def get(self, connection_id: UUID) -> Optional[BaseConnector]:
        """
        Get a cached connector by connection ID.

        Args:
            connection_id: Connection UUID

        Returns:
            Connector instance if cached and not expired, None otherwise
        """
        async with self._lock:
            cached = self._cache.get(connection_id)

            if cached is None:
                return None

            # Check if expired
            if cached.is_expired():
                # Remove expired connector
                await self._evict_connector(connection_id)
                return None

            # Touch and return
            cached.touch()
            logger.debug(
                f"Connector cache hit for {connection_id} "
                f"(access_count={cached.access_count})"
            )
            return cached.connector

    async def get_or_create(
        self,
        connection_id: UUID,
        connector_class: Type[BaseConnector],
        credentials: Dict[str, Any],
        **kwargs,
    ) -> BaseConnector:
        """
        Get cached connector or create new one if not found.

        Args:
            connection_id: Connection UUID
            connector_class: Connector class to instantiate
            credentials: Credentials dict for connector
            **kwargs: Additional kwargs for connector constructor

        Returns:
            Connector instance (cached or newly created)
        """
        # Try to get cached first
        connector = await self.get(connection_id)
        if connector is not None:
            return connector

        # Create new connector
        async with self._lock:
            # Double-check after acquiring lock (race condition)
            connector = await self.get(connection_id)
            if connector is not None:
                return connector

            # Ensure we don't exceed max size
            if len(self._cache) >= self.max_size:
                await self._evict_lru()

            # Create new connector
            logger.info(f"Creating new connector for {connection_id}")
            connector = connector_class(
                connection_id=connection_id, credentials=credentials, **kwargs
            )

            # Cache it
            cached = CachedConnector(connector, ttl_seconds=self.default_ttl)
            self._cache[connection_id] = cached

            return connector

    async def invalidate(self, connection_id: UUID) -> bool:
        """
        Invalidate (remove) a cached connector.

        Useful when credentials are rotated or connection is deleted.

        Args:
            connection_id: Connection UUID to invalidate

        Returns:
            True if connector was cached and removed, False otherwise
        """
        async with self._lock:
            return await self._evict_connector(connection_id)

    async def clear(self) -> int:
        """
        Clear all cached connectors and disconnect them.

        Returns:
            Number of connectors cleared
        """
        async with self._lock:
            count = len(self._cache)

            # Disconnect all connectors
            for connection_id in list(self._cache.keys()):
                await self._evict_connector(connection_id)

            logger.info(f"Cleared {count} connectors from cache")
            return count

    async def cleanup_expired(self) -> int:
        """
        Remove expired connectors from cache.

        Returns:
            Number of connectors removed
        """
        async with self._lock:
            expired_ids = [
                conn_id
                for conn_id, cached in self._cache.items()
                if cached.is_expired()
            ]

            for conn_id in expired_ids:
                await self._evict_connector(conn_id)

            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired connectors")

            return len(expired_ids)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (size, hit rate, etc.)
        """
        total_accesses = sum(cached.access_count for cached in self._cache.values())

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0,
            "total_accesses": total_accesses,
            "default_ttl": self.default_ttl,
            "connections": [
                {
                    "connection_id": str(conn_id),
                    "age_seconds": (
                        datetime.now(timezone.utc) - cached.created_at
                    ).total_seconds(),
                    "access_count": cached.access_count,
                    "last_accessed": cached.last_accessed_at.isoformat(),
                }
                for conn_id, cached in self._cache.items()
            ],
        }

    async def _evict_connector(self, connection_id: UUID) -> bool:
        """
        Evict a connector from cache and disconnect it.

        Must be called with _lock held.

        Args:
            connection_id: Connection UUID to evict

        Returns:
            True if evicted, False if not in cache
        """
        cached = self._cache.pop(connection_id, None)

        if cached is None:
            return False

        # Disconnect the connector
        try:
            if hasattr(cached.connector, "disconnect"):
                await cached.connector.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting connector {connection_id}: {e}")

        logger.debug(f"Evicted connector {connection_id} from cache")
        return True

    async def _evict_lru(self) -> None:
        """
        Evict least recently used connector.

        Must be called with _lock held.
        """
        if not self._cache:
            return

        # Find LRU connector
        lru_id = min(
            self._cache.keys(),
            key=lambda conn_id: self._cache[conn_id].last_accessed_at,
        )

        await self._evict_connector(lru_id)
        logger.info(f"Evicted LRU connector {lru_id} (cache full)")

    async def _background_cleanup(self) -> None:
        """
        Background task that periodically cleans up expired connectors.
        """
        logger.info(f"Background cleanup running every {self.cleanup_interval} seconds")

        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                count = await self.cleanup_expired()

                if count > 0:
                    logger.info(
                        f"Background cleanup removed {count} expired connectors"
                    )

            except asyncio.CancelledError:
                logger.info("Background cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}", exc_info=True)


# Global singleton instance
_connector_cache: Optional[ConnectorCache] = None


def get_connector_cache() -> ConnectorCache:
    """
    Get singleton connector cache instance.

    Returns:
        ConnectorCache instance
    """
    global _connector_cache
    if _connector_cache is None:
        _connector_cache = ConnectorCache(
            max_size=100,  # Max 100 cached connectors
            default_ttl=3600,  # 1 hour TTL
            cleanup_interval=300,  # Cleanup every 5 minutes
        )
    return _connector_cache
