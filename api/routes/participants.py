"""Participant management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
import logging

from api.dependencies import get_db
from db.models.participant import Participant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/participants", tags=["Participants"])


@router.get("/", summary="Get all participants")
async def get_participants(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of participants to return"),
    offset: int = Query(0, ge=0, description="Number of participants to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all participants with optional filtering and pagination.

    Args:
        platform: Optional platform filter
        limit: Maximum number of results to return
        offset: Number of results to skip
        db: Database session

    Returns:
        Dict containing list of participants and metadata
    """
    try:
        query = select(Participant)

        # Apply platform filter if provided
        if platform:
            query = query.where(Participant.platform == platform)

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        participants = result.scalars().all()

        return {
            "participants": [
                {
                    "id": str(p.id),
                    "platform": p.platform,
                    "platform_user_id": p.platform_user_id,
                    "display_name": p.display_name,
                    "email": p.email,
                    "phone": p.phone,
                    "avatar_url": p.avatar_url,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in participants
            ],
            "count": len(participants),
            "offset": offset,
            "limit": limit,
            "platform_filter": platform
        }
    except Exception as e:
        logger.error(f"Error getting participants: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get participants: {str(e)}")


@router.get("/{participant_id}", summary="Get participant by ID")
async def get_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific participant by ID.

    Args:
        participant_id: UUID of the participant
        db: Database session

    Returns:
        Dict containing participant details
    """
    try:
        result = await db.execute(
            select(Participant).where(Participant.id == participant_id)
        )
        participant = result.scalar_one_or_none()

        if not participant:
            raise HTTPException(
                status_code=404, detail="Participant not found")

        return {
            "id": str(participant.id),
            "platform": participant.platform,
            "platform_user_id": participant.platform_user_id,
            "display_name": participant.display_name,
            "email": participant.email,
            "phone": participant.phone,
            "avatar_url": participant.avatar_url,
            "created_at": participant.created_at.isoformat() if participant.created_at else None,
            "updated_at": participant.updated_at.isoformat() if participant.updated_at else None,
            "participant_metadata": participant.participant_metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting participant {participant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get participant: {str(e)}")
