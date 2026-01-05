"""
Health Check API Endpoints

Provides health monitoring for:
- Overall system health
- Database connectivity
- Redis connectivity
- Stage-specific health checks
- System statistics
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session, get_settings
from config.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class HealthStatus(BaseModel):
    """Health status response model."""
    
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(default="1.0.0", description="API version")
    environment: str = Field(..., description="Environment name")


class ComponentHealth(BaseModel):
    """Individual component health status."""
    
    name: str = Field(..., description="Component name")
    status: str = Field(..., description="Component status")
    message: str | None = Field(None, description="Status message")
    latency_ms: float | None = Field(None, description="Response latency in milliseconds")


class DetailedHealthStatus(HealthStatus):
    """Detailed health status with component checks."""
    
    components: list[ComponentHealth] = Field(default_factory=list, description="Component health")
    uptime_seconds: float | None = Field(None, description="System uptime in seconds")


class SystemStats(BaseModel):
    """System statistics response model."""
    
    database: Dict[str, Any] = Field(default_factory=dict, description="Database statistics")
    redis: Dict[str, Any] = Field(default_factory=dict, description="Redis statistics")
    api: Dict[str, Any] = Field(default_factory=dict, description="API statistics")


# =============================================================================
# Health Check Endpoints
# =============================================================================

@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Overall System Health",
    description="Check overall system health status"
)
async def health_check(
    settings: Settings = Depends(get_settings)
) -> HealthStatus:
    """
    Basic health check endpoint.
    
    Returns:
        HealthStatus: Overall system health
    """
    return HealthStatus(
        status="healthy",
        environment=settings.ENV,
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    summary="Detailed System Health",
    description="Check detailed health status of all components"
)
async def detailed_health_check(
    db: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings)
) -> DetailedHealthStatus:
    """
    Detailed health check with component status.
    
    Args:
        db: Database session
        settings: Application settings
        
    Returns:
        DetailedHealthStatus: Detailed health information
    """
    components = []
    overall_status = "healthy"
    
    # Check database
    db_health = await check_database_health(db)
    components.append(db_health)
    if db_health.status != "healthy":
        overall_status = "degraded"
    
    # Check Redis (TODO)
    redis_health = ComponentHealth(
        name="redis",
        status="unknown",
        message="Redis health check not implemented yet"
    )
    components.append(redis_health)
    
    # Check event bus (TODO)
    event_bus_health = ComponentHealth(
        name="event_bus",
        status="unknown",
        message="Event bus health check not implemented yet"
    )
    components.append(event_bus_health)
    
    return DetailedHealthStatus(
        status=overall_status,
        environment=settings.ENV,
        components=components,
    )


@router.get(
    "/health/database",
    response_model=ComponentHealth,
    summary="Database Health",
    description="Check database connectivity and health"
)
async def database_health(
    db: AsyncSession = Depends(get_database_session)
) -> ComponentHealth:
    """
    Check database health.
    
    Args:
        db: Database session
        
    Returns:
        ComponentHealth: Database health status
        
    Raises:
        HTTPException: If database is unhealthy
    """
    health = await check_database_health(db)
    
    if health.status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health.message
        )
    
    return health


@router.get(
    "/health/redis",
    response_model=ComponentHealth,
    summary="Redis Health",
    description="Check Redis connectivity and health"
)
async def redis_health() -> ComponentHealth:
    """
    Check Redis health.
    
    Returns:
        ComponentHealth: Redis health status
    """
    # TODO: Implement Redis health check
    return ComponentHealth(
        name="redis",
        status="unknown",
        message="Redis health check not implemented yet"
    )


@router.get(
    "/health/stages/{stage}",
    response_model=ComponentHealth,
    summary="Stage-Specific Health",
    description="Check health of a specific processing stage"
)
async def stage_health(
    stage: str,
    db: AsyncSession = Depends(get_database_session)
) -> ComponentHealth:
    """
    Check health of a specific processing stage.
    
    Args:
        stage: Stage name (connection, collection, cleaning, matching, ai)
        db: Database session
        
    Returns:
        ComponentHealth: Stage health status
        
    Raises:
        HTTPException: If stage is invalid
    """
    valid_stages = ["connection", "collection", "cleaning", "matching", "ai"]
    
    if stage not in valid_stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage. Must be one of: {', '.join(valid_stages)}"
        )
    
    # TODO: Implement stage-specific health checks
    return ComponentHealth(
        name=stage,
        status="unknown",
        message=f"Health check for {stage} stage not implemented yet"
    )


@router.get(
    "/stats",
    response_model=SystemStats,
    summary="System Statistics",
    description="Get system statistics and metrics"
)
async def system_stats(
    db: AsyncSession = Depends(get_database_session)
) -> SystemStats:
    """
    Get system statistics.
    
    Args:
        db: Database session
        
    Returns:
        SystemStats: System statistics
    """
    stats = SystemStats()
    
    # Get database stats
    try:
        stats.database = await get_database_stats(db)
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        stats.database = {"error": str(e)}
    
    # TODO: Get Redis stats
    stats.redis = {"status": "not_implemented"}
    
    # TODO: Get API stats
    stats.api = {"status": "not_implemented"}
    
    return stats


# =============================================================================
# Admin Endpoints
# =============================================================================

class CleanupResponse(BaseModel):
    """Cleanup operation response."""
    
    timestamp: str = Field(description="Cleanup timestamp")
    inactive_cleanup: Dict[str, Any] = Field(default_factory=dict)
    revoked_cleanup: Dict[str, Any] = Field(default_factory=dict)
    total_deleted: int = Field(default=0)
    error: str | None = None


@router.post(
    "/admin/cleanup-connections",
    response_model=CleanupResponse,
    summary="Cleanup Stale Connections",
    description="Remove inactive and old revoked connections (admin only)"
)
async def cleanup_connections(
    db: AsyncSession = Depends(get_database_session),
    dry_run: bool = False
) -> CleanupResponse:
    """
    Clean up stale connections.
    
    Removes:
    - Inactive connections older than 24 hours
    - Revoked connections older than 30 days
    
    Args:
        db: Database session
        dry_run: If True, only return what would be deleted
        
    Returns:
        CleanupResponse: Cleanup statistics
    """
    from services.tasks.connection_cleanup import (
        cleanup_inactive_connections,
        cleanup_revoked_connections
    )
    
    result = CleanupResponse(timestamp=datetime.utcnow().isoformat())
    
    try:
        # Cleanup inactive connections (24 hours)
        result.inactive_cleanup = await cleanup_inactive_connections(
            db, max_age_hours=24, dry_run=dry_run
        )
        
        # Cleanup revoked connections (30 days)
        result.revoked_cleanup = await cleanup_revoked_connections(
            db, max_age_days=30, dry_run=dry_run
        )
        
        result.total_deleted = (
            result.inactive_cleanup.get("deleted", 0) +
            result.revoked_cleanup.get("deleted", 0)
        )
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        result.error = str(e)
    
    return result


# =============================================================================
# Helper Functions
# =============================================================================

async def check_database_health(db: AsyncSession) -> ComponentHealth:
    """
    Check database connectivity and health.
    
    Args:
        db: Database session
        
    Returns:
        ComponentHealth: Database health status
    """
    import time
    
    start_time = time.time()
    
    try:
        # Execute simple query to check connectivity
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        latency_ms = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            name="database",
            status="healthy",
            message="Database is responsive",
            latency_ms=round(latency_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        
        return ComponentHealth(
            name="database",
            status="unhealthy",
            message=f"Database error: {str(e)}"
        )


async def get_database_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Get database statistics.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Database statistics
    """
    stats = {}
    
    try:
        # Get table counts (TODO: Update with actual table names)
        # result = await db.execute(text("SELECT COUNT(*) FROM messages"))
        # stats["message_count"] = result.scalar()
        
        # Get database size
        result = await db.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        ))
        stats["database_size"] = result.scalar()
        
        # Get connection count
        result = await db.execute(text(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        ))
        stats["active_connections"] = result.scalar()
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        stats["error"] = str(e)
    
    return stats


# =============================================================================
# Collection Worker Endpoints
# =============================================================================

@router.post(
    "/collection/start",
    summary="Start Message Collection Worker",
    description="Start background message collection"
)
async def start_collection():
    """Start the background message collection worker."""
    from services.tasks.message_collection import start_collection_worker
    
    start_collection_worker(interval_seconds=30)
    
    return {
        "status": "started",
        "message": "Message collection worker started (30s interval)"
    }


@router.post(
    "/collection/stop",
    summary="Stop Message Collection Worker",
    description="Stop background message collection"
)
async def stop_collection():
    """Stop the background message collection worker."""
    from services.tasks.message_collection import stop_collection_worker
    
    stop_collection_worker()
    
    return {
        "status": "stopped",
        "message": "Message collection worker stopped"
    }


@router.post(
    "/collection/run",
    summary="Run Collection Cycle",
    description="Manually trigger a message collection cycle"
)
async def run_collection():
    """Manually run a collection cycle."""
    from services.tasks.message_collection import run_collection_cycle
    
    stats = await run_collection_cycle()
    
    return {
        "status": "completed",
        "stats": stats
    }


# =============================================================================
# Export router
# =============================================================================

__all__ = ["router"]
