"""System statistics routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List
import logging

from api.dependencies import get_db
from db.models.participant import Participant
from db.models.thread import Thread
from db.models.message import Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/", summary="Get system statistics")
async def get_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get basic statistics about the system.

    Returns:
        Dict containing counts of participants, threads, messages and supported platforms
    """
    try:
        # Count participants
        participants_result = await db.execute(select(func.count(Participant.id)))
        participants_count = participants_result.scalar()

        # Count threads
        threads_result = await db.execute(select(func.count(Thread.id)))
        threads_count = threads_result.scalar()

        # Count messages
        messages_result = await db.execute(select(func.count(Message.id)))
        messages_count = messages_result.scalar()

        return {
            "participants": participants_count,
            "threads": threads_count,
            "messages": messages_count,
            "platforms_supported": [
                "gmail", "slack", "discord", "whatsapp",
                "twitter", "telegram", "google_chat",
                "linkedin", "instagram"
            ]
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/platforms", summary="Get platform statistics")
async def get_platform_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get statistics broken down by platform.

    Returns:
        Dict containing platform-specific statistics
    """
    try:
        # Get participant counts by platform
        participants_by_platform = await db.execute(
            select(Participant.platform, func.count(Participant.id))
            .group_by(Participant.platform)
        )

        # Get thread counts by platform
        threads_by_platform = await db.execute(
            select(Thread.platform, func.count(Thread.id))
            .group_by(Thread.platform)
        )

        # Get message counts by platform
        messages_by_platform = await db.execute(
            select(Message.platform, func.count(Message.id))
            .group_by(Message.platform)
        )

        platform_stats = {}

        # Process participants
        for platform, count in participants_by_platform.fetchall():
            if platform not in platform_stats:
                platform_stats[platform] = {}
            platform_stats[platform]["participants"] = count

        # Process threads
        for platform, count in threads_by_platform.fetchall():
            if platform not in platform_stats:
                platform_stats[platform] = {}
            platform_stats[platform]["threads"] = count

        # Process messages
        for platform, count in messages_by_platform.fetchall():
            if platform not in platform_stats:
                platform_stats[platform] = {}
            platform_stats[platform]["messages"] = count

        return {
            "platform_breakdown": platform_stats,
            "total_platforms": len(platform_stats)
        }

    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get platform stats: {str(e)}")
