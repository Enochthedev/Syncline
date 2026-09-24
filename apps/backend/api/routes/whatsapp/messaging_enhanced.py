"""
Enhanced WhatsApp Messaging API Routes

Provides improved endpoints with:
- Enhanced sync with retry logic
- Comprehensive diagnostics
- Better error handling
- Room discovery with retry
- Sync status monitoring
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.dependencies import get_current_user
from db.models.platform_connection import PlatformConnection
from db.models.user import User
from db.session import get_session
from integrations.whatsapp_connector import WhatsAppConnector
from services.whatsapp_sync_enhanced import whatsapp_sync_enhanced

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Request/Response Models
# =============================================================================


class EnhancedSyncRequest(BaseModel):
    """Enhanced sync request parameters"""

    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum messages to sync per room"
    )
    force: bool = Field(default=False, description="Force sync even if recently synced")
    max_retries: int = Field(
        default=5, ge=1, le=10, description="Maximum retry attempts"
    )
    base_delay: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Base delay between retries"
    )


class RoomDiscoveryRequest(BaseModel):
    """Room discovery request parameters"""

    wait_time: int = Field(
        default=10, ge=1, le=60, description="Time to wait for rooms to appear"
    )
    max_attempts: int = Field(
        default=3, ge=1, le=5, description="Maximum discovery attempts"
    )


class BridgeSyncRequest(BaseModel):
    """Bridge sync request parameters"""

    timeout: int = Field(
        default=30, ge=5, le=120, description="Bridge operation timeout"
    )
    force_reconnect: bool = Field(
        default=False, description="Force bridge reconnection"
    )


class SyncResponse(BaseModel):
    """Sync operation response"""

    success: bool
    connection_id: str
    total_messages_synced: int = 0
    total_rooms_processed: int = 0
    stats: Dict[str, Any] = {}
    message: Optional[str] = None
    error: Optional[str] = None


class StatusResponse(BaseModel):
    """Connection status response"""

    connection_id: str
    status: str
    last_sync_at: Optional[str] = None
    total_messages: int = 0
    is_syncing: bool = False
    platform: str = "whatsapp"


class DiagnosticsResponse(BaseModel):
    """Diagnostics response"""

    connection_id: str
    bridge_connected: bool = False
    logged_in: bool = False
    rooms_count: int = 0
    messages_count: int = 0
    last_error: Optional[str] = None
    recommendations: List[str] = []


# =============================================================================
# Helper Functions
# =============================================================================


async def get_whatsapp_connection(
    connection_id: UUID, user: User
) -> PlatformConnection:
    """Get WhatsApp connection for user"""
    async with get_session() as session:
        result = await session.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == connection_id,
                PlatformConnection.user_id == user.id,
                PlatformConnection.platform == "WHATSAPP",
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=404, detail=f"WhatsApp connection {connection_id} not found"
            )

        return connection


# =============================================================================
# Enhanced Sync Endpoints
# =============================================================================


@router.post("/{connection_id}/sync/enhanced", response_model=SyncResponse)
async def sync_messages_enhanced(
    connection_id: UUID,
    request: EnhancedSyncRequest,
    user: User = Depends(get_current_user),
):
    """
    Enhanced message sync with retry logic and comprehensive statistics

    Features:
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Detailed sync statistics
    - Race condition prevention
    - Bridge timeout handling
    """
    try:
        # Verify connection exists and belongs to user
        await get_whatsapp_connection(connection_id, user)

        # Execute enhanced sync
        result = await whatsapp_sync_enhanced.sync_messages_enhanced(
            connection_id=connection_id,
            limit=request.limit,
            force=request.force,
            max_retries=request.max_retries,
            base_delay=request.base_delay,
        )

        return SyncResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced sync failed for {connection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{connection_id}/sync/status", response_model=StatusResponse)
async def get_sync_status(connection_id: UUID, user: User = Depends(get_current_user)):
    """
    Get current sync status for a WhatsApp connection

    Returns:
    - Connection status
    - Last sync time
    - Message counts
    - Whether sync is currently running
    """
    try:
        # Verify connection exists and belongs to user
        await get_whatsapp_connection(connection_id, user)

        # Get sync status
        status = await whatsapp_sync_enhanced.get_sync_status(connection_id)

        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])

        return StatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync status for {connection_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync status: {str(e)}"
        )


# =============================================================================
# Room Discovery Endpoints
# =============================================================================


@router.post("/{connection_id}/rooms/discover")
async def discover_rooms_enhanced(
    connection_id: UUID,
    request: RoomDiscoveryRequest,
    user: User = Depends(get_current_user),
):
    """
    Enhanced room discovery with retry logic

    Features:
    - Multiple discovery attempts
    - Configurable wait times
    - Better error handling
    """
    try:
        # Verify connection exists and belongs to user
        connection = await get_whatsapp_connection(connection_id, user)

        # Execute enhanced room discovery
        result = await whatsapp_sync_enhanced.discover_rooms_enhanced(
            connection_id=connection_id,
            wait_time=request.wait_time,
            max_attempts=request.max_attempts,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Room discovery failed for {connection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Room discovery failed: {str(e)}")


@router.get("/{connection_id}/rooms")
async def get_rooms(connection_id: UUID, user: User = Depends(get_current_user)):
    """Get all WhatsApp rooms for a connection"""
    try:
        # Verify connection exists and belongs to user
        connection = await get_whatsapp_connection(connection_id, user)

        # Create connector and get rooms
        connector = WhatsAppConnector(connection_id, connection.credentials)

        try:
            await connector.connect()
            rooms = await connector.get_rooms()

            return {
                "success": True,
                "connection_id": str(connection_id),
                "rooms_count": len(rooms),
                "rooms": rooms,
            }

        finally:
            try:
                await connector.disconnect()
            except Exception as e:
                logger.debug(f"Failed to disconnect connector during cleanup: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rooms for {connection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rooms: {str(e)}")


# =============================================================================
# Bridge Management Endpoints
# =============================================================================


@router.post("/{connection_id}/bridge/sync")
async def sync_bridge(
    connection_id: UUID,
    request: BridgeSyncRequest,
    user: User = Depends(get_current_user),
):
    """
    Force bridge synchronization

    Use when bridge seems stuck or unresponsive
    """
    try:
        # Verify connection exists and belongs to user
        connection = await get_whatsapp_connection(connection_id, user)

        # Create connector
        connector = WhatsAppConnector(connection_id, connection.credentials)

        try:
            await connector.connect()

            # Force bridge sync
            result = await connector.sync_bridge(
                timeout=request.timeout, force_reconnect=request.force_reconnect
            )

            return {
                "success": True,
                "connection_id": str(connection_id),
                "bridge_synced": True,
                "message": "Bridge sync completed successfully",
            }

        finally:
            try:
                await connector.disconnect()
            except Exception as e:
                logger.debug(f"Failed to disconnect connector during cleanup: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bridge sync failed for {connection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Bridge sync failed: {str(e)}")


# =============================================================================
# Diagnostics Endpoints
# =============================================================================


@router.get("/{connection_id}/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics(connection_id: UUID, user: User = Depends(get_current_user)):
    """
    Comprehensive diagnostics for WhatsApp connection

    Returns:
    - Bridge connectivity status
    - Login status
    - Room and message counts
    - Error information
    - Recommendations for fixes
    """
    try:
        # Verify connection exists and belongs to user
        connection = await get_whatsapp_connection(connection_id, user)

        diagnostics = {
            "connection_id": str(connection_id),
            "bridge_connected": False,
            "logged_in": False,
            "rooms_count": 0,
            "messages_count": 0,
            "last_error": None,
            "recommendations": [],
        }

        # Create connector for diagnostics
        connector = WhatsAppConnector(connection_id, connection.credentials)

        try:
            # Test bridge connection
            await connector.connect()
            diagnostics["bridge_connected"] = True

            # Check login status
            status = await connector.get_status()
            diagnostics["logged_in"] = status.get("logged_in", False)

            # Get room count
            rooms = await connector.get_rooms()
            diagnostics["rooms_count"] = len(rooms)

            # Get message count from database
            async with get_session() as session:
                from sqlalchemy import func, select

                from db.models.message import Message

                result = await session.execute(
                    select(func.count(Message.id)).where(
                        Message.connection_id == connection_id
                    )
                )
                diagnostics["messages_count"] = result.scalar() or 0

        except Exception as e:
            diagnostics["last_error"] = str(e)
        finally:
            try:
                await connector.disconnect()
            except Exception as e:
                logger.debug(f"Failed to disconnect connector during cleanup: {e}")

        # Generate recommendations
        recommendations = []

        if not diagnostics["bridge_connected"]:
            recommendations.append(
                "Bridge connection failed - check Matrix homeserver and credentials"
            )

        if not diagnostics["logged_in"]:
            recommendations.append(
                "WhatsApp not logged in - scan QR code using /login endpoint"
            )

        if diagnostics["rooms_count"] == 0:
            recommendations.append(
                "No rooms found - try room discovery or check WhatsApp account"
            )

        if diagnostics["messages_count"] == 0:
            recommendations.append("No messages synced - run enhanced sync after login")

        if diagnostics["last_error"]:
            if "auth" in diagnostics["last_error"].lower():
                recommendations.append(
                    "Authentication error - check Matrix access token"
                )
            elif "timeout" in diagnostics["last_error"].lower():
                recommendations.append("Timeout error - check bridge responsiveness")

        diagnostics["recommendations"] = recommendations

        return DiagnosticsResponse(**diagnostics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diagnostics failed for {connection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


# =============================================================================
# Background Sync Management
# =============================================================================


@router.post("/{connection_id}/background-sync/start")
async def start_background_sync(
    connection_id: UUID,
    background_tasks: BackgroundTasks,
    sync_interval: int = 300,  # 5 minutes default
    user: User = Depends(get_current_user),
):
    """
    Start background sync for a WhatsApp connection

    Args:
        sync_interval: Sync interval in seconds (minimum 60)
    """
    try:
        # Verify connection exists and belongs to user
        await get_whatsapp_connection(connection_id, user)

        if sync_interval < 60:
            raise HTTPException(
                status_code=400, detail="Sync interval must be at least 60 seconds"
            )

        # Add background sync task
        background_tasks.add_task(_background_sync_task, connection_id, sync_interval)

        return {
            "success": True,
            "connection_id": str(connection_id),
            "sync_interval": sync_interval,
            "message": f"Background sync started with {sync_interval}s interval",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start background sync for {connection_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start background sync: {str(e)}"
        )


async def _background_sync_task(connection_id: UUID, sync_interval: int):
    """Background sync task"""
    logger.info(
        f"Starting background sync for {connection_id} with {sync_interval}s interval"
    )

    while True:
        try:
            # Run enhanced sync
            result = await whatsapp_sync_enhanced.sync_messages_enhanced(
                connection_id=connection_id,
                limit=50,  # Smaller limit for background sync
                force=False,
                max_retries=3,  # Fewer retries for background
            )

            if result["success"]:
                logger.info(
                    f"Background sync completed: {result['total_messages_synced']} messages"
                )
            else:
                logger.warning(f"Background sync failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Background sync error: {e}")

        # Wait for next sync
        await asyncio.sleep(sync_interval)
