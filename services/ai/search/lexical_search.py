"""
PostgreSQL full-text search engine for lexical search capabilities.

This module provides advanced full-text search using PostgreSQL's
built-in search features with ranking and filtering.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy import text, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models.message import Message
from db.models.thread import Thread
from db.models.participant import Participant
from db.models.entity import Entity, MessageEntity
from db.models.summary import Summary
from db.session import get_async_session

from .types import SearchQuery, SearchResult, SearchResultType, SearchRanking, SearchFilters

logger = logging.getLogger(__name__)


class LexicalSearchEngine:
    """
    PostgreSQL-based lexical search engine with full-text search capabilities.

    Provides ranked search results using PostgreSQL's tsvector and tsquery
    functionality with advanced filtering and ranking.
    """

    def __init__(self):
        """Initialize the lexical search engine."""
        self.session_factory = get_async_session

    async def search(
        self,
        query: SearchQuery,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """
        Perform lexical search using PostgreSQL full-text search.

        Args:
            query: The search query with filters
            boost_factors: Optional boost factors for ranking

        Returns:
            List of search results with lexical ranking
        """
        try:
            async with self.session_factory() as session:
                results = []

                # Search messages
                message_results = await self._search_messages(session, query, boost_factors)
                results.extend(message_results)

                # Search summaries
                summary_results = await self._search_summaries(session, query, boost_factors)
                results.extend(summary_results)

                # Search entities if relevant
                if self._should_search_entities(query):
                    entity_results = await self._search_entities(session, query, boost_factors)
                    results.extend(entity_results)

                # Sort by lexical score
                results.sort(
                    key=lambda r: r.ranking.lexical_score, reverse=True)

                # Apply limit and offset
                start_idx = query.offset
                end_idx = start_idx + query.limit

                return results[start_idx:end_idx]

        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return []

    async def _search_messages(
        self,
        session: AsyncSession,
        query: SearchQuery,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """Search messages using full-text search."""
        try:
            # Build the base query
            search_query = self._build_message_search_query(query)

            # Execute the query
            result = await session.execute(search_query)
            rows = result.fetchall()

            # Convert to SearchResult objects
            results = []
            for row in rows:
                search_result = await self._create_message_search_result(
                    row, query, boost_factors
                )
                if search_result:
                    results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Message search failed: {e}")
            return []

    def _build_message_search_query(self, query: SearchQuery):
        """Build PostgreSQL query for message search."""
        # Create tsquery from search text
        search_text = query.processed_text or query.text
        tsquery_text = self._create_tsquery(search_text)

        # Base query with full-text search
        base_query = text("""
            SELECT 
                m.id,
                m.platform,
                m.platform_message_id,
                m.thread_id,
                m.sender_id,
                m.content_text,
                m.content_html,
                m.content_markdown,
                m.timestamp,
                m.message_metadata,
                t.title as thread_title,
                p.display_name as sender_name,
                p.email as sender_email,
                ts_rank_cd(
                    to_tsvector('english', COALESCE(m.content_text, '') || ' ' || COALESCE(t.title, '')),
                    plainto_tsquery('english', :search_text)
                ) as rank_score,
                ts_headline(
                    'english',
                    COALESCE(m.content_text, ''),
                    plainto_tsquery('english', :search_text),
                    'MaxWords=50, MinWords=10, ShortWord=3, HighlightAll=false'
                ) as snippet
            FROM messages m
            LEFT JOIN threads t ON m.thread_id = t.id
            LEFT JOIN participants p ON m.sender_id = p.id
            WHERE to_tsvector('english', COALESCE(m.content_text, '') || ' ' || COALESCE(t.title, ''))
                  @@ plainto_tsquery('english', :search_text)
        """)

        # Add filters
        filter_conditions = []
        params = {"search_text": search_text}

        if query.filters:
            if query.filters.platforms:
                filter_conditions.append("m.platform = ANY(:platforms)")
                params["platforms"] = query.filters.platforms

            if query.filters.date_from:
                filter_conditions.append("m.timestamp >= :date_from")
                params["date_from"] = query.filters.date_from

            if query.filters.date_to:
                filter_conditions.append("m.timestamp <= :date_to")
                params["date_to"] = query.filters.date_to

            if query.filters.thread_ids:
                filter_conditions.append("m.thread_id = ANY(:thread_ids)")
                params["thread_ids"] = [str(tid)
                                        for tid in query.filters.thread_ids]

            if query.filters.participants:
                filter_conditions.append("""
                    (p.display_name ILIKE ANY(:participants) OR 
                     p.email ILIKE ANY(:participants))
                """)
                params["participants"] = [
                    f"%{name}%" for name in query.filters.participants]

            if query.filters.has_attachments is not None:
                if query.filters.has_attachments:
                    filter_conditions.append("""
                        EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id)
                    """)
                else:
                    filter_conditions.append("""
                        NOT EXISTS (SELECT 1 FROM attachments a WHERE a.message_id = m.id)
                    """)

        # Add filter conditions to query
        if filter_conditions:
            filter_clause = " AND " + " AND ".join(filter_conditions)
            query_text = str(base_query) + filter_clause
            base_query = text(query_text)

        # Add ordering and limit
        final_query = text(str(base_query) + """
            ORDER BY rank_score DESC, m.timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        params.update({
            "limit": query.limit * 2,  # Get more results for better ranking
            "offset": 0  # We'll handle offset in Python for better control
        })

        return final_query.params(**params)

    def _create_tsquery(self, search_text: str) -> str:
        """Create a PostgreSQL tsquery from search text."""
        # Clean and prepare search text
        words = search_text.strip().split()

        # Handle quoted phrases
        if '"' in search_text:
            # Keep quoted phrases intact
            return search_text

        # For multiple words, create OR query for better recall
        if len(words) > 1:
            return " | ".join(words)

        return search_text

    async def _create_message_search_result(
        self,
        row: Any,
        query: SearchQuery,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> Optional[SearchResult]:
        """Create a SearchResult from a database row."""
        try:
            # Calculate ranking
            base_score = float(row.rank_score) if row.rank_score else 0.0

            # Apply boost factors
            boosted_score = self._apply_boost_factors(
                base_score, row, boost_factors or {}
            )

            ranking = SearchRanking(
                lexical_score=boosted_score,
                vector_score=0.0,  # Will be set by fusion algorithm
                combined_score=boosted_score,
                boost_factors=boost_factors or {},
                explanation=f"Full-text search rank: {base_score:.3f}"
            )

            # Create snippet
            snippet = row.snippet if hasattr(
                row, 'snippet') and row.snippet else ""
            if not snippet and row.content_text:
                snippet = self._create_snippet(row.content_text, query.text)

            # Build metadata
            metadata = {
                "platform_message_id": row.platform_message_id,
                "thread_title": row.thread_title,
                "sender_name": row.sender_name,
                "sender_email": row.sender_email,
                "message_metadata": row.message_metadata or {}
            }

            return SearchResult(
                id=str(row.id),
                type=SearchResultType.MESSAGE,
                title=row.thread_title or f"Message from {row.sender_name or 'Unknown'}",
                content=row.content_text or "",
                snippet=snippet,
                metadata=metadata,
                ranking=ranking,
                timestamp=row.timestamp,
                platform=row.platform,
                thread_id=row.thread_id,
                participant_id=row.sender_id
            )

        except Exception as e:
            logger.error(f"Failed to create message search result: {e}")
            return None

    def _apply_boost_factors(
        self,
        base_score: float,
        row: Any,
        boost_factors: Dict[str, float]
    ) -> float:
        """Apply boost factors to the base search score."""
        boosted_score = base_score

        try:
            # Recency boost
            if "recency" in boost_factors and hasattr(row, 'timestamp'):
                days_old = (datetime.utcnow() - row.timestamp).days
                recency_multiplier = max(
                    0.1, 1.0 - (days_old / 365.0))  # Decay over a year
                boosted_score *= (1.0 +
                                  boost_factors["recency"] * recency_multiplier)

            # Platform boost
            if "platform" in boost_factors and hasattr(row, 'platform'):
                platform_boost = boost_factors.get(
                    f"platform_{row.platform}", 0.0)
                boosted_score *= (1.0 + platform_boost)

            # Sender boost
            if "sender" in boost_factors and hasattr(row, 'sender_email'):
                sender_boost = boost_factors.get(
                    f"sender_{row.sender_email}", 0.0)
                boosted_score *= (1.0 + sender_boost)

        except Exception as e:
            logger.error(f"Failed to apply boost factors: {e}")

        return boosted_score

    def _create_snippet(self, content: str, search_text: str, max_length: int = 200) -> str:
        """Create a search snippet from content."""
        if not content or not search_text:
            return content[:max_length] if content else ""

        # Find the first occurrence of any search term
        search_words = search_text.lower().split()
        content_lower = content.lower()

        best_pos = -1
        for word in search_words:
            pos = content_lower.find(word)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos

        if best_pos == -1:
            return content[:max_length]

        # Create snippet around the found position
        start = max(0, best_pos - max_length // 2)
        end = min(len(content), start + max_length)

        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    async def _search_summaries(
        self,
        session: AsyncSession,
        query: SearchQuery,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """Search summaries using full-text search."""
        try:
            search_text = query.processed_text or query.text

            # Build summary search query
            summary_query = text("""
                SELECT 
                    s.id,
                    s.type,
                    s.scope_type,
                    s.scope_id,
                    s.content,
                    s.key_points,
                    s.action_items,
                    s.timeframe_start,
                    s.timeframe_end,
                    s.created_at,
                    ts_rank_cd(
                        to_tsvector('english', s.content),
                        plainto_tsquery('english', :search_text)
                    ) as rank_score,
                    ts_headline(
                        'english',
                        s.content,
                        plainto_tsquery('english', :search_text),
                        'MaxWords=30, MinWords=5'
                    ) as snippet
                FROM summaries s
                WHERE to_tsvector('english', s.content) @@ plainto_tsquery('english', :search_text)
                ORDER BY rank_score DESC
                LIMIT :limit
            """).params(search_text=search_text, limit=query.limit // 2)

            result = await session.execute(summary_query)
            rows = result.fetchall()

            # Convert to SearchResult objects
            results = []
            for row in rows:
                search_result = self._create_summary_search_result(
                    row, boost_factors)
                if search_result:
                    results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Summary search failed: {e}")
            return []

    def _create_summary_search_result(
        self,
        row: Any,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> Optional[SearchResult]:
        """Create a SearchResult from a summary row."""
        try:
            base_score = float(row.rank_score) if row.rank_score else 0.0

            ranking = SearchRanking(
                lexical_score=base_score,
                vector_score=0.0,
                combined_score=base_score,
                explanation=f"Summary search rank: {base_score:.3f}"
            )

            metadata = {
                "summary_type": row.type,
                "scope_type": row.scope_type,
                "scope_id": str(row.scope_id) if row.scope_id else None,
                "key_points": row.key_points or [],
                "action_items": row.action_items or [],
                "timeframe_start": row.timeframe_start.isoformat() if row.timeframe_start else None,
                "timeframe_end": row.timeframe_end.isoformat() if row.timeframe_end else None
            }

            return SearchResult(
                id=str(row.id),
                type=SearchResultType.SUMMARY,
                title=f"{row.type.title()} Summary",
                content=row.content,
                snippet=row.snippet if hasattr(
                    row, 'snippet') else row.content[:200],
                metadata=metadata,
                ranking=ranking,
                timestamp=row.created_at
            )

        except Exception as e:
            logger.error(f"Failed to create summary search result: {e}")
            return None

    def _should_search_entities(self, query: SearchQuery) -> bool:
        """Determine if entity search should be performed."""
        # Search entities for specific intents
        return query.intent in [
            query.intent.PERSON_SEARCH,
            query.intent.TOPIC_SEARCH,
            query.intent.COMMITMENT_SEARCH
        ]

    async def _search_entities(
        self,
        session: AsyncSession,
        query: SearchQuery,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """Search entities for relevant matches."""
        try:
            search_text = query.processed_text or query.text

            entity_query = text("""
                SELECT DISTINCT
                    e.id,
                    e.type,
                    e.value,
                    e.normalized_value,
                    e.confidence,
                    e.metadata,
                    COUNT(me.message_id) as message_count,
                    similarity(e.value, :search_text) as similarity_score
                FROM entities e
                LEFT JOIN message_entities me ON e.id = me.entity_id
                WHERE e.value ILIKE :search_pattern
                   OR e.normalized_value ILIKE :search_pattern
                   OR similarity(e.value, :search_text) > 0.3
                GROUP BY e.id, e.type, e.value, e.normalized_value, e.confidence, e.metadata
                ORDER BY similarity_score DESC, message_count DESC
                LIMIT :limit
            """).params(
                search_text=search_text,
                search_pattern=f"%{search_text}%",
                limit=query.limit // 4
            )

            result = await session.execute(entity_query)
            rows = result.fetchall()

            # Convert to SearchResult objects
            results = []
            for row in rows:
                search_result = self._create_entity_search_result(row)
                if search_result:
                    results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return []

    def _create_entity_search_result(self, row: Any) -> Optional[SearchResult]:
        """Create a SearchResult from an entity row."""
        try:
            similarity_score = float(
                row.similarity_score) if row.similarity_score else 0.0

            ranking = SearchRanking(
                lexical_score=similarity_score,
                vector_score=0.0,
                combined_score=similarity_score,
                explanation=f"Entity similarity: {similarity_score:.3f}"
            )

            metadata = {
                "entity_type": row.type,
                "normalized_value": row.normalized_value,
                "confidence": row.confidence,
                "message_count": row.message_count,
                "entity_metadata": row.metadata or {}
            }

            return SearchResult(
                id=str(row.id),
                type=SearchResultType.ENTITY,
                title=f"{row.type.title()}: {row.value}",
                content=f"Entity found in {row.message_count} messages",
                snippet=f"{row.type}: {row.value}",
                metadata=metadata,
                ranking=ranking,
                timestamp=datetime.utcnow()  # Entities don't have timestamps
            )

        except Exception as e:
            logger.error(f"Failed to create entity search result: {e}")
            return None
