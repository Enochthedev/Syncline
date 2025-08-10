"""Message management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
import logging

from api.dependencies import get_db
from db.models.message import Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("/", summary="Get recent messages")
async def get_messages(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent messages with optional filtering and pagination.

    Args:
        platform: Optional platform filter
        limit: Maximum number of results to return
        offset: Number of results to skip
        db: Database session

    Returns:
        Dict containing list of messages and metadata
    """
    try:
        query = select(Message)

        # Apply platform filter if provided
        if platform:
            query = query.where(Message.platform == platform)

        # Order by timestamp (most recent first)
        query = query.order_by(Message.timestamp.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        messages = result.scalars().all()

        return {
            "messages": [
                {
                    "id": str(m.id),
                    "platform": m.platform,
                    "platform_message_id": m.platform_message_id,
                    "thread_id": str(m.thread_id),
                    "sender_id": str(m.sender_id),
                    "content_text": m.content_text,
                    "content_html": m.content_html,
                    "content_markdown": m.content_markdown,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None
                }
                for m in messages
            ],
            "count": len(messages),
            "offset": offset,
            "limit": limit,
            "platform_filter": platform
        }
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.get("/{message_id}", summary="Get message by ID")
async def get_message(
    message_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific message by ID.

    Args:
        message_id: UUID of the message
        db: Database session

    Returns:
        Dict containing message details
    """
    try:
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        return {
            "id": str(message.id),
            "platform": message.platform,
            "platform_message_id": message.platform_message_id,
            "thread_id": str(message.thread_id),
            "sender_id": str(message.sender_id),
            "content_text": message.content_text,
            "content_html": message.content_html,
            "content_markdown": message.content_markdown,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "updated_at": message.updated_at.isoformat() if message.updated_at else None,
            "message_metadata": message.message_metadata,
            "raw_data": message.raw_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message {message_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get message: {str(e)}")


@router.get("/search", summary="Search messages")
async def search_messages(
    q: str = Query(..., description="Search query"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search messages by content.

    Args:
        q: Search query string
        platform: Optional platform filter
        limit: Maximum number of results to return
        offset: Number of results to skip
        db: Database session

    Returns:
        Dict containing matching messages
    """
    try:
        query = select(Message).where(Message.content_text.ilike(f"%{q}%"))

        # Apply platform filter if provided
        if platform:
            query = query.where(Message.platform == platform)

        # Order by timestamp (most recent first)
        query = query.order_by(Message.timestamp.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        messages = result.scalars().all()

        return {
            "query": q,
            "messages": [
                {
                    "id": str(m.id),
                    "platform": m.platform,
                    "platform_message_id": m.platform_message_id,
                    "thread_id": str(m.thread_id),
                    "sender_id": str(m.sender_id),
                    "content_text": m.content_text,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ],
            "count": len(messages),
            "offset": offset,
            "limit": limit,
            "platform_filter": platform
        }

    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search messages: {str(e)}")
