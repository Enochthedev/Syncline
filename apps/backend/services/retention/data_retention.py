"""
Data Retention Policy Service

Manages data lifecycle and retention:
- Automatic cleanup of old data
- Retention policy configuration
- Archival of expired data
- Compliance with data retention laws
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.message import Message
from db.models.raw_message import RawMessage
from db.models.audit import AuditLog
from config.config import settings

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """Data retention policy configuration."""

    def __init__(
        self,
        messages_retention_days: int = 365,
        raw_messages_retention_days: int = 90,
        audit_logs_retention_days: int = 730,  # 2 years
    ):
        self.messages_retention_days = messages_retention_days
        self.raw_messages_retention_days = raw_messages_retention_days
        self.audit_logs_retention_days = audit_logs_retention_days


class DataRetentionService:
    """
    Service for managing data retention and cleanup.

    Handles:
    - Automatic deletion of expired data
    - Policy-based retention
    - Data archival
    """

    def __init__(self, policy: Optional[RetentionPolicy] = None):
        """
        Initialize data retention service.

        Args:
            policy: Retention policy (uses defaults if not provided)
        """
        self.policy = policy or RetentionPolicy()
        logger.info(f"Initialized DataRetentionService with policy: {self.policy.__dict__}")

    async def cleanup_old_messages(self, db: AsyncSession) -> int:
        """
        Delete messages older than retention period.

        Args:
            db: Database session

        Returns:
            Number of messages deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(
            days=self.policy.messages_retention_days
        )

        query = delete(Message).where(Message.timestamp < cutoff_date)
        result = await db.execute(query)
        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} messages older than {cutoff_date}")

        return deleted_count

    async def cleanup_old_raw_messages(self, db: AsyncSession) -> int:
        """
        Delete raw messages older than retention period.

        Args:
            db: Database session

        Returns:
            Number of raw messages deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(
            days=self.policy.raw_messages_retention_days
        )

        query = delete(RawMessage).where(RawMessage.collected_at < cutoff_date)
        result = await db.execute(query)
        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} raw messages older than {cutoff_date}")

        return deleted_count

    async def cleanup_old_audit_logs(self, db: AsyncSession) -> int:
        """
        Delete audit logs older than retention period.

        Args:
            db: Database session

        Returns:
            Number of audit logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(
            days=self.policy.audit_logs_retention_days
        )

        query = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
        result = await db.execute(query)
        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} audit logs older than {cutoff_date}")

        return deleted_count

    async def run_cleanup(self, db: AsyncSession) -> dict[str, int]:
        """
        Run full data retention cleanup.

        Args:
            db: Database session

        Returns:
            Dictionary with counts of deleted items
        """
        logger.info("Running data retention cleanup")

        results = {
            "messages": await self.cleanup_old_messages(db),
            "raw_messages": await self.cleanup_old_raw_messages(db),
            "audit_logs": await self.cleanup_old_audit_logs(db),
        }

        logger.info(f"Data retention cleanup completed: {results}")

        return results


# Global service instance
_retention_service: Optional[DataRetentionService] = None


def get_retention_service() -> DataRetentionService:
    """
    Get the global data retention service instance.

    Returns:
        Data retention service
    """
    global _retention_service

    if _retention_service is None:
        _retention_service = DataRetentionService()

    return _retention_service


__all__ = [
    "DataRetentionService",
    "RetentionPolicy",
    "get_retention_service",
]
