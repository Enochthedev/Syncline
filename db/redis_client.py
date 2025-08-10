"""Redis client configuration for event streaming and caching."""

import redis.asyncio as redis
from typing import Optional
from config.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper for event streaming and caching."""
    
    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Test connection
            await self._client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
        logger.info("Redis connection closed")
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self._client:
                return False
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

# Global Redis client instance
redis_client = RedisClient()

async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    return redis_client.client

async def initialize_redis() -> None:
    """Initialize Redis connection."""
    await redis_client.initialize()

async def close_redis() -> None:
    """Close Redis connection."""
    await redis_client.close()