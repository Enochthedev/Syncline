"""Shared API dependencies."""

from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db

# Re-export for convenience
__all__ = ["get_db", "AsyncSession"]
