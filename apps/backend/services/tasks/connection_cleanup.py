"""
Connection Cleanup Tasks

Scheduled tasks for cleaning up unused/stale connections:
- Remove inactive connections older than 24 hours
- Clean up orphaned connection records
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.platform_connection import ConnectionStatus, PlatformConnection

logger = logging.getLogger(__name__)


async def cleanup_inactive_connections(
    db: AsyncSession, max_age_hours: int = 24, dry_run: bool = False
) -> dict:
    """
    Clean up inactive connections that were never used.

    These are connections that were initiated but never completed:
    - Status is INACTIVE
    - Created more than max_age_hours ago

    Args:
        db: Database session
        max_age_hours: Maximum age in hours for inactive connections
        dry_run: If True, only return what would be deleted without actually deleting

    Returns:
        dict with cleanup statistics
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

    try:
        # Find inactive connections older than cutoff
        query = select(PlatformConnection).where(
            PlatformConnection.status == ConnectionStatus.INACTIVE,
            PlatformConnection.created_at < cutoff_time,
        )

        result = await db.execute(query)
        stale_connections = result.scalars().all()

        stats = {
            "found": len(stale_connections),
            "deleted": 0,
            "dry_run": dry_run,
            "cutoff_time": cutoff_time.isoformat(),
            "platforms": {},
        }

        # Count by platform
        for conn in stale_connections:
            platform = conn.platform.value
            stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1

        if dry_run:
            logger.info(
                f"DRY RUN: Would delete {len(stale_connections)} inactive connections"
            )
            return stats

        if stale_connections:
            # Delete the connections
            delete_query = delete(PlatformConnection).where(
                PlatformConnection.status == ConnectionStatus.INACTIVE,
                PlatformConnection.created_at < cutoff_time,
            )

            result = await db.execute(delete_query)
            await db.commit()

            stats["deleted"] = result.rowcount
            logger.info(
                f"Deleted {stats['deleted']} inactive connections older than {max_age_hours}h"
            )

        return stats

    except Exception as e:
        logger.error(f"Failed to cleanup inactive connections: {e}")
        await db.rollback()
        raise


async def cleanup_revoked_connections(
    db: AsyncSession, max_age_days: int = 30, dry_run: bool = False
) -> dict:
    """
    Clean up revoked connections that are old.

    These are connections that were disconnected by the user.
    We keep them for some time for audit purposes.

    Args:
        db: Database session
        max_age_days: Maximum age in days for revoked connections
        dry_run: If True, only return what would be deleted

    Returns:
        dict with cleanup statistics
    """
    cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)

    try:
        query = select(PlatformConnection).where(
            PlatformConnection.status == ConnectionStatus.REVOKED,
            PlatformConnection.updated_at < cutoff_time,
        )

        result = await db.execute(query)
        old_revoked = result.scalars().all()

        stats = {
            "found": len(old_revoked),
            "deleted": 0,
            "dry_run": dry_run,
            "cutoff_time": cutoff_time.isoformat(),
        }

        if dry_run:
            logger.info(
                f"DRY RUN: Would delete {len(old_revoked)} old revoked connections"
            )
            return stats

        if old_revoked:
            delete_query = delete(PlatformConnection).where(
                PlatformConnection.status == ConnectionStatus.REVOKED,
                PlatformConnection.updated_at < cutoff_time,
            )

            result = await db.execute(delete_query)
            await db.commit()

            stats["deleted"] = result.rowcount
            logger.info(
                f"Deleted {stats['deleted']} revoked connections older than {max_age_days} days"
            )

        return stats

    except Exception as e:
        logger.error(f"Failed to cleanup revoked connections: {e}")
        await db.rollback()
        raise


async def run_daily_cleanup(db: AsyncSession) -> dict:
    """
    Run all daily cleanup tasks.

    Args:
        db: Database session

    Returns:
        dict with combined cleanup statistics
    """
    logger.info("Starting daily connection cleanup...")

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "inactive_cleanup": None,
        "revoked_cleanup": None,
    }

    try:
        # Cleanup inactive connections (24 hours)
        results["inactive_cleanup"] = await cleanup_inactive_connections(
            db, max_age_hours=24
        )

        # Cleanup revoked connections (30 days)
        results["revoked_cleanup"] = await cleanup_revoked_connections(
            db, max_age_days=30
        )

        total_deleted = results["inactive_cleanup"].get("deleted", 0) + results[
            "revoked_cleanup"
        ].get("deleted", 0)

        results["total_deleted"] = total_deleted
        logger.info(f"Daily cleanup completed. Total deleted: {total_deleted}")

    except Exception as e:
        logger.error(f"Daily cleanup failed: {e}")
        results["error"] = str(e)

    return results
