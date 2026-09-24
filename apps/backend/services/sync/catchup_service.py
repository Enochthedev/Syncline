"""
Catch-up Sync Service

Handles synchronization of missed messages during downtime:
- Detects gaps in message collection
- Prioritizes recent messages
- Tracks sync progress
- Handles rate limiting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.collection_job import CollectionJob, CollectionJobStatus
from db.models.message import Message
from db.models.platform_connection import PlatformConnection
from services.collection_orchestrator import get_collection_orchestrator

logger = logging.getLogger(__name__)


class CatchUpSyncService:
    """
    Service for syncing missed messages.

    Handles:
    - Gap detection in message timeline
    - Priority-based sync (recent messages first)
    - Progress tracking
    - Resource management
    """

    def __init__(self):
        """Initialize catch-up sync service."""
        logger.info("Initialized CatchUpSyncService")

    async def detect_sync_gaps(
        self,
        connection_id: UUID,
        db: AsyncSession,
        lookback_days: int = 30,
    ) -> list[dict]:
        """
        Detect gaps in message collection.

        Args:
            connection_id: Platform connection ID
            db: Database session
            lookback_days: Days to look back for gaps

        Returns:
            List of detected gaps with start/end dates
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=lookback_days)

            # Get all messages for this connection, ordered by timestamp
            query = (
                select(Message)
                .where(
                    and_(
                        Message.connection_id == connection_id,
                        Message.timestamp >= start_date,
                    )
                )
                .order_by(Message.timestamp)
            )

            result = await db.execute(query)
            messages = result.scalars().all()

            if not messages:
                # No messages yet, entire period is a gap
                return [
                    {
                        "start_date": start_date,
                        "end_date": datetime.utcnow(),
                        "gap_hours": (datetime.utcnow() - start_date).total_seconds()
                        / 3600,
                    }
                ]

            # Detect gaps (periods > 1 hour without messages)
            gaps = []
            threshold = timedelta(hours=1)

            for i in range(len(messages) - 1):
                current = messages[i].timestamp
                next_msg = messages[i + 1].timestamp
                gap_duration = next_msg - current

                if gap_duration > threshold:
                    gaps.append(
                        {
                            "start_date": current,
                            "end_date": next_msg,
                            "gap_hours": gap_duration.total_seconds() / 3600,
                        }
                    )

            # Check gap from last message to now
            if messages:
                last_message = messages[-1].timestamp
                now = datetime.utcnow()
                gap_since_last = now - last_message

                if gap_since_last > threshold:
                    gaps.append(
                        {
                            "start_date": last_message,
                            "end_date": now,
                            "gap_hours": gap_since_last.total_seconds() / 3600,
                        }
                    )

            logger.info(f"Detected {len(gaps)} gaps for connection {connection_id}")
            return gaps

        except Exception as e:
            logger.error(f"Failed to detect sync gaps: {e}")
            return []

    async def sync_missed_messages(
        self,
        connection_id: UUID,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[UUID]:
        """
        Sync missed messages for a connection.

        Args:
            connection_id: Platform connection ID
            db: Database session
            start_date: Start of sync period
            end_date: End of sync period

        Returns:
            Collection job ID if sync started, None otherwise
        """
        try:
            # Get connection
            connection = await db.get(PlatformConnection, connection_id)
            if not connection:
                logger.error(f"Connection {connection_id} not found")
                return None

            # Get orchestrator
            orchestrator = get_collection_orchestrator()

            # Create collection job for catch-up
            job_id = await orchestrator.create_collection_job(
                connection_id=connection_id,
                db=db,
                start_date=start_date or (datetime.utcnow() - timedelta(days=7)),
                end_date=end_date or datetime.utcnow(),
                priority="high",  # Catch-up has high priority
                job_type="catch_up",
            )

            logger.info(
                f"Started catch-up sync for connection {connection_id}, "
                f"job {job_id}"
            )

            return job_id

        except Exception as e:
            logger.error(f"Failed to start catch-up sync: {e}")
            return None

    async def sync_all_connections(
        self,
        db: AsyncSession,
        lookback_days: int = 7,
    ) -> dict[UUID, Optional[UUID]]:
        """
        Sync all active connections.

        Args:
            db: Database session
            lookback_days: Days to sync

        Returns:
            Dictionary mapping connection IDs to job IDs
        """
        try:
            # Get all active connections
            query = select(PlatformConnection).where(
                PlatformConnection.status == "active"
            )

            result = await db.execute(query)
            connections = result.scalars().all()

            logger.info(f"Starting catch-up sync for {len(connections)} connections")

            jobs = {}

            for connection in connections:
                job_id = await self.sync_missed_messages(
                    connection_id=connection.id,
                    db=db,
                    start_date=datetime.utcnow() - timedelta(days=lookback_days),
                )

                jobs[connection.id] = job_id

                # Add small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)

            logger.info(f"Started {len([j for j in jobs.values() if j])} catch-up jobs")

            return jobs

        except Exception as e:
            logger.error(f"Failed to sync all connections: {e}")
            return {}


# Global service instance
_catchup_service: Optional[CatchUpSyncService] = None


def get_catchup_service() -> CatchUpSyncService:
    """
    Get the global catch-up sync service instance.

    Returns:
        Catch-up sync service
    """
    global _catchup_service

    if _catchup_service is None:
        _catchup_service = CatchUpSyncService()

    return _catchup_service


__all__ = [
    "CatchUpSyncService",
    "get_catchup_service",
]
