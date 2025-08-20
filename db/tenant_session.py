"""
Tenant-aware database session management for row-level security.

This module provides database sessions that automatically set the tenant context
for PostgreSQL Row-Level Security (RLS) policies.
"""

import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import uuid

from config.config import settings

logger = logging.getLogger(__name__)


class TenantAwareSession:
    """
    Tenant-aware database session that sets RLS context variables.

    This class wraps SQLAlchemy AsyncSession to automatically set
    PostgreSQL session variables for tenant isolation.
    """

    def __init__(self, session: AsyncSession, tenant_id: Optional[str] = None, is_system_admin: bool = False):
        self._session = session
        self._tenant_id = tenant_id
        self._is_system_admin = is_system_admin
        self._context_set = False

    async def __aenter__(self):
        """Set tenant context when entering the session."""
        await self._set_tenant_context()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up session when exiting."""
        await self._clear_tenant_context()
        await self._session.close()

    async def _set_tenant_context(self):
        """Set PostgreSQL session variables for RLS policies."""
        try:
            if self._tenant_id:
                # Validate tenant_id is a valid UUID
                uuid.UUID(self._tenant_id)
                await self._session.execute(
                    text("SET app.current_tenant_id = :tenant_id"),
                    {"tenant_id": self._tenant_id}
                )

            # Set system admin flag
            await self._session.execute(
                text("SET app.is_system_admin = :is_admin"),
                {"is_admin": str(self._is_system_admin).lower()}
            )

            self._context_set = True
            logger.debug(
                f"Set tenant context: tenant_id={self._tenant_id}, is_admin={self._is_system_admin}")

        except Exception as e:
            logger.error(f"Failed to set tenant context: {e}")
            raise

    async def _clear_tenant_context(self):
        """Clear PostgreSQL session variables."""
        try:
            if self._context_set:
                await self._session.execute(text("RESET app.current_tenant_id"))
                await self._session.execute(text("RESET app.is_system_admin"))
                logger.debug("Cleared tenant context")
        except Exception as e:
            logger.warning(f"Failed to clear tenant context: {e}")

    @property
    def tenant_id(self) -> Optional[str]:
        """Get the current tenant ID."""
        return self._tenant_id

    @property
    def is_system_admin(self) -> bool:
        """Check if current session is system admin."""
        return self._is_system_admin


# Create async engine and session factory
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=settings.DEBUG
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_tenant_session(
    tenant_id: Optional[str] = None,
    is_system_admin: bool = False
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a tenant-aware database session.

    Args:
        tenant_id: Tenant identifier for RLS context
        is_system_admin: Whether the session has system admin privileges

    Yields:
        AsyncSession with tenant context set
    """
    session = AsyncSessionLocal()
    tenant_session = TenantAwareSession(session, tenant_id, is_system_admin)

    try:
        async with tenant_session as db:
            yield db
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_system_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a system admin database session that bypasses RLS.

    This should only be used for system operations like migrations,
    tenant provisioning, and administrative tasks.

    Yields:
        AsyncSession with system admin privileges
    """
    async with get_tenant_session(is_system_admin=True) as session:
        yield session


async def execute_rls_setup():
    """
    Execute the RLS setup SQL file.

    This function should be called during application initialization
    to set up row-level security policies.
    """
    try:
        async with get_system_session() as session:
            # Read and execute the RLS SQL file
            with open("db/sql/row_level_security.sql", "r") as f:
                rls_sql = f.read()

            # Split by semicolon and execute each statement
            statements = [stmt.strip()
                          for stmt in rls_sql.split(';') if stmt.strip()]

            for statement in statements:
                if statement and not statement.startswith('--'):
                    await session.execute(text(statement))

            await session.commit()
            logger.info("RLS policies set up successfully")

    except Exception as e:
        logger.error(f"Failed to set up RLS policies: {e}")
        raise


class TenantSessionManager:
    """
    Manager for tenant-aware database sessions.

    Provides methods to create sessions with proper tenant context
    and manage session lifecycle.
    """

    def __init__(self):
        self._engine = engine
        self._session_factory = AsyncSessionLocal

    async def get_session(
        self,
        tenant_id: Optional[str] = None,
        is_system_admin: bool = False
    ) -> TenantAwareSession:
        """
        Create a new tenant-aware session.

        Args:
            tenant_id: Tenant identifier
            is_system_admin: System admin flag

        Returns:
            TenantAwareSession instance
        """
        session = self._session_factory()
        return TenantAwareSession(session, tenant_id, is_system_admin)

    async def execute_with_tenant(
        self,
        tenant_id: str,
        query_func,
        *args,
        **kwargs
    ):
        """
        Execute a query function with tenant context.

        Args:
            tenant_id: Tenant identifier
            query_func: Async function that takes a session as first argument
            *args: Additional arguments for query_func
            **kwargs: Additional keyword arguments for query_func

        Returns:
            Result of query_func
        """
        async with get_tenant_session(tenant_id) as session:
            return await query_func(session, *args, **kwargs)

    async def execute_as_system(
        self,
        query_func,
        *args,
        **kwargs
    ):
        """
        Execute a query function with system admin privileges.

        Args:
            query_func: Async function that takes a session as first argument
            *args: Additional arguments for query_func
            **kwargs: Additional keyword arguments for query_func

        Returns:
            Result of query_func
        """
        async with get_system_session() as session:
            return await query_func(session, *args, **kwargs)

    async def health_check(self) -> bool:
        """
        Check database connectivity and RLS setup.

        Returns:
            True if database is healthy and RLS is working
        """
        try:
            async with get_system_session() as session:
                # Test basic connectivity
                result = await session.execute(text("SELECT 1"))
                if not result.scalar():
                    return False

                # Test RLS functions exist
                result = await session.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'current_tenant_id')")
                )
                if not result.scalar():
                    logger.warning(
                        "RLS functions not found, may need to run setup")
                    return False

                return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global session manager instance
session_manager = TenantSessionManager()


# Dependency for FastAPI
async def get_tenant_db_session(
    tenant_id: Optional[str] = None,
    is_system_admin: bool = False
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for tenant-aware database sessions.

    Args:
        tenant_id: Tenant identifier (usually from JWT token or request context)
        is_system_admin: System admin flag (from JWT token)

    Yields:
        AsyncSession with tenant context
    """
    async with get_tenant_session(tenant_id, is_system_admin) as session:
        yield session
