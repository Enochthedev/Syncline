"""Summary API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from api.dependencies import get_db
from api.auth.auth import get_current_active_user
from api.auth.rate_limiting import rate_limit
from api.auth.rbac import require_permission
from api.auth.models import User
from db.models.summary import Summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.get("/", summary="Get summaries")
@rate_limit(requests_per_minute=30, requests_per_hour=500, per_user=True)
@require_permission("summaries", "read")
async def get_summaries(
    scope_type: Optional[str] = Query(
        None, description="Filter by scope type (message, thread, contact, global)"),
    scope_id: Optional[str] = Query(None, description="Filter by scope ID"),
    summary_type: Optional[str] = Query(
        None, description="Filter by summary type (micro, thread, daily, weekly)"),
    since_date: Optional[datetime] = Query(
        None, description="Get summaries created since this date"),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summaries with filtering and pagination.

    Implements the 'summarize since [date]' functionality as required.
    Provides access to AI-generated summaries at various granularities.
    """
    try:
        query = select(Summary)

        # Apply filters
        filters = []

        if scope_type:
            filters.append(Summary.scope_type == scope_type)

        if scope_id:
            filters.append(Summary.scope_id == UUID(scope_id))

        if summary_type:
            filters.append(Summary.type == summary_type)

        if since_date:
            filters.append(Summary.created_at >= since_date)

        if filters:
            query = query.where(and_(*filters))

        # Apply tenant isolation (if needed)
        if hasattr(current_user, 'tenant_id') and not current_user.is_superuser:
            # Additional tenant filtering would go here if needed
            pass

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Order by creation time (most recent first)
        query = query.order_by(desc(Summary.created_at))

        result = await db.execute(query)
        summaries = result.scalars().all()

        return {
            "summaries": [
                {
                    "id": str(s.id),
                    "type": s.type,
                    "scope_type": s.scope_type,
                    "scope_id": str(s.scope_id) if s.scope_id else None,
                    "content": s.content,
                    "key_points": s.key_points,
                    "action_items": s.action_items,
                    "entities": [str(e) for e in s.entities] if s.entities else [],
                    "timeframe_start": s.timeframe_start.isoformat() if s.timeframe_start else None,
                    "timeframe_end": s.timeframe_end.isoformat() if s.timeframe_end else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "summary_metadata": s.summary_metadata
                }
                for s in summaries
            ],
            "count": len(summaries),
            "offset": offset,
            "limit": limit,
            "filters": {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "summary_type": summary_type,
                "since_date": since_date.isoformat() if since_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error getting summaries: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get summaries: {str(e)}")


@router.get("/{summary_id}", summary="Get summary by ID")
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("summaries", "read")
async def get_summary(
    summary_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific summary by ID.

    Returns detailed summary information including content, key points,
    action items, and associated entities.
    """
    try:
        result = await db.execute(
            select(Summary).where(Summary.id == UUID(summary_id))
        )
        summary = result.scalar_one_or_none()

        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")

        return {
            "id": str(summary.id),
            "type": summary.type,
            "scope_type": summary.scope_type,
            "scope_id": str(summary.scope_id) if summary.scope_id else None,
            "content": summary.content,
            "key_points": summary.key_points,
            "action_items": summary.action_items,
            "entities": [str(e) for e in summary.entities] if summary.entities else [],
            "timeframe_start": summary.timeframe_start.isoformat() if summary.timeframe_start else None,
            "timeframe_end": summary.timeframe_end.isoformat() if summary.timeframe_end else None,
            "created_at": summary.created_at.isoformat() if summary.created_at else None,
            "summary_metadata": summary.summary_metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary {summary_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get summary: {str(e)}")


@router.get("/thread/{thread_id}", summary="Get thread summaries")
@rate_limit(requests_per_minute=30, requests_per_hour=300, per_user=True)
@require_permission("summaries", "read")
async def get_thread_summaries(
    thread_id: str,
    summary_type: Optional[str] = Query(
        None, description="Filter by summary type"),
    since_date: Optional[datetime] = Query(
        None, description="Get summaries since this date"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summaries for a specific thread.

    Returns all summaries associated with a conversation thread,
    optionally filtered by type and date.
    """
    try:
        query = select(Summary).where(
            and_(
                Summary.scope_type == "thread",
                Summary.scope_id == UUID(thread_id)
            )
        )

        # Apply additional filters
        if summary_type:
            query = query.where(Summary.type == summary_type)

        if since_date:
            query = query.where(Summary.created_at >= since_date)

        # Apply limit and ordering
        query = query.order_by(desc(Summary.created_at)).limit(limit)

        result = await db.execute(query)
        summaries = result.scalars().all()

        return {
            "thread_id": thread_id,
            "summaries": [
                {
                    "id": str(s.id),
                    "type": s.type,
                    "content": s.content,
                    "key_points": s.key_points,
                    "action_items": s.action_items,
                    "entities": [str(e) for e in s.entities] if s.entities else [],
                    "timeframe_start": s.timeframe_start.isoformat() if s.timeframe_start else None,
                    "timeframe_end": s.timeframe_end.isoformat() if s.timeframe_end else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in summaries
            ],
            "count": len(summaries),
            "filters": {
                "summary_type": summary_type,
                "since_date": since_date.isoformat() if since_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error getting thread summaries for {thread_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get thread summaries: {str(e)}")


@router.get("/contact/{contact_id}", summary="Get contact summaries")
@rate_limit(requests_per_minute=30, requests_per_hour=300, per_user=True)
@require_permission("summaries", "read")
async def get_contact_summaries(
    contact_id: str,
    summary_type: Optional[str] = Query(
        None, description="Filter by summary type"),
    since_date: Optional[datetime] = Query(
        None, description="Get summaries since this date"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summaries for a specific contact.

    Returns all summaries associated with a contact,
    optionally filtered by type and date.
    """
    try:
        query = select(Summary).where(
            and_(
                Summary.scope_type == "contact",
                Summary.scope_id == UUID(contact_id)
            )
        )

        # Apply additional filters
        if summary_type:
            query = query.where(Summary.type == summary_type)

        if since_date:
            query = query.where(Summary.created_at >= since_date)

        # Apply limit and ordering
        query = query.order_by(desc(Summary.created_at)).limit(limit)

        result = await db.execute(query)
        summaries = result.scalars().all()

        return {
            "contact_id": contact_id,
            "summaries": [
                {
                    "id": str(s.id),
                    "type": s.type,
                    "content": s.content,
                    "key_points": s.key_points,
                    "action_items": s.action_items,
                    "entities": [str(e) for e in s.entities] if s.entities else [],
                    "timeframe_start": s.timeframe_start.isoformat() if s.timeframe_start else None,
                    "timeframe_end": s.timeframe_end.isoformat() if s.timeframe_end else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in summaries
            ],
            "count": len(summaries),
            "filters": {
                "summary_type": summary_type,
                "since_date": since_date.isoformat() if since_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error getting contact summaries for {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact summaries: {str(e)}")


@router.get("/daily/{date}", summary="Get daily summaries")
@rate_limit(requests_per_minute=20, requests_per_hour=200, per_user=True)
@require_permission("summaries", "read")
async def get_daily_summaries(
    date: str,  # Format: YYYY-MM-DD
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get daily summaries for a specific date.

    Returns all daily summaries generated for the specified date,
    providing a comprehensive overview of that day's communications.
    """
    try:
        # Parse date
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        query = select(Summary).where(
            and_(
                Summary.type == "daily",
                Summary.timeframe_start >= start_datetime,
                Summary.timeframe_end <= end_datetime
            )
        )

        # Order by creation time
        query = query.order_by(desc(Summary.created_at))

        result = await db.execute(query)
        summaries = result.scalars().all()

        return {
            "date": date,
            "summaries": [
                {
                    "id": str(s.id),
                    "scope_type": s.scope_type,
                    "scope_id": str(s.scope_id) if s.scope_id else None,
                    "content": s.content,
                    "key_points": s.key_points,
                    "action_items": s.action_items,
                    "entities": [str(e) for e in s.entities] if s.entities else [],
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in summaries
            ],
            "count": len(summaries)
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except Exception as e:
        logger.error(f"Error getting daily summaries for {date}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get daily summaries: {str(e)}")
