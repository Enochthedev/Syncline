"""
Full-Text Search Service

Provides PostgreSQL full-text search capabilities for messages:
- Query parsing and sanitization
- Full-text search with ranking
- Advanced filtering by platform, contact, date range, thread
- Pagination support
- Search highlighting
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.contact import Contact
from db.models.message import Message

logger = logging.getLogger(__name__)


class FullTextSearchFilter(BaseModel):
    """Filters for full-text search."""

    platforms: Optional[list[str]] = Field(
        default=None, description="Filter by platforms"
    )
    contact_ids: Optional[list[UUID]] = Field(
        default=None, description="Filter by contact IDs"
    )
    thread_ids: Optional[list[str]] = Field(
        default=None, description="Filter by thread IDs"
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Filter messages after this date"
    )
    end_date: Optional[datetime] = Field(
        default=None, description="Filter messages before this date"
    )
    has_attachments: Optional[bool] = Field(
        default=None, description="Filter by attachment presence"
    )


class FullTextSearchResult(BaseModel):
    """Search result with message details and relevance ranking."""

    message_id: UUID
    platform: str
    platform_message_id: str
    thread_id: Optional[str]
    sender_id: Optional[UUID]
    content: dict
    timestamp: datetime
    rank: float  # Relevance ranking (higher is better)
    headline: Optional[str] = None  # Highlighted snippet

    class Config:
        """Pydantic config."""

        from_attributes = True


class FullTextSearchService:
    """
    Full-text search service for messages.

    Provides functionality for:
    - PostgreSQL full-text search with ranking
    - Query parsing and sanitization
    - Advanced filtering by metadata
    - Search result highlighting
    """

    def __init__(self):
        """Initialize full-text search service."""
        logger.info("Initialized FullTextSearchService")

    async def search(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[FullTextSearchFilter] = None,
        include_highlights: bool = True,
    ) -> tuple[list[FullTextSearchResult], int]:
        """
        Perform full-text search for messages.

        Args:
            query: Search query text
            db: Database session
            limit: Maximum number of results per page
            offset: Number of results to skip (for pagination)
            filters: Optional filters for search
            include_highlights: Whether to include highlighted snippets

        Returns:
            Tuple of (search results, total count)
        """
        try:
            logger.info(f"Full-text search: '{query}' (limit={limit}, offset={offset})")

            # Sanitize and parse query
            ts_query = self._parse_query(query)

            if not ts_query:
                logger.warning("Invalid or empty query after parsing")
                return [], 0

            # Build base query
            stmt = select(Message)

            # Apply full-text search
            stmt = stmt.where(
                text("search_vector @@ to_tsquery('english', :query)")
            ).params(query=ts_query)

            # Apply filters
            if filters:
                conditions = self._build_filter_conditions(filters)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            # Add ranking
            rank_expr = text(
                "ts_rank_cd(search_vector, to_tsquery('english', :query))"
            ).params(query=ts_query)

            # Create selection with rank
            stmt_with_rank = (
                select(Message, rank_expr.label("rank"))
                .select_from(Message)
                .where(text("search_vector @@ to_tsquery('english', :query)"))
                .params(query=ts_query)
            )

            # Apply filters to ranked query
            if filters:
                conditions = self._build_filter_conditions(filters)
                if conditions:
                    stmt_with_rank = stmt_with_rank.where(and_(*conditions))

            # Order by rank (descending)
            stmt_with_rank = stmt_with_rank.order_by(text("rank DESC"))

            # Get total count (before pagination)
            count_stmt = (
                select(func.count())
                .select_from(Message)
                .where(text("search_vector @@ to_tsquery('english', :query)"))
                .params(query=ts_query)
            )

            if filters:
                conditions = self._build_filter_conditions(filters)
                if conditions:
                    count_stmt = count_stmt.where(and_(*conditions))

            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar() or 0

            # Apply pagination
            stmt_with_rank = stmt_with_rank.limit(limit).offset(offset)

            # Execute search
            result = await db.execute(stmt_with_rank)
            rows = result.all()

            # Build results
            results = []
            for row in rows:
                message = row[0]
                rank = row[1]

                # Generate headline (highlighted snippet) if requested
                headline = None
                if include_highlights:
                    headline = await self._generate_headline(message, ts_query, db)

                results.append(
                    FullTextSearchResult(
                        message_id=message.id,
                        platform=message.platform,
                        platform_message_id=message.platform_message_id,
                        thread_id=message.thread_id,
                        sender_id=message.sender_id,
                        content=message.content,
                        timestamp=message.timestamp,
                        rank=rank,
                        headline=headline,
                    )
                )

            logger.info(
                f"Full-text search returned {len(results)} results "
                f"(total: {total_count})"
            )
            return results, total_count

        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            return [], 0

    def _parse_query(self, query: str) -> str:
        """
        Parse and sanitize search query for PostgreSQL tsquery.

        Converts simple search terms into a proper tsquery expression.

        Args:
            query: Raw search query

        Returns:
            Sanitized tsquery expression
        """
        if not query or not query.strip():
            return ""

        # Remove special characters that could break tsquery
        query = query.strip()

        # Split into words
        words = query.split()

        # Sanitize each word (remove special chars except *)
        sanitized_words = []
        for word in words:
            # Remove characters that aren't alphanumeric, *, or -
            word = "".join(c for c in word if c.isalnum() or c in ("*", "-", "_"))
            if word:
                sanitized_words.append(word)

        if not sanitized_words:
            return ""

        # Join with & (AND operator) for tsquery
        ts_query = " & ".join(sanitized_words)

        logger.debug(f"Parsed query: '{query}' -> '{ts_query}'")
        return ts_query

    def _build_filter_conditions(self, filters: FullTextSearchFilter) -> list:
        """
        Build SQLAlchemy filter conditions from search filters.

        Args:
            filters: Search filters

        Returns:
            List of SQLAlchemy conditions
        """
        conditions = []

        if filters.platforms:
            conditions.append(Message.platform.in_(filters.platforms))

        if filters.thread_ids:
            conditions.append(Message.thread_id.in_(filters.thread_ids))

        if filters.contact_ids:
            # Filter by sender being one of the contacts
            conditions.append(Message.sender_id.in_(filters.contact_ids))

        if filters.start_date:
            conditions.append(Message.timestamp >= filters.start_date)

        if filters.end_date:
            conditions.append(Message.timestamp <= filters.end_date)

        if filters.has_attachments is not None:
            if filters.has_attachments:
                # Has attachments
                conditions.append(
                    text(
                        "EXISTS (SELECT 1 FROM attachments WHERE attachments.message_id = messages.id)"
                    )
                )
            else:
                # No attachments
                conditions.append(
                    text(
                        "NOT EXISTS (SELECT 1 FROM attachments WHERE attachments.message_id = messages.id)"
                    )
                )

        return conditions

    async def _generate_headline(
        self, message: Message, ts_query: str, db: AsyncSession
    ) -> Optional[str]:
        """
        Generate highlighted headline/snippet for search result.

        Uses PostgreSQL's ts_headline function to highlight matching terms.

        Args:
            message: Message object
            ts_query: tsquery expression
            db: Database session

        Returns:
            Highlighted snippet or None
        """
        try:
            # Get message text content
            text_content = message.content.get("text", "")

            if not text_content:
                return None

            # Use PostgreSQL's ts_headline function
            headline_query = text("""
                SELECT ts_headline(
                    'english',
                    :text,
                    to_tsquery('english', :query),
                    'MaxWords=20, MinWords=10, ShortWord=3, HighlightAll=false'
                )
            """).bindparams(text=text_content, query=ts_query)

            result = await db.execute(headline_query)
            headline = result.scalar()

            return headline

        except Exception as e:
            logger.error(f"Failed to generate headline: {e}")
            return None

    async def search_in_thread(
        self,
        query: str,
        thread_id: str,
        db: AsyncSession,
        limit: int = 50,
    ) -> tuple[list[FullTextSearchResult], int]:
        """Search within a specific thread."""
        return await self.search(
            query, db, limit=limit, filters=FullTextSearchFilter(thread_ids=[thread_id])
        )

    async def search_by_platform(
        self,
        query: str,
        platform: str,
        db: AsyncSession,
        limit: int = 50,
    ) -> tuple[list[FullTextSearchResult], int]:
        """Search within a specific platform."""
        return await self.search(
            query, db, limit=limit, filters=FullTextSearchFilter(platforms=[platform])
        )

    async def search_by_contact(
        self,
        query: str,
        contact_id: UUID,
        db: AsyncSession,
        limit: int = 50,
    ) -> tuple[list[FullTextSearchResult], int]:
        """Search messages from/to a specific contact."""
        return await self.search(
            query,
            db,
            limit=limit,
            filters=FullTextSearchFilter(contact_ids=[contact_id]),
        )

    async def search_by_date_range(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession,
        limit: int = 50,
    ) -> tuple[list[FullTextSearchResult], int]:
        """Search within a date range."""
        return await self.search(
            query,
            db,
            limit=limit,
            filters=FullTextSearchFilter(start_date=start_date, end_date=end_date),
        )


# Global service instance
_fulltext_search_service: Optional[FullTextSearchService] = None


def get_fulltext_search_service() -> FullTextSearchService:
    """
    Get the global full-text search service instance.

    Returns:
        Full-text search service
    """
    global _fulltext_search_service

    if _fulltext_search_service is None:
        _fulltext_search_service = FullTextSearchService()

    return _fulltext_search_service


__all__ = [
    "FullTextSearchService",
    "FullTextSearchFilter",
    "FullTextSearchResult",
    "get_fulltext_search_service",
]
