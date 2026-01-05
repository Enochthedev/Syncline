"""
Async Database Session Management

This module provides async database session management with:
- Connection pooling
- Async context managers
- Dependency injection for FastAPI
- Transaction management
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from config.config import settings

logger = logging.getLogger(__name__)


# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global async database engine.
    
    Returns:
        AsyncEngine instance configured with connection pooling
    """
    global _engine
    
    if _engine is None:
        # Determine pool class based on environment
        pool_class = NullPool if settings.ENV == "test" else QueuePool
        
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            poolclass=pool_class,
        )
        
        logger.info(
            f"Database engine created: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}"
        )
    
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the global session factory.
    
    Returns:
        Async session factory for creating database sessions
    """
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Session factory created")
    
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Usage:
        async with get_session() as session:
            result = await session.execute(query)
    
    Yields:
        AsyncSession instance
    """
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage in FastAPI routes:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Yields:
        AsyncSession instance
    """
    async with get_session() as session:
        yield session


async def init_db() -> None:
    """
    Initialize database connection, run migrations, and verify connectivity.
    
    This should be called during application startup.
    """
    try:
        engine = get_engine()
        
        # Test connection
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        
        logger.info("Database connection initialized successfully")
        
        # Run migrations automatically
        await run_migrations()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def run_migrations() -> None:
    """
    Run database migrations using Alembic.
    
    This runs 'alembic upgrade head' programmatically.
    """
    import asyncio
    from alembic import command
    from alembic.config import Config
    import os
    
    try:
        # Get the directory containing this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini = os.path.join(base_dir, "alembic.ini")
        
        if not os.path.exists(alembic_ini):
            logger.warning(f"alembic.ini not found at {alembic_ini}, skipping migrations")
            return
        
        # Create Alembic config
        alembic_cfg = Config(alembic_ini)
        
        # Run migrations in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: command.upgrade(alembic_cfg, "head")
        )
        
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.warning(f"Migration check/run encountered an issue: {e}")
        # Don't fail startup if migrations have issues - they might already be applied


async def close_db() -> None:
    """
    Close database connections and dispose of the engine.
    
    This should be called during application shutdown.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")


# Export public API
__all__ = [
    "get_engine",
    "get_session_factory",
    "get_session",
    "get_db",
    "init_db",
    "close_db",
]
