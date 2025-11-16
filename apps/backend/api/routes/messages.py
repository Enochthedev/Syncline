"""
Messages API Endpoints

Provides endpoints for:
- Listing normalized messages with filtering
- Getting message details
- Message statistics
- Reprocessing messages
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_database_session, get_pagination_params, PaginationParams
from db.models.message import Message
from db.models.raw_message import RawMessage
from services.event_bus import get_event_bus
from services.events.types import EventType, MessageEvent
from services.search.fulltext_search import (
    get_fulltext_search_service,
    FullTextSearchFilter,
    FullTextSearchResult as FullTextResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class MessageContent(BaseModel):
    """Message content structure."""
    
    text: str = Field(..., description="Plain text content")
    html: str | None = Field(None, description="HTML content")
    format: str = Field(..., description="Content format: plain, html, markdown")


class MessageSender(BaseModel):
    """Message sender information."""
    
    sender_id: UUID | None = Field(None, description="Sender participant ID")
    platform_user_id: str | None = Field(None, description="Platform-specific user ID")
    name: str | None = Field(None, description="Sender name")


class AttachmentInfo(BaseModel):
    """Attachment information."""
    
    id: UUID = Field(..., description="Attachment ID")
    filename: str = Field(..., description="File name")
    mime_type: str | None = Field(None, description="MIME type")
    size_bytes: int | None = Field(None, description="File size in bytes")


class MessageResponse(BaseModel):
    """Message response model."""
    
    id: UUID = Field(..., description="Message ID")
    connection_id: UUID = Field(..., description="Platform connection ID")
    platform: str = Field(..., description="Platform name")
    platform_message_id: str = Field(..., description="Platform message ID")
    thread_id: str | None = Field(None, description="Thread ID")
    sender: MessageSender = Field(..., description="Sender information")
    content: MessageContent = Field(..., description="Message content")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    timestamp: datetime = Field(..., description="Message timestamp")
    collected_at: datetime = Field(..., description="Collection timestamp")
    cleaned_at: datetime = Field(..., description="Cleaning timestamp")
    attachment_count: int = Field(default=0, description="Number of attachments")
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Paginated message list response."""
    
    messages: list[MessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
    skip: int = Field(..., description="Number of messages skipped")
    limit: int = Field(..., description="Maximum messages returned")


class MessageDetailResponse(MessageResponse):
    """Detailed message response with attachments."""
    
    attachments: list[AttachmentInfo] = Field(default_factory=list, description="Message attachments")
    raw_data: dict[str, Any] | None = Field(None, description="Original raw message data")


class MessageStats(BaseModel):
    """Message statistics."""
    
    total_messages: int = Field(..., description="Total normalized messages")
    messages_by_platform: dict[str, int] = Field(..., description="Message count by platform")
    messages_by_date: dict[str, int] = Field(..., description="Message count by date")
    total_attachments: int = Field(..., description="Total attachments")
    processing_stats: dict[str, Any] = Field(..., description="Processing statistics")


class ReprocessResponse(BaseModel):
    """Reprocess message response."""

    message_id: UUID = Field(..., description="Message ID")
    status: str = Field(..., description="Reprocess status")
    message: str = Field(..., description="Status message")


class FullTextSearchResponse(BaseModel):
    """Full-text search response."""

    query: str = Field(..., description="Search query")
    results: list[FullTextResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    skip: int = Field(..., description="Number of results skipped")
    limit: int = Field(..., description="Maximum results returned")


# =============================================================================
# Message Endpoints
# =============================================================================

@router.get(
    "/search",
    response_model=FullTextSearchResponse,
    summary="Full-Text Search Messages",
    description="Search messages using PostgreSQL full-text search with advanced filtering"
)
async def search_messages(
    query: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_database_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    platforms: list[str] | None = Query(None, description="Filter by platforms"),
    contact_ids: list[UUID] | None = Query(None, description="Filter by contact IDs"),
    thread_ids: list[str] | None = Query(None, description="Filter by thread IDs"),
    start_date: datetime | None = Query(None, description="Filter messages after this date"),
    end_date: datetime | None = Query(None, description="Filter messages before this date"),
    has_attachments: bool | None = Query(None, description="Filter by attachment presence"),
    include_highlights: bool = Query(True, description="Include highlighted snippets"),
) -> FullTextSearchResponse:
    """
    Search messages using full-text search.

    Performs PostgreSQL full-text search with ranking and highlighting.
    Supports advanced filtering by platform, contact, date range, and more.

    Args:
        query: Search query text
        db: Database session
        pagination: Pagination parameters
        platforms: Optional platform filter
        contact_ids: Optional contact ID filter
        thread_ids: Optional thread ID filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        has_attachments: Optional attachment filter
        include_highlights: Whether to include highlighted snippets

    Returns:
        FullTextSearchResponse: Search results with ranking
    """
    try:
        logger.info(f"Full-text search: '{query}'")

        # Build search filters
        search_filter = FullTextSearchFilter(
            platforms=platforms,
            contact_ids=contact_ids,
            thread_ids=thread_ids,
            start_date=start_date,
            end_date=end_date,
            has_attachments=has_attachments,
        )

        # Get search service
        search_service = get_fulltext_search_service()

        # Perform search
        results, total = await search_service.search(
            query=query,
            db=db,
            limit=pagination.limit,
            offset=pagination.skip,
            filters=search_filter,
            include_highlights=include_highlights,
        )

        logger.info(f"Full-text search returned {len(results)} results (total: {total})")

        return FullTextSearchResponse(
            query=query,
            results=results,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
        )

    except Exception as e:
        logger.error(f"Full-text search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "",
    response_model=MessageListResponse,
    summary="List Normalized Messages",
    description="List normalized messages with optional filtering and pagination"
)
async def list_messages(
    db: AsyncSession = Depends(get_database_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    platform: str | None = Query(None, description="Filter by platform"),
    connection_id: UUID | None = Query(None, description="Filter by connection ID"),
    thread_id: str | None = Query(None, description="Filter by thread ID"),
    start_date: datetime | None = Query(None, description="Filter messages after this date"),
    end_date: datetime | None = Query(None, description="Filter messages before this date"),
    search: str | None = Query(None, description="Search in message content"),
) -> MessageListResponse:
    """
    List normalized messages with filtering and pagination.
    
    Args:
        db: Database session
        pagination: Pagination parameters
        platform: Optional platform filter
        connection_id: Optional connection ID filter
        thread_id: Optional thread ID filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        search: Optional text search in content
        
    Returns:
        MessageListResponse: Paginated list of messages
    """
    # Build query
    query = select(Message)
    count_query = select(func.count(Message.id))
    
    # Apply filters
    filters = []
    
    if platform:
        filters.append(Message.platform == platform)
    
    if connection_id:
        filters.append(Message.connection_id == connection_id)
    
    if thread_id:
        filters.append(Message.thread_id == thread_id)
    
    if start_date:
        filters.append(Message.timestamp >= start_date)
    
    if end_date:
        filters.append(Message.timestamp <= end_date)
    
    if search:
        # Search in text content (case-insensitive)
        filters.append(
            func.lower(Message.content["text"].astext).contains(search.lower())
        )
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply ordering and pagination
    query = query.order_by(Message.timestamp.desc())
    query = query.offset(pagination.skip).limit(pagination.limit)
    
    # Execute query
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Convert to response models
    message_responses = []
    for msg in messages:
        # Extract sender info from metadata
        sender_info = msg.message_metadata.get("sender", {}) if msg.message_metadata else {}
        
        message_responses.append(MessageResponse(
            id=msg.id,
            connection_id=msg.connection_id,
            platform=msg.platform,
            platform_message_id=msg.platform_message_id,
            thread_id=msg.thread_id,
            sender=MessageSender(
                sender_id=msg.sender_id,
                platform_user_id=sender_info.get("platform_user_id"),
                name=sender_info.get("name")
            ),
            content=MessageContent(**msg.content),
            metadata=msg.message_metadata,
            timestamp=msg.timestamp,
            collected_at=msg.collected_at,
            cleaned_at=msg.cleaned_at,
            attachment_count=len(msg.attachments) if msg.attachments else 0
        ))
    
    return MessageListResponse(
        messages=message_responses,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit
    )


@router.get(
    "/stats",
    response_model=MessageStats,
    summary="Get Message Statistics",
    description="Get statistics about normalized messages"
)
async def get_message_stats(
    db: AsyncSession = Depends(get_database_session),
    platform: str | None = Query(None, description="Filter by platform"),
    connection_id: UUID | None = Query(None, description="Filter by connection ID"),
    start_date: datetime | None = Query(None, description="Stats from this date"),
    end_date: datetime | None = Query(None, description="Stats until this date"),
) -> MessageStats:
    """
    Get message statistics.
    
    Args:
        db: Database session
        platform: Optional platform filter
        connection_id: Optional connection ID filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        MessageStats: Message statistics
    """
    # Build base filters
    filters = []
    
    if platform:
        filters.append(Message.platform == platform)
    
    if connection_id:
        filters.append(Message.connection_id == connection_id)
    
    if start_date:
        filters.append(Message.timestamp >= start_date)
    
    if end_date:
        filters.append(Message.timestamp <= end_date)
    
    # Get total message count
    count_query = select(func.count(Message.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    
    result = await db.execute(count_query)
    total_messages = result.scalar() or 0
    
    # Get messages by platform
    platform_query = select(
        Message.platform,
        func.count(Message.id).label("count")
    ).group_by(Message.platform)
    
    if filters:
        platform_query = platform_query.where(and_(*filters))
    
    result = await db.execute(platform_query)
    messages_by_platform = {row[0]: row[1] for row in result.all()}
    
    # Get messages by date (grouped by day)
    date_query = select(
        func.date(Message.timestamp).label("date"),
        func.count(Message.id).label("count")
    ).group_by(func.date(Message.timestamp))
    
    if filters:
        date_query = date_query.where(and_(*filters))
    
    date_query = date_query.order_by(func.date(Message.timestamp).desc()).limit(30)
    
    result = await db.execute(date_query)
    messages_by_date = {str(row[0]): row[1] for row in result.all()}
    
    # Get total attachments (using subquery)
    from db.models.attachment import Attachment
    
    attachment_query = select(func.count(Attachment.id))
    if filters:
        # Join with Message to apply filters
        attachment_query = attachment_query.select_from(Attachment).join(Message)
        attachment_query = attachment_query.where(and_(*filters))
    
    result = await db.execute(attachment_query)
    total_attachments = result.scalar() or 0
    
    # Get processing stats
    processing_query = select(
        func.count(RawMessage.id).label("total_raw"),
        func.count(RawMessage.id).filter(RawMessage.processed == True).label("processed"),
        func.count(RawMessage.id).filter(RawMessage.processed == False).label("pending")
    )
    
    if connection_id:
        processing_query = processing_query.where(RawMessage.connection_id == connection_id)
    
    result = await db.execute(processing_query)
    processing_row = result.one()
    
    processing_stats = {
        "total_raw_messages": processing_row.total_raw or 0,
        "processed_messages": processing_row.processed or 0,
        "pending_messages": processing_row.pending or 0,
        "processing_rate": (
            round((processing_row.processed / processing_row.total_raw) * 100, 2)
            if processing_row.total_raw > 0 else 0.0
        )
    }
    
    return MessageStats(
        total_messages=total_messages,
        messages_by_platform=messages_by_platform,
        messages_by_date=messages_by_date,
        total_attachments=total_attachments,
        processing_stats=processing_stats
    )


@router.get(
    "/{message_id}",
    response_model=MessageDetailResponse,
    summary="Get Message Details",
    description="Get detailed information about a specific message"
)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_database_session),
    include_raw: bool = Query(False, description="Include raw message data")
) -> MessageDetailResponse:
    """
    Get detailed message information.
    
    Args:
        message_id: Message ID
        db: Database session
        include_raw: Whether to include raw message data
        
    Returns:
        MessageDetailResponse: Detailed message information
        
    Raises:
        HTTPException: If message not found
    """
    # Query with relationships
    query = select(Message).where(Message.id == message_id)
    query = query.options(
        selectinload(Message.attachments),
        selectinload(Message.raw_message)
    )
    
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found"
        )
    
    # Extract sender info
    sender_info = message.message_metadata.get("sender", {}) if message.message_metadata else {}
    
    # Build attachment list
    attachments = []
    if message.attachments:
        for att in message.attachments:
            attachments.append(AttachmentInfo(
                id=att.id,
                filename=att.filename,
                mime_type=att.mime_type,
                size_bytes=att.size_bytes
            ))
    
    # Get raw data if requested
    raw_data = None
    if include_raw and message.raw_message:
        raw_data = message.raw_message.raw_data
    
    return MessageDetailResponse(
        id=message.id,
        connection_id=message.connection_id,
        platform=message.platform,
        platform_message_id=message.platform_message_id,
        thread_id=message.thread_id,
        sender=MessageSender(
            sender_id=message.sender_id,
            platform_user_id=sender_info.get("platform_user_id"),
            name=sender_info.get("name")
        ),
        content=MessageContent(**message.content),
        metadata=message.message_metadata,
        timestamp=message.timestamp,
        collected_at=message.collected_at,
        cleaned_at=message.cleaned_at,
        attachment_count=len(attachments),
        attachments=attachments,
        raw_data=raw_data
    )


@router.post(
    "/{message_id}/reprocess",
    response_model=ReprocessResponse,
    summary="Reprocess Message",
    description="Reprocess a message through the cleaning stage"
)
async def reprocess_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ReprocessResponse:
    """
    Reprocess a message through the cleaning stage.
    
    This marks the raw message as unprocessed and emits an event
    to trigger re-normalization.
    
    Args:
        message_id: Message ID to reprocess
        db: Database session
        
    Returns:
        ReprocessResponse: Reprocess status
        
    Raises:
        HTTPException: If message not found
    """
    # Get message with raw message
    query = select(Message).where(Message.id == message_id)
    query = query.options(selectinload(Message.raw_message))
    
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found"
        )
    
    if not message.raw_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message has no associated raw message to reprocess"
        )
    
    try:
        # Mark raw message as unprocessed
        message.raw_message.processed = False
        
        # Delete the normalized message (will be recreated)
        await db.delete(message)
        await db.commit()
        
        # Emit event to trigger reprocessing
        event_bus = get_event_bus()
        event = MessageEvent(
            event_id=str(UUID(int=0)),  # Generate new event ID
            event_type=EventType.MESSAGE_COLLECTED,
            source="messages_api",
            payload={
                "raw_message_id": str(message.raw_message.id),
                "connection_id": str(message.connection_id),
                "platform": message.platform,
                "platform_message_id": message.platform_message_id,
                "reprocess": True
            }
        )
        
        await event_bus.publish(event)
        
        logger.info(f"Reprocessing message {message_id}")
        
        return ReprocessResponse(
            message_id=message_id,
            status="queued",
            message="Message queued for reprocessing"
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reprocess message {message_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess message: {str(e)}"
        )


# =============================================================================
# Export router
# =============================================================================

__all__ = ["router"]
