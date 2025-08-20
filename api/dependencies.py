"""Shared API dependencies."""

from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from api.auth import get_current_user, get_current_active_user
from api.auth.models import User

# Re-export for convenience
__all__ = ["get_db", "AsyncSession", "get_current_user",
           "get_current_active_user", "User"]
