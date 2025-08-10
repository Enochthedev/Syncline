"""Thread management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
import logging

from api.dependencies import get_db
from db.models.thread import Thread

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/threads", tags=["Threads"])


@router.get("/", summary="Get all threads")
async def get_threads(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of threads to return"),
    offset: int = Query(0, ge=0, description="Number of threads to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all threads with optional filtering and pagination.

    Args:
        platform: Optional platform filter
        limit: Maximum number of results to return
        offset: Number of results to skip
        db: Database session

    Returns:
        Dict containing list of threads and metadata
    """
    try:
        query = select(Thread)

        # Apply platform filter if provided
        if platform:
            query = query.where(Thread.platform == platform)

        # Order by last message time (most recent first)
        query = query.order_by(Thread.last_message_at.desc().nullslast())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        threads = result.scalars().all()

        return {
            "threads": [
                {
                    "id": str(t.id),
                    "platform": t.platform,
                    "platform_thread_id": t.platform_thread_id,
                    "title": t.title,
                    "participants": [str(p) for p in (t.participants or [])],
                    "message_count": t.message_count,
                    "last_message_at": t.last_message_at.isoformat() if t.last_message_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None
                }
                for t in threads
            ],
            "count": len(threads),
            "offset": offset,
            "limit": limit,
            "platform_filter": platform
        }
    except Exception as e:
        logger.error(f"Error getting threads: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get threads: {str(e)}")


@router.get("/{thread_id}", summary="Get thread by ID")
async def get_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific thread by ID.

    Args:
        thread_id: UUID of the thread
        db: Database session

    Returns:
        Dict containing thread details
    """
    try:
        result = await db.execute(
            select(Thread).where(Thread.id == thread_id)
        )
        thread = result.scalar_one_or_none()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        return {
            "id": str(thread.id),
            "platform": thread.platform,
            "platform_thread_id": thread.platform_thread_id,
            "title": thread.title,
            "participants": [str(p) for p in (thread.participants or [])],
            "message_count": thread.message_count,
            "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
            "created_at": thread.created_at.isoformat() if thread.created_at else None,
            "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
            "thread_metadata": thread.thread_metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread {thread_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get thread: {str(e)}")


@router.get("/{thread_id}/messages", summary="Get messages in thread")
async def get_thread_messages(
    thread_id: str,
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get messages in a specific thread.

    Args:
        thread_id: UUID of the thread
        limit: Maximum number of results to return
        offset: Number of results to skip
        db: Database session

    Returns:
        Dict containing list of messages in the thread
    """
    try:
        from db.models.message import Message

        # First verify thread exists
        thread_result = await db.execute(
            select(Thread).where(Thread.id == thread_id)
        )
        thread = thread_result.scalar_one_or_none()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get messages in thread
        query = select(Message).where(Message.thread_id == thread_id)
        query = query.order_by(Message.timestamp.desc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        messages = result.scalars().all()

        return {
            "thread_id": thread_id,
            "messages": [
                {
                    "id": str(m.id),
                    "platform": m.platform,
                    "platform_message_id": m.platform_message_id,
                    "sender_id": str(m.sender_id),
                    "content_text": m.content_text,
                    "content_html": m.content_html,
                    "content_markdown": m.content_markdown,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ],
            "count": len(messages),
            "offset": offset,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for thread {thread_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get thread messages: {str(e)}")
