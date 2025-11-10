"""
Redis Client and Connection Management

This module provides Redis connection management with:
- Connection pooling
- Async context managers
- Health checks
- Automatic reconnection
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError

from config.config import settings

logger = logging.getLogger(__name__)


# Global Redis client instance
_redis_client: Redis | None = None
_connection_pool: ConnectionPool | None = None


def get_connection_pool() -> ConnectionPool:
    """
    Get or create the global Redis connection pool.
    
    Returns:
        ConnectionPool instance configured with settings
    """
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            decode_responses=True,
            encoding="utf-8",
        )
        logger.info(f"Redis connection pool created: {settings.REDIS_URL}")
    
    return _connection_pool


def get_redis_client() -> Redis:
    """
    Get or create the global Redis client.
    
    Returns:
        Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        pool = get_connection_pool()
        _redis_client = Redis(connection_pool=pool)
        logger.info("Redis client created")
    
    return _redis_client


@asynccontextmanager
async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Async context manager for Redis connections.
    
    Usage:
        async with get_redis() as redis_conn:
            await redis_conn.set("key", "value")
    
    Yields:
        Redis client instance
    """
    client = get_redis_client()
    try:
        yield client
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error: {e}")
        raise
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        raise


async def init_redis() -> None:
    """
    Initialize Redis connection and verify connectivity.
    
    This should be called during application startup.
    """
    try:
        client = get_redis_client()
        
        # Test connection with ping
        await client.ping()
        
        logger.info("Redis connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def close_redis() -> None:
    """
    Close Redis connections and dispose of the connection pool.
    
    This should be called during application shutdown.
    """
    global _redis_client, _connection_pool
    
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    
    if _connection_pool is not None:
        await _connection_pool.disconnect()
        _connection_pool = None
    
    logger.info("Redis connections closed")


async def health_check() -> bool:
    """
    Check Redis connection health.
    
    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        client = get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


# Export public API
__all__ = [
    "get_connection_pool",
    "get_redis_client",
    "get_redis",
    "init_redis",
    "close_redis",
    "health_check",
]
