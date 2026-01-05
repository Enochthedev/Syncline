"""
WhatsApp Status Routes

Handles WhatsApp status checking and health monitoring.
"""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from api.dependencies.auth import get_current_active_user, get_optional_current_user
from db.models.user import User
from services.whatsapp_session_manager import get_whatsapp_session_manager

from .models import WhatsAppStatusResponse
from .utils import get_user_whatsapp_connection

router = APIRouter()


@router.get("/health", summary="WhatsApp Service Health")
async def whatsapp_health(
    current_user: User = Depends(get_optional_current_user)
):
    """Check WhatsApp service health (public endpoint)."""
    return {
        "service": "whatsapp",
        "status": "healthy",
        "message": "WhatsApp service is available"
    }


@router.get("/{connection_id}/status", response_model=WhatsAppStatusResponse, summary="Connection Status")
async def get_whatsapp_status(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
) -> WhatsAppStatusResponse:
    """Get WhatsApp connection status."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)
    
    session_manager = get_whatsapp_session_manager()
    status_result = await session_manager.get_bridge_status(db, connection_id)
    
    return WhatsAppStatusResponse(
        connection_id=connection_id,
        bridge_status=status_result["bridge_status"],
        is_healthy=status_result["is_healthy"]
    )