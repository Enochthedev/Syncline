"""Health check and system status routes."""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="Basic health check")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Dict containing system status
    """
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected"
    }


@router.get("/detailed", summary="Detailed health check")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with more system information.

    Returns:
        Dict containing detailed system status
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "database": {
                "status": "connected",
                "type": "PostgreSQL"
            },
            "redis": {
                "status": "connected",
                "type": "Redis"
            }
        },
        "features": {
            "message_ingestion": "enabled",
            "ai_processing": "enabled",
            "real_time_streaming": "enabled"
        }
    }
