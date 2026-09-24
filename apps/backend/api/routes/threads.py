"""
Threads API Endpoints

Provides endpoints for:
- Listing threads with filtering
- Getting thread details
- Getting messages in a thread
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import (
    PaginationParams,
    get_database_session,
    get_pagination_params,
)
from db.models.contact import Contact
from db.models.message import Message
from db.models.thread import Thread

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class ThreadResponse(BaseModel):
    """Thread response model."""

    id: UUID = Field(..., description="Thread ID")
    platform: str = Field(..., description="Platform name")
    platform_thread_id: str = Field(..., description="Platform thread ID")
    contact_id: UUID | None = Field(None, description="Primary contact ID")
    contact_name: str | None = Field(None, description="Primary contact name")
    title: str | None = Field(None, description="Thread title")
    participant_ids: list[UUID] | None = Field(None, description="Participant IDs")
    message_count: int = Field(default=0, description="Number of messages")
    first_message_at: datetime | None = Field(
        None, description="First message timestamp"
    )
    last_message_at: datetime | None = Field(None, description="Last message timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class ThreadListResponse(BaseModel):
    """Paginated thread list response."""

    threads: list[ThreadResponse] = Field(..., description="List of threads")
    total: int = Field(..., description="Total number of threads")
    skip: int = Field(..., description="Number of threads skipped")
    limit: int = Field(..., description="Maximum threads returned")


class MessageSummary(BaseModel):
    """Message summary for thread."""

    id: UUID = Field(..., description="Message ID")
    platform_message_id: str = Field(..., description="Platform message ID")
    sender_id: UUID | None = Field(None, description="Sender participant ID")
    sender_name: str | None = Field(None, description="Sender name")
    content_preview: str = Field(..., description="Content preview (first 200 chars)")
    timestamp: datetime = Field(..., description="Message timestamp")
    attachment_count: int = Field(default=0, description="Number of attachments")

    class Config:
        from_attributes = True


class ThreadMessagesResponse(BaseModel):
    """Thread messages response."""

    thread_id: UUID = Field(..., description="Thread ID")
    platform: str = Field(..., description="Platform name")
    title: str | None = Field(None, description="Thread title")
    messages: list[MessageSummary] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
    skip: int = Field(..., description="Number of messages skipped")
    limit: int = Field(..., description="Maximum messages returned")


class ThreadDetailResponse(ThreadResponse):
    """Detailed thread response with statistics."""

    participant_count: int = Field(default=0, description="Number of participants")
    recent_messages: list[MessageSummary] = Field(
        default_factory=list, description="Recent messages (last 5)"
    )


# =============================================================================
# Thread Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ThreadListResponse,
    summary="List Threads",
    description="List all threads with optional filtering and pagination",
)
async def list_threads(
    db: AsyncSession = Depends(get_database_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    platform: str | None = Query(None, description="Filter by platform"),
    contact_id: UUID | None = Query(None, description="Filter by contact ID"),
    has_contact: bool | None = Query(
        None, description="Filter threads with/without contact"
    ),
    min_messages: int | None = Query(None, description="Minimum message count"),
    start_date: datetime | None = Query(
        None, description="Filter threads after this date"
    ),
    end_date: datetime | None = Query(
        None, description="Filter threads before this date"
    ),
) -> ThreadListResponse:
    """
    List threads with filtering and pagination.

    Args:
        db: Database session
        pagination: Pagination parameters
        platform: Optional platform filter
        contact_id: Optional contact ID filter
        has_contact: Optional contact association filter
        min_messages: Optional minimum message count
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        ThreadListResponse: Paginated list of threads
    """
    # Build query
    query = select(Thread)
    count_query = select(func.count(Thread.id))

    # Apply filters
    filters = []

    if platform:
        filters.append(Thread.platform == platform)

    if contact_id:
        filters.append(Thread.contact_id == contact_id)

    if has_contact is not None:
        if has_contact:
            filters.append(Thread.contact_id.isnot(None))
        else:
            filters.append(Thread.contact_id.is_(None))

    if min_messages is not None:
        filters.append(Thread.message_count >= min_messages)

    if start_date:
        filters.append(Thread.last_message_at >= start_date)

    if end_date:
        filters.append(Thread.last_message_at <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Thread.last_message_at.desc().nullslast())
    query = query.offset(pagination.skip).limit(pagination.limit)

    # Load contact relationship
    query = query.options(selectinload(Thread.contact))

    # Execute query
    result = await db.execute(query)
    threads = result.scalars().all()

    # Convert to response models
    thread_responses = []
    for thread in threads:
        thread_responses.append(
            ThreadResponse(
                id=thread.id,
                platform=thread.platform,
                platform_thread_id=thread.platform_thread_id,
                contact_id=thread.contact_id,
                contact_name=thread.contact.canonical_name if thread.contact else None,
                title=thread.title,
                participant_ids=thread.participant_ids,
                message_count=thread.message_count,
                first_message_at=thread.first_message_at,
                last_message_at=thread.last_message_at,
                created_at=thread.created_at,
                updated_at=thread.updated_at,
            )
        )

    return ThreadListResponse(
        threads=thread_responses,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{thread_id}",
    response_model=ThreadDetailResponse,
    summary="Get Thread Details",
    description="Get detailed information about a specific thread",
)
async def get_thread(
    thread_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ThreadDetailResponse:
    """
    Get detailed thread information.

    Args:
        thread_id: Thread ID
        db: Database session

    Returns:
        ThreadDetailResponse: Detailed thread information

    Raises:
        HTTPException: If thread not found
    """
    # Query with relationships
    query = select(Thread).where(Thread.id == thread_id)
    query = query.options(selectinload(Thread.contact))

    result = await db.execute(query)
    thread = result.scalar_one_or_none()

    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found",
        )

    # Get recent messages
    messages_query = select(Message).where(
        Message.thread_id == thread.platform_thread_id
    )
    messages_query = messages_query.where(Message.platform == thread.platform)
    messages_query = messages_query.order_by(Message.timestamp.desc())
    messages_query = messages_query.limit(5)
    messages_query = messages_query.options(selectinload(Message.attachments))

    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()

    # Build recent messages list
    recent_messages = []
    for msg in messages:
        # Extract sender info from metadata
        sender_info = (
            msg.message_metadata.get("sender", {}) if msg.message_metadata else {}
        )

        # Get content preview
        content_text = msg.content.get("text", "") if msg.content else ""
        content_preview = (
            content_text[:200] + "..." if len(content_text) > 200 else content_text
        )

        recent_messages.append(
            MessageSummary(
                id=msg.id,
                platform_message_id=msg.platform_message_id,
                sender_id=msg.sender_id,
                sender_name=sender_info.get("name"),
                content_preview=content_preview,
                timestamp=msg.timestamp,
                attachment_count=len(msg.attachments) if msg.attachments else 0,
            )
        )

    # Calculate participant count
    participant_count = len(thread.participant_ids) if thread.participant_ids else 0

    return ThreadDetailResponse(
        id=thread.id,
        platform=thread.platform,
        platform_thread_id=thread.platform_thread_id,
        contact_id=thread.contact_id,
        contact_name=thread.contact.canonical_name if thread.contact else None,
        title=thread.title,
        participant_ids=thread.participant_ids,
        message_count=thread.message_count,
        first_message_at=thread.first_message_at,
        last_message_at=thread.last_message_at,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        participant_count=participant_count,
        recent_messages=recent_messages,
    )


@router.get(
    "/{thread_id}/messages",
    response_model=ThreadMessagesResponse,
    summary="Get Thread Messages",
    description="Get all messages in a thread with pagination",
)
async def get_thread_messages(
    thread_id: UUID,
    db: AsyncSession = Depends(get_database_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    order: str = Query("desc", description="Sort order: asc or desc"),
) -> ThreadMessagesResponse:
    """
    Get all messages in a thread.

    Args:
        thread_id: Thread ID
        db: Database session
        pagination: Pagination parameters
        order: Sort order (asc or desc)

    Returns:
        ThreadMessagesResponse: Thread messages

    Raises:
        HTTPException: If thread not found
    """
    # Check if thread exists
    thread_query = select(Thread).where(Thread.id == thread_id)
    thread_result = await db.execute(thread_query)
    thread = thread_result.scalar_one_or_none()

    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found",
        )

    # Query messages
    query = select(Message).where(Message.thread_id == thread.platform_thread_id)
    query = query.where(Message.platform == thread.platform)

    count_query = select(func.count(Message.id))
    count_query = count_query.where(Message.thread_id == thread.platform_thread_id)
    count_query = count_query.where(Message.platform == thread.platform)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering
    if order.lower() == "asc":
        query = query.order_by(Message.timestamp.asc())
    else:
        query = query.order_by(Message.timestamp.desc())

    # Apply pagination
    query = query.offset(pagination.skip).limit(pagination.limit)

    # Load attachments
    query = query.options(selectinload(Message.attachments))

    # Execute query
    result = await db.execute(query)
    messages = result.scalars().all()

    # Convert to response models
    message_summaries = []
    for msg in messages:
        # Extract sender info from metadata
        sender_info = (
            msg.message_metadata.get("sender", {}) if msg.message_metadata else {}
        )

        # Get content preview
        content_text = msg.content.get("text", "") if msg.content else ""
        content_preview = (
            content_text[:200] + "..." if len(content_text) > 200 else content_text
        )

        message_summaries.append(
            MessageSummary(
                id=msg.id,
                platform_message_id=msg.platform_message_id,
                sender_id=msg.sender_id,
                sender_name=sender_info.get("name"),
                content_preview=content_preview,
                timestamp=msg.timestamp,
                attachment_count=len(msg.attachments) if msg.attachments else 0,
            )
        )

    return ThreadMessagesResponse(
        thread_id=thread_id,
        platform=thread.platform,
        title=thread.title,
        messages=message_summaries,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


# =============================================================================
# Export router
# =============================================================================

__all__ = ["router"]
