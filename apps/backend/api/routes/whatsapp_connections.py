"""
WhatsApp Connection Management API

Handles WhatsApp-specific connection management:
- Check for existing connections
- Prevent duplicate connections
- Connection reuse logic
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from api.dependencies.auth import get_current_active_user
from config.config import settings
from db.models.platform_connection import (
    ConnectionStatus,
    PlatformConnection,
    PlatformType,
)
from db.models.user import User
from services.whatsapp_connection_manager import get_whatsapp_connection_manager

router = APIRouter()


class WhatsAppConnectionCheckResponse(BaseModel):
    """Response for WhatsApp connection check."""

    connection_id: str | None
    is_existing: bool
    is_logged_in: bool
    phone: str | None = None
    message: str
    error: str | None = None


@router.get("/check-existing", response_model=WhatsAppConnectionCheckResponse)
async def check_existing_whatsapp_connection(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
) -> WhatsAppConnectionCheckResponse:
    """
    Check for existing WhatsApp connections for the current user.

    This prevents the mobile app from creating duplicate connections
    by checking for existing active connections first.

    Returns:
        Connection info if exists, or indication that new connection is needed
    """
    connection_manager = get_whatsapp_connection_manager()

    result = await connection_manager.get_or_create_connection(db, current_user.id)

    return WhatsAppConnectionCheckResponse(
        connection_id=result.get("connection_id"),
        is_existing=result.get("is_existing", False),
        is_logged_in=result.get("is_logged_in", False),
        phone=result.get("phone"),
        message=result.get("message", ""),
        error=result.get("error"),
    )


@router.get("/list", summary="List User's WhatsApp Connections")
async def list_whatsapp_connections(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """List all WhatsApp connections for the current user."""
    connection_manager = get_whatsapp_connection_manager()

    connections = await connection_manager.list_user_connections(db, current_user.id)

    return {"connections": connections, "total": len(connections)}


@router.post("/cleanup-old", summary="Clean Up Old Connections")
async def cleanup_old_whatsapp_connections(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Clean up old WhatsApp connections for the current user."""
    connection_manager = get_whatsapp_connection_manager()

    # This will be called internally by get_or_create_connection
    # but we can also expose it as a manual cleanup endpoint
    await connection_manager._cleanup_old_connections(db, current_user.id)

    return {"success": True, "message": "Old connections cleaned up"}


@router.post("/create", summary="Create WhatsApp Connection")
async def create_whatsapp_connection(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Create a new WhatsApp connection for the current user.

    This creates a connection record with default Matrix credentials
    from environment variables.
    """
    from uuid import uuid4

    from config.config import settings

    # Create new connection with default credentials
    connection = PlatformConnection(
        id=uuid4(),
        user_id=current_user.id,
        platform=PlatformType.WHATSAPP,
        status=ConnectionStatus.INACTIVE,
        credentials={
            "matrix_homeserver_url": settings.MATRIX_HOMESERVER_URL,
            "matrix_access_token": settings.MATRIX_ACCESS_TOKEN,
            "matrix_user_id": settings.MATRIX_USER_ID,
            "bridge_bot_id": settings.WHATSAPP_BRIDGE_BOT_ID,
        },
        platform_metadata={},
    )

    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    return {
        "success": True,
        "connection_id": str(connection.id),
        "message": "WhatsApp connection created",
    }
