"""
WhatsApp Messaging Routes

Handles WhatsApp message operations, sync, and chat management.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from api.dependencies.auth import get_current_active_user
from db.models.user import User
from services.whatsapp_background_sync import get_whatsapp_background_sync_service
from services.whatsapp_message_sync import get_whatsapp_sync_service
from services.whatsapp_session_manager import get_whatsapp_session_manager
from services.whatsapp_webhook_service import get_whatsapp_webhook_service

from .utils import get_user_whatsapp_connection

router = APIRouter()


class WebhookSetupRequest(BaseModel):
    """Request to setup webhook subscription."""

    webhook_url: str


@router.get("/{connection_id}/login/status", summary="Poll Login Status")
async def poll_login_status(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Poll for login completion status."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    session_manager = get_whatsapp_session_manager()
    status_result = await session_manager.check_login_status(db, connection_id)

    if not status_result["success"]:
        raise HTTPException(status_code=500, detail=status_result["error"])

    # If just became logged in, trigger auto-sync
    auto_sync_result = None
    if status_result["logged_in"]:
        auto_sync_result = await session_manager.auto_sync_chats(db, connection_id)

    return {
        "connection_id": connection_id,
        "is_logged_in": status_result["logged_in"],
        "phone_number": status_result.get("phone"),
        "auto_sync": auto_sync_result,
        "message": (
            "Login completed" if status_result["logged_in"] else "Waiting for login"
        ),
    }


@router.post("/{connection_id}/sync", summary="Sync WhatsApp Chats")
async def sync_whatsapp_chats(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Sync WhatsApp chats and messages."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    # Check if logged in first
    session_manager = get_whatsapp_session_manager()
    status = await session_manager.check_login_status(db, connection_id)

    if not status.get("logged_in", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must be logged in to WhatsApp to sync chats",
        )

    # Perform sync
    sync_result = await session_manager.sync_chats(db, connection_id)

    return {
        "connection_id": connection_id,
        "sync_result": sync_result,
        "message": "WhatsApp chats synced successfully",
    }


@router.post("/{connection_id}/sync-after-login", summary="Manual Sync After Login")
async def sync_after_login(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Manually trigger sync after login completion."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    session_manager = get_whatsapp_session_manager()

    # Check login status first
    status = await session_manager.check_login_status(db, connection_id)
    if not status.get("logged_in", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must be logged in to WhatsApp to sync",
        )

    # Trigger auto-sync
    auto_sync_result = await session_manager.auto_sync_chats(db, connection_id)

    return {
        "connection_id": connection_id,
        "sync_result": auto_sync_result,
        "message": "Auto-sync completed after login",
    }


@router.post("/{connection_id}/cleanup", summary="Clean Up WhatsApp Data")
async def cleanup_whatsapp_data(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Clean up WhatsApp data for fresh start."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    session_manager = get_whatsapp_session_manager()

    # Logout first
    logout_result = await session_manager.logout(db, connection_id)

    # Clean up data
    cleanup_result = await session_manager.cleanup_data(db, connection_id)

    return {
        "success": cleanup_result.get("success", False),
        "messages_deleted": cleanup_result.get("messages_deleted", 0),
        "sessions_cleared": cleanup_result.get("sessions_cleared", 0),
        "message": "WhatsApp data cleaned up successfully",
    }


@router.post("/{connection_id}/messages/sync", summary="Sync Messages to Database")
async def sync_messages_to_database(
    connection_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Sync WhatsApp messages from Matrix to database."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    sync_service = get_whatsapp_sync_service()
    result = await sync_service.sync_messages_for_connection(db, connection_id, limit)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "connection_id": connection_id,
        "sync_result": result,
        "message": f"Synced {result['total_messages_synced']} messages from {result['total_rooms']} rooms",
    }


@router.post("/{connection_id}/background-sync/start", summary="Start Background Sync")
async def start_background_sync(
    connection_id: UUID,
    sync_interval: int = 300,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Start background sync for real-time message updates."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    background_sync_service = get_whatsapp_background_sync_service()
    background_tasks.add_task(
        background_sync_service.start_background_sync, sync_interval
    )

    return {
        "success": True,
        "connection_id": connection_id,
        "sync_interval": sync_interval,
        "message": "Background sync started",
    }


@router.post("/{connection_id}/webhook/setup", summary="Setup Webhook")
async def setup_webhook(
    connection_id: UUID,
    request: WebhookSetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Setup webhook for real-time message delivery."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    webhook_service = get_whatsapp_webhook_service()
    result = await webhook_service.setup_webhook_subscription(
        connection_id, request.webhook_url
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/webhook/matrix", summary="Matrix Webhook Handler")
async def handle_matrix_webhook(
    webhook_data: Dict[str, Any],
    db: AsyncSession = Depends(get_database_session),
):
    """Handle Matrix webhooks for real-time message processing."""
    webhook_service = get_whatsapp_webhook_service()
    result = await webhook_service.handle_matrix_webhook(db, webhook_data)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return result
