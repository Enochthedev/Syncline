"""
System Statistics API

Provides comprehensive system statistics:
- Message processing statistics
- Platform connection stats
- AI processing stats
- Performance metrics
- Storage statistics
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from db.models.attachment import Attachment
from db.models.collection_job import CollectionJob, CollectionJobStatus
from db.models.embedding import Embedding
from db.models.entity import Entity
from db.models.message import Message
from db.models.platform_connection import PlatformConnection
from db.models.raw_message import RawMessage
from db.models.summary import Summary
from services.realtime.websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()

__all__ = ["router"]


# =============================================================================
# Response Models
# =============================================================================


class SystemStats(BaseModel):
    """Comprehensive system statistics."""

    # Message stats
    total_messages: int = Field(..., description="Total normalized messages")
    total_raw_messages: int = Field(..., description="Total raw messages")
    messages_last_24h: int = Field(..., description="Messages collected in last 24h")
    messages_last_7d: int = Field(..., description="Messages collected in last 7 days")
    processing_rate: float = Field(..., description="Message processing rate (%)")

    # Platform stats
    total_connections: int = Field(..., description="Total platform connections")
    active_connections: int = Field(..., description="Active platform connections")
    connections_by_platform: dict[str, int] = Field(
        ..., description="Connections per platform"
    )
    messages_by_platform: dict[str, int] = Field(
        ..., description="Messages per platform"
    )

    # Collection stats
    total_collection_jobs: int = Field(..., description="Total collection jobs")
    active_jobs: int = Field(..., description="Active collection jobs")
    completed_jobs: int = Field(..., description="Completed collection jobs")
    failed_jobs: int = Field(..., description="Failed collection jobs")

    # AI processing stats
    total_embeddings: int = Field(..., description="Total message embeddings")
    total_entities: int = Field(..., description="Total extracted entities")
    total_summaries: int = Field(..., description="Total generated summaries")
    ai_processing_rate: float = Field(..., description="AI processing rate (%)")

    # Storage stats
    total_attachments: int = Field(..., description="Total attachments")
    total_storage_bytes: int = Field(
        ..., description="Total attachment storage in bytes"
    )

    # Real-time stats
    active_websocket_connections: int = Field(
        ..., description="Active WebSocket connections"
    )

    # Timestamps
    oldest_message: datetime | None = Field(
        None, description="Oldest message timestamp"
    )
    newest_message: datetime | None = Field(
        None, description="Newest message timestamp"
    )
    last_updated: datetime = Field(..., description="Stats last updated timestamp")


class PlatformStats(BaseModel):
    """Platform-specific statistics."""

    platform: str
    total_connections: int
    active_connections: int
    total_messages: int
    messages_last_24h: int
    last_collection: datetime | None
    collection_health: str  # healthy, degraded, unhealthy


# =============================================================================
# Stats Endpoints
# =============================================================================


@router.get(
    "",
    response_model=SystemStats,
    summary="Get System Statistics",
    description="Get comprehensive system-wide statistics",
)
async def get_system_stats(
    db: AsyncSession = Depends(get_database_session),
) -> SystemStats:
    """
    Get comprehensive system statistics.

    Returns statistics about:
    - Message processing
    - Platform connections
    - Collection jobs
    - AI processing
    - Storage usage
    - Real-time connections

    Args:
        db: Database session

    Returns:
        SystemStats: Comprehensive system statistics
    """
    try:
        logger.info("Generating system statistics")

        # Message stats
        total_messages_query = select(func.count(Message.id))
        total_messages_result = await db.execute(total_messages_query)
        total_messages = total_messages_result.scalar() or 0

        total_raw_query = select(func.count(RawMessage.id))
        total_raw_result = await db.execute(total_raw_query)
        total_raw_messages = total_raw_result.scalar() or 0

        # Messages in last 24h
        last_24h = datetime.utcnow() - timedelta(hours=24)
        messages_24h_query = select(func.count(Message.id)).where(
            Message.collected_at >= last_24h
        )
        messages_24h_result = await db.execute(messages_24h_query)
        messages_last_24h = messages_24h_result.scalar() or 0

        # Messages in last 7 days
        last_7d = datetime.utcnow() - timedelta(days=7)
        messages_7d_query = select(func.count(Message.id)).where(
            Message.collected_at >= last_7d
        )
        messages_7d_result = await db.execute(messages_7d_query)
        messages_last_7d = messages_7d_result.scalar() or 0

        # Processing rate
        processing_rate = (
            (total_messages / total_raw_messages * 100)
            if total_raw_messages > 0
            else 0.0
        )

        # Connection stats
        total_conn_query = select(func.count(PlatformConnection.id))
        total_conn_result = await db.execute(total_conn_query)
        total_connections = total_conn_result.scalar() or 0

        active_conn_query = select(func.count(PlatformConnection.id)).where(
            PlatformConnection.status == "active"
        )
        active_conn_result = await db.execute(active_conn_query)
        active_connections = active_conn_result.scalar() or 0

        # Connections by platform
        conn_by_platform_query = select(
            PlatformConnection.platform, func.count(PlatformConnection.id)
        ).group_by(PlatformConnection.platform)
        conn_by_platform_result = await db.execute(conn_by_platform_query)
        connections_by_platform = {
            row[0]: row[1] for row in conn_by_platform_result.all()
        }

        # Messages by platform
        msg_by_platform_query = select(
            Message.platform, func.count(Message.id)
        ).group_by(Message.platform)
        msg_by_platform_result = await db.execute(msg_by_platform_query)
        messages_by_platform = {row[0]: row[1] for row in msg_by_platform_result.all()}

        # Collection job stats
        total_jobs_query = select(func.count(CollectionJob.id))
        total_jobs_result = await db.execute(total_jobs_query)
        total_collection_jobs = total_jobs_result.scalar() or 0

        active_jobs_query = select(func.count(CollectionJob.id)).where(
            CollectionJob.status == CollectionJobStatus.RUNNING
        )
        active_jobs_result = await db.execute(active_jobs_query)
        active_jobs = active_jobs_result.scalar() or 0

        completed_jobs_query = select(func.count(CollectionJob.id)).where(
            CollectionJob.status == CollectionJobStatus.COMPLETED
        )
        completed_jobs_result = await db.execute(completed_jobs_query)
        completed_jobs = completed_jobs_result.scalar() or 0

        failed_jobs_query = select(func.count(CollectionJob.id)).where(
            CollectionJob.status == CollectionJobStatus.FAILED
        )
        failed_jobs_result = await db.execute(failed_jobs_query)
        failed_jobs = failed_jobs_result.scalar() or 0

        # AI processing stats
        total_embeddings_query = select(func.count(Embedding.id))
        total_embeddings_result = await db.execute(total_embeddings_query)
        total_embeddings = total_embeddings_result.scalar() or 0

        total_entities_query = select(func.count(Entity.id))
        total_entities_result = await db.execute(total_entities_query)
        total_entities = total_entities_result.scalar() or 0

        total_summaries_query = select(func.count(Summary.id))
        total_summaries_result = await db.execute(total_summaries_query)
        total_summaries = total_summaries_result.scalar() or 0

        # AI processing rate (messages with embeddings / total messages)
        ai_processing_rate = (
            (total_embeddings / total_messages * 100) if total_messages > 0 else 0.0
        )

        # Storage stats
        total_attachments_query = select(func.count(Attachment.id))
        total_attachments_result = await db.execute(total_attachments_query)
        total_attachments = total_attachments_result.scalar() or 0

        total_storage_query = select(func.coalesce(func.sum(Attachment.size_bytes), 0))
        total_storage_result = await db.execute(total_storage_query)
        total_storage_bytes = total_storage_result.scalar() or 0

        # Real-time stats
        ws_manager = get_websocket_manager()
        active_websocket_connections = ws_manager.get_connection_count()

        # Timestamp stats
        oldest_msg_query = select(func.min(Message.timestamp))
        oldest_msg_result = await db.execute(oldest_msg_query)
        oldest_message = oldest_msg_result.scalar()

        newest_msg_query = select(func.max(Message.timestamp))
        newest_msg_result = await db.execute(newest_msg_query)
        newest_message = newest_msg_result.scalar()

        return SystemStats(
            total_messages=total_messages,
            total_raw_messages=total_raw_messages,
            messages_last_24h=messages_last_24h,
            messages_last_7d=messages_last_7d,
            processing_rate=round(processing_rate, 2),
            total_connections=total_connections,
            active_connections=active_connections,
            connections_by_platform=connections_by_platform,
            messages_by_platform=messages_by_platform,
            total_collection_jobs=total_collection_jobs,
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            total_embeddings=total_embeddings,
            total_entities=total_entities,
            total_summaries=total_summaries,
            ai_processing_rate=round(ai_processing_rate, 2),
            total_attachments=total_attachments,
            total_storage_bytes=total_storage_bytes,
            active_websocket_connections=active_websocket_connections,
            oldest_message=oldest_message,
            newest_message=newest_message,
            last_updated=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to generate system stats: {e}")
        raise


@router.get(
    "/platform/{platform}",
    response_model=PlatformStats,
    summary="Get Platform Statistics",
    description="Get statistics for a specific platform",
)
async def get_platform_stats(
    platform: str,
    db: AsyncSession = Depends(get_database_session),
) -> PlatformStats:
    """
    Get platform-specific statistics.

    Args:
        platform: Platform name (gmail, slack, discord, etc.)
        db: Database session

    Returns:
        PlatformStats: Platform statistics
    """
    try:
        logger.info(f"Generating stats for platform: {platform}")

        # Connection stats
        total_conn_query = select(func.count(PlatformConnection.id)).where(
            PlatformConnection.platform == platform
        )
        total_conn_result = await db.execute(total_conn_query)
        total_connections = total_conn_result.scalar() or 0

        active_conn_query = select(func.count(PlatformConnection.id)).where(
            and_(
                PlatformConnection.platform == platform,
                PlatformConnection.status == "active",
            )
        )
        active_conn_result = await db.execute(active_conn_query)
        active_connections = active_conn_result.scalar() or 0

        # Message stats
        total_msg_query = select(func.count(Message.id)).where(
            Message.platform == platform
        )
        total_msg_result = await db.execute(total_msg_query)
        total_messages = total_msg_result.scalar() or 0

        # Messages in last 24h
        last_24h = datetime.utcnow() - timedelta(hours=24)
        msg_24h_query = select(func.count(Message.id)).where(
            and_(Message.platform == platform, Message.collected_at >= last_24h)
        )
        msg_24h_result = await db.execute(msg_24h_query)
        messages_last_24h = msg_24h_result.scalar() or 0

        # Last collection time
        last_collection_query = select(func.max(Message.collected_at)).where(
            Message.platform == platform
        )
        last_collection_result = await db.execute(last_collection_query)
        last_collection = last_collection_result.scalar()

        # Health status
        if not last_collection:
            collection_health = "unhealthy"
        elif (datetime.utcnow() - last_collection).total_seconds() > 3600:  # 1 hour
            collection_health = "degraded"
        else:
            collection_health = "healthy"

        return PlatformStats(
            platform=platform,
            total_connections=total_connections,
            active_connections=active_connections,
            total_messages=total_messages,
            messages_last_24h=messages_last_24h,
            last_collection=last_collection,
            collection_health=collection_health,
        )

    except Exception as e:
        logger.error(f"Failed to generate platform stats: {e}")
        raise
