"""
WhatsApp API Utilities

Shared helper functions for WhatsApp endpoints.
"""

from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from db.models.platform_connection import PlatformConnection, PlatformType


async def get_user_whatsapp_connection(
    connection_id: UUID,
    current_user: User,
    db: AsyncSession
) -> PlatformConnection:
    """Get and validate user's WhatsApp connection."""
    result = await db.execute(
        select(PlatformConnection)
        .where(PlatformConnection.id == connection_id)
        .where(PlatformConnection.user_id == current_user.id)
        .where(PlatformConnection.platform == PlatformType.WHATSAPP)
    )
    
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp connection not found"
        )
    
    return connection