"""
Database operations for summary generation.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .types import SummaryRequest, SummaryResult, SummaryType, SummaryScope

logger = logging.getLogger(__name__)

# Check database availability
try:
    from sqlalchemy import select, and_, desc
    from sqlalchemy.ext.asyncio import AsyncSession
    from db.models.summary import Summary
    from db.models.message import Message
    from db.models.thread import Thread
    from db.models.participant import Participant
    from db.session import get_async_session
    DB_AVAILABLE = True
except ImportError:
    # If imports fail, set DB_AVAILABLE to False
    DB_AVAILABLE = False
    select = and_ = desc = None
    AsyncSession = Summary = Message = Thread = Participant = None
    get_async_session = None


class DatabaseOperations:
    """Database operations for summary generation."""

    @staticmethod
    async def get_messages_for_summary(request: SummaryRequest) -> List[Dict[str, Any]]:
        """Get messages based on summary request parameters."""
        if not DB_AVAILABLE:
            # Return empty list for testing without database
            return []

        async with get_async_session() as session:
            query = select(Message).join(Thread).join(Participant)

            # Apply scope filtering
            if request.scope_type == SummaryScope.thread and request.scope_id:
                query = query.where(Message.thread_id == request.scope_id)
            elif request.scope_type == SummaryScope.contact and request.scope_id:
                query = query.where(Message.sender_id == request.scope_id)

            # Apply time filtering
            if request.timeframe_start:
                query = query.where(Message.timestamp >=
                                    request.timeframe_start)
            if request.timeframe_end:
                query = query.where(Message.timestamp <= request.timeframe_end)

            # Order by timestamp
            query = query.order_by(Message.timestamp.asc())

            # Execute query
            result = await session.execute(query)
            messages = result.scalars().all()

            # Convert to dict format for processing
            return [
                {
                    'id': msg.id,
                    'content': msg.content_text or msg.content_markdown or msg.content_html or "",
                    'sender': msg.sender.display_name or msg.sender.email or "Unknown",
                    'timestamp': msg.timestamp,
                    'platform': msg.platform,
                    'thread_id': msg.thread_id
                }
                for msg in messages
                if msg.content_text or msg.content_markdown or msg.content_html
            ]

    @staticmethod
    async def store_summary(result: SummaryResult, request: SummaryRequest) -> str:
        """Store summary in database."""
        if not DB_AVAILABLE:
            # For testing without database, return mock ID
            return f"mock_summary_{request.id}"

        try:
            async with get_async_session() as session:
                summary = Summary(
                    type=request.summary_type.value,
                    scope_type=request.scope_type.value,
                    scope_id=request.scope_id,
                    content=result.content,
                    key_points=result.key_points,
                    action_items=result.action_items,
                    entities=[],  # Entity IDs would be resolved separately
                    timeframe_start=request.timeframe_start,
                    timeframe_end=request.timeframe_end,
                    summary_metadata={
                        'confidence_score': result.confidence_score,
                        'word_count': result.word_count,
                        'processing_time': result.processing_time,
                        'quality': request.quality.value,
                        'entities_mentioned': result.entities
                    }
                )

                session.add(summary)
                await session.commit()
                await session.refresh(summary)

                return str(summary.id)

        except Exception as e:
            logger.error(f"Failed to store summary: {e}")
            return ""

    @staticmethod
    async def get_latest_thread_summary(session: Optional[AsyncSession], thread_id: str):
        """Get the latest summary for a thread."""
        if not DB_AVAILABLE or not session:
            return None

        query = select(Summary).where(
            and_(
                Summary.scope_type == SummaryScope.thread.value,
                Summary.scope_id == thread_id,
                Summary.type == SummaryType.thread.value
            )
        ).order_by(desc(Summary.created_at)).limit(1)

        result = await session.execute(query)
        return result.scalar_one_or_none()
