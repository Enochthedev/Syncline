"""
Semantic Search Engine

Provides semantic search capabilities using vector embeddings:
- Query embedding generation
- Vector similarity search
- Result ranking and filtering
- Hybrid search (semantic + metadata filters)
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.embedding import Embedding
from db.models.message import Message
from services.ai.embeddings import EmbeddingService, get_embedding_service
from services.vector_db.chroma_client import (
    ChromaDBClient,
    SearchResult,
    get_chroma_client,
)

logger = logging.getLogger(__name__)


class SearchFilter(BaseModel):
    """Filters for semantic search."""

    platforms: Optional[list[str]] = Field(
        default=None, description="Filter by platforms"
    )
    thread_ids: Optional[list[str]] = Field(
        default=None, description="Filter by thread IDs"
    )
    sender_ids: Optional[list[UUID]] = Field(
        default=None, description="Filter by sender IDs"
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Filter messages after this date"
    )
    end_date: Optional[datetime] = Field(
        default=None, description="Filter messages before this date"
    )
    min_score: Optional[float] = Field(
        default=None, description="Minimum similarity score"
    )


class MessageSearchResult(BaseModel):
    """Search result with message details."""

    message_id: UUID
    platform: str
    platform_message_id: str
    thread_id: Optional[str]
    sender_id: Optional[UUID]
    content: dict
    timestamp: datetime
    similarity_score: float
    distance: float

    class Config:
        """Pydantic config."""

        from_attributes = True


class SemanticSearchEngine:
    """
    Semantic search engine for messages.

    Provides functionality for:
    - Semantic search using vector embeddings
    - Filtering by metadata (platform, date, sender, etc.)
    - Result ranking and scoring
    - Hybrid search combining semantic and keyword search
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        chroma_client: Optional[ChromaDBClient] = None,
    ):
        """
        Initialize semantic search engine.

        Args:
            embedding_service: Embedding service for query embedding
            chroma_client: ChromaDB client for vector search
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.chroma_client = chroma_client or get_chroma_client()

        logger.info("Initialized SemanticSearchEngine")

    async def search(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 10,
        filters: Optional[SearchFilter] = None,
    ) -> list[MessageSearchResult]:
        """
        Perform semantic search for messages.

        Args:
            query: Search query text
            db: Database session
            limit: Maximum number of results
            filters: Optional filters for search

        Returns:
            List of search results with message details
        """
        try:
            logger.info(f"Performing semantic search: '{query}' (limit={limit})")

            # Generate embedding for query
            query_embedding = await self.embedding_service.generate_embedding(query)

            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []

            # Prepare metadata filters for ChromaDB
            where_filter = self._build_chroma_filter(filters)

            # Perform vector search in ChromaDB
            chroma_results = self.chroma_client.query(
                query_embeddings=[query_embedding],
                n_results=limit * 2,  # Get more results for filtering
                where=where_filter,
            )

            if not chroma_results:
                logger.info("No results found in vector search")
                return []

            # Extract message IDs from ChromaDB results
            message_ids = [UUID(result.id) for result in chroma_results]

            # Fetch full message details from database
            messages = await self._fetch_messages(db, message_ids, filters)

            # Combine ChromaDB results with message details
            results = self._combine_results(chroma_results, messages, filters)

            # Limit to requested number
            results = results[:limit]

            logger.info(f"Semantic search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def search_by_embedding(
        self,
        embedding: list[float],
        db: AsyncSession,
        limit: int = 10,
        filters: Optional[SearchFilter] = None,
    ) -> list[MessageSearchResult]:
        """
        Perform semantic search using a pre-computed embedding.

        Args:
            embedding: Query embedding vector
            db: Database session
            limit: Maximum number of results
            filters: Optional filters for search

        Returns:
            List of search results with message details
        """
        try:
            logger.info(f"Performing embedding-based search (limit={limit})")

            # Prepare metadata filters for ChromaDB
            where_filter = self._build_chroma_filter(filters)

            # Perform vector search in ChromaDB
            chroma_results = self.chroma_client.query(
                query_embeddings=[embedding],
                n_results=limit * 2,
                where=where_filter,
            )

            if not chroma_results:
                logger.info("No results found in vector search")
                return []

            # Extract message IDs
            message_ids = [UUID(result.id) for result in chroma_results]

            # Fetch full message details
            messages = await self._fetch_messages(db, message_ids, filters)

            # Combine results
            results = self._combine_results(chroma_results, messages, filters)

            # Limit to requested number
            results = results[:limit]

            logger.info(f"Embedding search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []

    async def find_similar_messages(
        self,
        message_id: UUID,
        db: AsyncSession,
        limit: int = 10,
        filters: Optional[SearchFilter] = None,
    ) -> list[MessageSearchResult]:
        """
        Find messages similar to a given message.

        Args:
            message_id: ID of the reference message
            db: Database session
            limit: Maximum number of results
            filters: Optional filters for search

        Returns:
            List of similar messages
        """
        try:
            logger.info(f"Finding messages similar to {message_id}")

            # Get embedding for the reference message
            embedding = await self.embedding_service.get_embedding(message_id, db)

            if not embedding or not embedding.vector:
                logger.error(f"No embedding found for message {message_id}")
                return []

            # Search using the message's embedding
            results = await self.search_by_embedding(
                embedding=embedding.vector,
                db=db,
                limit=limit + 1,  # +1 to account for the reference message itself
                filters=filters,
            )

            # Remove the reference message from results
            results = [r for r in results if r.message_id != message_id]

            # Limit to requested number
            results = results[:limit]

            logger.info(f"Found {len(results)} similar messages")
            return results

        except Exception as e:
            logger.error(f"Failed to find similar messages: {e}")
            return []

    async def search_in_thread(
        self, query: str, thread_id: str, db: AsyncSession, limit: int = 10
    ) -> list[MessageSearchResult]:
        """Search within a specific thread."""
        return await self.search(query, db, limit, SearchFilter(thread_ids=[thread_id]))

    async def search_by_platform(
        self, query: str, platform: str, db: AsyncSession, limit: int = 10
    ) -> list[MessageSearchResult]:
        """Search within a specific platform."""
        return await self.search(query, db, limit, SearchFilter(platforms=[platform]))

    async def search_by_date_range(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[MessageSearchResult]:
        """Search within a date range."""
        return await self.search(
            query, db, limit, SearchFilter(start_date=start_date, end_date=end_date)
        )

    def _build_chroma_filter(self, filters: Optional[SearchFilter]) -> Optional[dict]:
        """Build ChromaDB metadata filter from SearchFilter."""
        if not filters:
            return None

        where = {}

        # Platform and thread filters
        if filters.platforms:
            where["platform"] = (
                filters.platforms[0]
                if len(filters.platforms) == 1
                else {"$in": filters.platforms}
            )
        if filters.thread_ids:
            where["thread_id"] = (
                filters.thread_ids[0]
                if len(filters.thread_ids) == 1
                else {"$in": filters.thread_ids}
            )

        # Date range filters
        if filters.start_date or filters.end_date:
            where["timestamp"] = {}
            if filters.start_date:
                where["timestamp"]["$gte"] = filters.start_date.isoformat()
            if filters.end_date:
                where["timestamp"]["$lte"] = filters.end_date.isoformat()

        return where if where else None

    async def _fetch_messages(
        self,
        db: AsyncSession,
        message_ids: list[UUID],
        filters: Optional[SearchFilter] = None,
    ) -> dict[UUID, Message]:
        """Fetch messages from database by IDs with optional filters."""
        try:
            query = select(Message).where(Message.id.in_(message_ids))

            # Apply filters
            if filters:
                conditions = []
                if filters.platforms:
                    conditions.append(Message.platform.in_(filters.platforms))
                if filters.thread_ids:
                    conditions.append(Message.thread_id.in_(filters.thread_ids))
                if filters.sender_ids:
                    conditions.append(Message.sender_id.in_(filters.sender_ids))
                if filters.start_date:
                    conditions.append(Message.timestamp >= filters.start_date)
                if filters.end_date:
                    conditions.append(Message.timestamp <= filters.end_date)

                if conditions:
                    query = query.where(and_(*conditions))

            result = await db.execute(query)
            return {msg.id: msg for msg in result.scalars().all()}
        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            return {}

    def _combine_results(
        self,
        chroma_results: list[SearchResult],
        messages: dict[UUID, Message],
        filters: Optional[SearchFilter] = None,
    ) -> list[MessageSearchResult]:
        """Combine ChromaDB results with message details."""
        combined = []

        for cr in chroma_results:
            msg_id = UUID(cr.id)
            if msg_id not in messages:
                continue

            # Apply score filter
            if filters and filters.min_score and cr.score < filters.min_score:
                continue

            msg = messages[msg_id]
            combined.append(
                MessageSearchResult(
                    message_id=msg.id,
                    platform=msg.platform,
                    platform_message_id=msg.platform_message_id,
                    thread_id=msg.thread_id,
                    sender_id=msg.sender_id,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    similarity_score=cr.score,
                    distance=cr.distance,
                )
            )

        return combined

    async def health_check(self) -> dict[str, bool]:
        """
        Check health of semantic search components.

        Returns:
            Dictionary with health status
        """
        health = {
            "embedding_service": False,
            "chroma_client": False,
        }

        try:
            # Check embedding service
            embedding_health = await self.embedding_service.health_check()
            health["embedding_service"] = all(embedding_health.values())
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")

        try:
            # Check ChromaDB
            health["chroma_client"] = self.chroma_client.health_check()
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")

        return health


# Global service instance
_semantic_search_engine: Optional[SemanticSearchEngine] = None


def get_semantic_search_engine() -> SemanticSearchEngine:
    """
    Get the global semantic search engine instance.

    Returns:
        Semantic search engine
    """
    global _semantic_search_engine

    if _semantic_search_engine is None:
        _semantic_search_engine = SemanticSearchEngine()

    return _semantic_search_engine


__all__ = [
    "SemanticSearchEngine",
    "SearchFilter",
    "MessageSearchResult",
    "get_semantic_search_engine",
]
