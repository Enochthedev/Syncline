"""
WhatsApp Integration API Routes for R.E.M.I System

Provides REST endpoints for WhatsApp connection management,
user preferences, and monitoring for academic evaluation.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from integrations.whatsapp_integration_service import (
    WhatsAppIntegrationService, WhatsAppPreferences, SyncTier
)
from services.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Global service instance (would be dependency injected in production)
whatsapp_service: Optional[WhatsAppIntegrationService] = None


# Pydantic models for API
class WhatsAppConnectionRequest(BaseModel):
    """Request model for WhatsApp connection."""
    user_id: str = Field(..., description="R.E.M.I user ID")
    sync_tier: str = Field(
        default="daily_batch", description="Sync tier: real_time, hourly_batch, daily_batch")
    include_groups: bool = Field(
        default=False, description="Include group chats")
    include_dms: bool = Field(
        default=True, description="Include direct messages")
    sync_history_days: int = Field(
        default=30, description="Days of history to sync")
    auto_sync: bool = Field(default=True, description="Enable automatic sync")
    notification_keywords: list[str] = Field(
        default=[], description="Keywords for notifications")


class WhatsAppConnectionResponse(BaseModel):
    """Response model for WhatsApp connection."""
    status: str
    session_id: Optional[str] = None
    qr_code: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None
    message: str


class WhatsAppStatusResponse(BaseModel):
    """Response model for WhatsApp status."""
    status: str
    session_id: Optional[str] = None
    bridge_id: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None
    connected_at: Optional[str] = None
    last_sync: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class WhatsAppMetricsResponse(BaseModel):
    """Response model for WhatsApp metrics."""
    total_users: int
    active_connections: int
    messages_processed: int
    sync_latency_ms: float
    bridge_utilization: float
    bridge_pool_size: int
    queue_lengths: Dict[str, int]


# Dependency to get WhatsApp service
async def get_whatsapp_service() -> WhatsAppIntegrationService:
    """Get WhatsApp integration service instance."""
    global whatsapp_service
    if whatsapp_service is None:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp service not initialized"
        )
    return whatsapp_service


@router.post("/connect", response_model=WhatsAppConnectionResponse)
async def connect_whatsapp(
    request: WhatsAppConnectionRequest,
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> WhatsAppConnectionResponse:
    """
    Connect WhatsApp account for a user.

    User Experience Flow:
    1. User clicks "Connect WhatsApp" in R.E.M.I dashboard
    2. System checks bridge availability
    3. If available: Show QR code immediately
    4. If busy: Queue user with estimated wait time
    5. User scans QR with WhatsApp "Link Device"
    6. System confirms connection and starts sync
    """
    try:
        # Convert sync tier string to enum
        try:
            sync_tier = SyncTier(request.sync_tier)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sync tier: {request.sync_tier}"
            )

        # Create preferences
        preferences = WhatsAppPreferences(
            sync_tier=sync_tier,
            include_groups=request.include_groups,
            include_dms=request.include_dms,
            sync_history_days=request.sync_history_days,
            auto_sync=request.auto_sync,
            notification_keywords=request.notification_keywords
        )

        # Connect WhatsApp
        result = await service.connect_whatsapp(request.user_id, preferences)

        return WhatsAppConnectionResponse(**result)

    except Exception as e:
        logger.error(
            f"Failed to connect WhatsApp for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Connection failed: {str(e)}"
        )


@router.get("/status/{user_id}", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    user_id: str,
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> WhatsAppStatusResponse:
    """Get WhatsApp connection status for a user."""
    try:
        status = await service.get_connection_status(user_id)
        return WhatsAppStatusResponse(**status)

    except Exception as e:
        logger.error(f"Failed to get WhatsApp status for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


@router.delete("/disconnect/{user_id}")
async def disconnect_whatsapp(
    user_id: str,
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> Dict[str, str]:
    """Disconnect WhatsApp account for a user."""
    try:
        result = await service.disconnect_whatsapp(user_id)

        if result["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail="WhatsApp connection not found for user"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect WhatsApp for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Disconnection failed: {str(e)}"
        )


@router.get("/metrics", response_model=WhatsAppMetricsResponse)
async def get_whatsapp_metrics(
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> WhatsAppMetricsResponse:
    """
    Get WhatsApp integration metrics for academic evaluation.

    Performance metrics dashboard:
    - Messages processed
    - Sync latency
    - Resource usage monitoring
    - User satisfaction scoring
    - Comparison metrics
    """
    try:
        metrics = await service.get_metrics()
        return WhatsAppMetricsResponse(**metrics)

    except Exception as e:
        logger.error(f"Failed to get WhatsApp metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Metrics retrieval failed: {str(e)}"
        )


@router.post("/webhook")
async def whatsapp_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
):
    """Handle WhatsApp webhook events from Matrix bridges."""
    try:
        # Process webhook in background
        background_tasks.add_task(service.handle_webhook, payload)

        return {"status": "accepted"}

    except Exception as e:
        logger.error(f"Failed to handle WhatsApp webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/bridges/status")
async def get_bridge_status(
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> Dict[str, Any]:
    """Get status of all WhatsApp bridges in the pool."""
    try:
        bridge_status = {}
        for bridge_id, bridge in service.bridge_pool.bridges.items():
            bridge_status[bridge_id] = {
                "bridge_id": bridge_id,
                "container_id": bridge.container_id,
                "status": bridge.status,
                "assigned_user": bridge.assigned_user,
                "sync_tier": bridge.sync_tier.value,
                "created_at": bridge.created_at.isoformat(),
                "last_activity": bridge.last_activity.isoformat() if bridge.last_activity else None,
                "message_count": bridge.message_count,
                "error_count": bridge.error_count
            }

        return {
            "bridges": bridge_status,
            "total_bridges": len(bridge_status),
            "active_bridges": len([b for b in service.bridge_pool.bridges.values() if b.assigned_user]),
            "available_bridges": len([b for b in service.bridge_pool.bridges.values() if not b.assigned_user])
        }

    except Exception as e:
        logger.error(f"Failed to get bridge status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bridge status retrieval failed: {str(e)}"
        )


@router.post("/bridges/{bridge_id}/cleanup")
async def cleanup_bridge(
    bridge_id: str,
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> Dict[str, str]:
    """Clean up and recycle a specific bridge."""
    try:
        success = await service.bridge_pool.cleanup_bridge(bridge_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Bridge {bridge_id} not found or cleanup failed"
            )

        return {"status": "cleaned", "bridge_id": bridge_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup bridge {bridge_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bridge cleanup failed: {str(e)}"
        )


@router.get("/queue/status")
async def get_queue_status(
    service: WhatsAppIntegrationService = Depends(get_whatsapp_service)
) -> Dict[str, Any]:
    """Get current queue status for all sync tiers."""
    try:
        queue_status = {}
        for tier, queue in service.sync_scheduler.user_queues.items():
            queue_status[tier.value] = {
                "length": len(queue),
                "users": queue,
                "estimated_wait_per_user": 15,  # minutes
                "total_estimated_wait": len(queue) * 15
            }

        return {
            "queues": queue_status,
            "total_queued_users": sum(len(q) for q in service.sync_scheduler.user_queues.values())
        }

    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Queue status retrieval failed: {str(e)}"
        )


# Initialize service function (called from main app)
async def initialize_whatsapp_service(config: Dict[str, Any], event_bus: EventBus):
    """Initialize the global WhatsApp service instance."""
    global whatsapp_service
    try:
        whatsapp_service = WhatsAppIntegrationService(config, event_bus)
        await whatsapp_service.authenticate()
        await whatsapp_service.start_real_time_ingestion()
        logger.info("WhatsApp integration service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WhatsApp service: {e}")
        raise


# Cleanup function (called on app shutdown)
async def cleanup_whatsapp_service():
    """Cleanup the global WhatsApp service instance."""
    global whatsapp_service
    if whatsapp_service:
        try:
            await whatsapp_service.stop_real_time_ingestion()
            logger.info("WhatsApp integration service cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up WhatsApp service: {e}")
        finally:
            whatsapp_service = None
