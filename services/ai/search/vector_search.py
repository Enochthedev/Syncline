"""
Vector search engine using ChromaDB for semantic similarity search.

This module provides semantic search capabilities using embeddings
stored in the vector database with metadata filtering.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from services.vector_db.chroma_client import get_vector_db
from services.vector_db.types import VectorSearchQuery, VectorCollectionType
from services.ai.embeddings import get_embedding_service

from .types import SearchQuery, SearchResult, SearchResultType, SearchRanking, SearchFilters

logger = logging.getLogger(__name__)


class VectorSearchEngine:
    """
    Vector-based semantic search engine using ChromaDB.

    Provides semantic similarity search using embeddings with
    metadata filtering and relevance scoring.
    """

    def __init__(self):
        """Initialize the vector search engine."""
        self.vector_db = None
        self.embedding_service = None

    async def initialize(self) -> None:
        """Initialize vector database and embedding service."""
        try:
            self.vector_db = await get_vector_db()
            self.embedding_service = await get_embedding_service()
            logger.info("VectorSearchEngine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize VectorSearchEngine: {e}")
            raise

    async def search(
        self,
        query: SearchQuery,
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """
        Perform vector search using semantic similarity.

        Args:
            query: The search query with filters
            boost_factors: Optional boost factors for ranking

        Returns:
            List of search results with vector similarity scores
        """
        try:
            if not self.vector_db or not self.embedding_service:
                await self.initialize()

            results = []

            # Generate embedding for the query
            query_embedding = await self._generate_query_embedding(query)
            if not query_embedding:
                return []

            # Search messages
            message_results = await self._search_messages(query, query_embedding, boost_factors)
            results.extend(message_results)

            # Search summaries
            summary_results = await self._search_summaries(query, query_embedding, boost_factors)
            results.extend(summary_results)

            # Search entities if relevant
            if self._should_search_entities(query):
                entity_results = await self._search_entities(query, query_embedding, boost_factors)
                results.extend(entity_results)

            # Sort by vector score
            results.sort(key=lambda r: r.ranking.vector_score, reverse=True)

            # Apply limit and offset
            start_idx = query.offset
            end_idx = start_idx + query.limit

            return results[start_idx:end_idx]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _generate_query_embedding(self, query: SearchQuery) -> Optional[List[float]]:
        """Generate embedding for the search query."""
        try:
            search_text = query.processed_text or query.text

            embedding_result = await self.embedding_service.generate_embedding(
                text=search_text,
                use_cache=True
            )

            if embedding_result and embedding_result.embedding:
                return embedding_result.embedding

            return None

        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return None

    async def _search_messages(
        self,
        query: SearchQuery,
        query_embedding: List[float],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """Search message embeddings for semantic similarity."""
        try:
            # Build metadata filters
            metadata_filters = self._build_metadata_filters(query.filters)

            # Create vector search query
            vector_query = VectorSearchQuery(
                collection_type=VectorCollectionType.MESSAGES,
                n_results=query.limit,
                where=metadata_filters
            )

            # Perform vector search
            search_results = await self.vector_db.search_similar(
                query=vector_query,
                embedding=query_embedding
            )

            # Convert to SearchResult objects
            results = []
            for i, (doc_id, distance, metadata) in enumerate(zip(
                search_results.get("ids", []),
                search_results.get("distances", []),
                search_results.get("metadatas", [])
            )):
                search_result = self._create_message_vector_result(
                    doc_id, distance, metadata, boost_factors
                )
                if search_result:
                    results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Vector message search failed: {e}")
            return []

    async def _search_summaries(
        self,
        query: SearchQuery,
        query_embedding: List[float],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """Search summary embeddings for semantic similarity."""
        try:
            # Build metadata filters for summaries
            metadata_filters = {}
            if query.filters:
                if query.filters.date_from:
                    metadata_filters["timestamp"] = {
                        "$gte": query.filters.date_from.isoformat()}
                if query.filters.date_to:
                    metadata_filters["timestamp"] = {
                        "$lte": query.filters.date_to.isoformat()}

            # Create vector search query
            vector_query = VectorSearchQuery(
                collection_type=VectorCollectionType.SUMMARIES,
                n_results=query.limit // 2,  # Fewer summary results
                where=metadata_filters
            )

            # Perform vector search
            search_results = await self.vector_db.search_similar(
                query=vector_query,
                embedding=query_embedding
            )

            # Convert to SearchResult objects
            results = []
            for doc_id, distance, metadata in zip(
                search_results.get("ids", []),
                search_results.get("distances", []),
                search_results.get("metadatas", [])
            ):
                search_result = self._create_summary_vector_result(
                    doc_id, distance, metadata, boost_factors
                )
                if search_result:
                    results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Vector summary search failed: {e}")
            return []

    async def _search_entities(
        self,
        query: SearchQuery,
        query_embedding: List[float],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[SearchResult]:
        """Search entity embeddings for semantic similarity."""
        try:
            # Build metadata filters for entities
            metadata_filters = {}
            if query.filters and query.filters.entity_types:
                metadata_filters["entity_type"] = {
                    "$in": query.filters.entity_types}

            # Create vector search query
            vector_query = VectorSearchQuery(
                collection_type=VectorCollectionType.ENTITIES,
                n_results=query.limit // 4,  # Even fewer entity results
                where=metadata_filters
            )

            # Perform vector search
            search_results = await self.vector_db.search_similar(
                query=vector_query,
                embedding=query_embedding
            )

            # Convert to SearchResult objects
            results = []
            for doc_id, distance, metadata in zip(
                search_results.get("ids", []),
                search_results.get("distances", []),
                search_results.get("metadatas", [])
            ):
                search_result = self._create_entity_vector_result(
                    doc_id, distance, metadata, boost_factors
                )
                if search_result:
                    results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Vector entity search failed: {e}")
            return []

    def _build_metadata_filters(self, filters: Optional[SearchFilters]) -> Dict[str, Any]:
        """Build metadata filters for vector search."""
        metadata_filters = {}

        if not filters:
            return metadata_filters

        try:
            # Platform filter
            if filters.platforms:
                metadata_filters["platform"] = {"$in": filters.platforms}

            # Date filters
            if filters.date_from:
                metadata_filters["timestamp"] = {
                    "$gte": filters.date_from.isoformat()}
            if filters.date_to:
                if "timestamp" in metadata_filters:
                    metadata_filters["timestamp"]["$lte"] = filters.date_to.isoformat(
                    )
                else:
                    metadata_filters["timestamp"] = {
                        "$lte": filters.date_to.isoformat()}

            # Thread filter
            if filters.thread_ids:
                metadata_filters["thread_id"] = {
                    "$in": [str(tid) for tid in filters.thread_ids]}

            # Participant filter (simplified - would need more complex logic for names)
            if filters.participants:
                # This is a simplified approach - in practice, you'd need to resolve
                # participant names to IDs first
                metadata_filters["sender_email"] = {
                    "$in": filters.participants}

            # Attachment filter
            if filters.has_attachments is not None:
                metadata_filters["has_attachments"] = filters.has_attachments

        except Exception as e:
            logger.error(f"Failed to build metadata filters: {e}")

        return metadata_filters

    def _create_message_vector_result(
        self,
        doc_id: str,
        distance: float,
        metadata: Dict[str, Any],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> Optional[SearchResult]:
        """Create a SearchResult from vector search results."""
        try:
            # Convert distance to similarity score (lower distance = higher similarity)
            similarity_score = max(0.0, 1.0 - distance)

            # Apply boost factors
            boosted_score = self._apply_vector_boost_factors(
                similarity_score, metadata, boost_factors or {}
            )

            ranking = SearchRanking(
                lexical_score=0.0,  # Will be set by fusion algorithm
                vector_score=boosted_score,
                combined_score=boosted_score,
                boost_factors=boost_factors or {},
                explanation=f"Vector similarity: {similarity_score:.3f}, distance: {distance:.3f}"
            )

            # Extract metadata
            message_id = doc_id.replace(
                "message_", "") if doc_id.startswith("message_") else doc_id

            # Create snippet from content preview
            content_preview = metadata.get("content_preview", "")
            snippet = content_preview[:200] + \
                "..." if len(content_preview) > 200 else content_preview

            # Parse timestamp
            timestamp_str = metadata.get("timestamp")
            timestamp = datetime.fromisoformat(
                timestamp_str) if timestamp_str else datetime.utcnow()

            return SearchResult(
                id=message_id,
                type=SearchResultType.MESSAGE,
                title=metadata.get("thread_title", "Message"),
                content=content_preview,
                snippet=snippet,
                metadata=metadata,
                ranking=ranking,
                timestamp=timestamp,
                platform=metadata.get("platform"),
                thread_id=UUID(metadata["thread_id"]) if metadata.get(
                    "thread_id") else None,
                participant_id=UUID(metadata["sender_id"]) if metadata.get(
                    "sender_id") else None
            )

        except Exception as e:
            logger.error(f"Failed to create message vector result: {e}")
            return None

    def _create_summary_vector_result(
        self,
        doc_id: str,
        distance: float,
        metadata: Dict[str, Any],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> Optional[SearchResult]:
        """Create a SearchResult from summary vector search results."""
        try:
            similarity_score = max(0.0, 1.0 - distance)

            ranking = SearchRanking(
                lexical_score=0.0,
                vector_score=similarity_score,
                combined_score=similarity_score,
                explanation=f"Summary vector similarity: {similarity_score:.3f}"
            )

            summary_id = doc_id.replace(
                "summary_", "") if doc_id.startswith("summary_") else doc_id

            content_preview = metadata.get("content_preview", "")
            snippet = content_preview[:150] + \
                "..." if len(content_preview) > 150 else content_preview

            timestamp_str = metadata.get("timestamp")
            timestamp = datetime.fromisoformat(
                timestamp_str) if timestamp_str else datetime.utcnow()

            return SearchResult(
                id=summary_id,
                type=SearchResultType.SUMMARY,
                title=f"{metadata.get('summary_type', 'Summary').title()} Summary",
                content=content_preview,
                snippet=snippet,
                metadata=metadata,
                ranking=ranking,
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"Failed to create summary vector result: {e}")
            return None

    def _create_entity_vector_result(
        self,
        doc_id: str,
        distance: float,
        metadata: Dict[str, Any],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> Optional[SearchResult]:
        """Create a SearchResult from entity vector search results."""
        try:
            similarity_score = max(0.0, 1.0 - distance)

            ranking = SearchRanking(
                lexical_score=0.0,
                vector_score=similarity_score,
                combined_score=similarity_score,
                explanation=f"Entity vector similarity: {similarity_score:.3f}"
            )

            entity_id = doc_id.replace(
                "entity_", "") if doc_id.startswith("entity_") else doc_id
            entity_value = metadata.get("entity_value", "Unknown")
            entity_type = metadata.get("entity_type", "unknown")

            return SearchResult(
                id=entity_id,
                type=SearchResultType.ENTITY,
                title=f"{entity_type.title()}: {entity_value}",
                content=f"Entity of type {entity_type}",
                snippet=f"{entity_type}: {entity_value}",
                metadata=metadata,
                ranking=ranking,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to create entity vector result: {e}")
            return None

    def _apply_vector_boost_factors(
        self,
        base_score: float,
        metadata: Dict[str, Any],
        boost_factors: Dict[str, float]
    ) -> float:
        """Apply boost factors to vector similarity scores."""
        boosted_score = base_score

        try:
            # Recency boost for vector results
            if "recency" in boost_factors and "timestamp" in metadata:
                timestamp_str = metadata["timestamp"]
                timestamp = datetime.fromisoformat(timestamp_str)
                days_old = (datetime.utcnow() - timestamp).days
                recency_multiplier = max(0.1, 1.0 - (days_old / 365.0))
                boosted_score *= (1.0 +
                                  boost_factors["recency"] * recency_multiplier)

            # Platform boost
            if "platform" in boost_factors and "platform" in metadata:
                platform = metadata["platform"]
                platform_boost = boost_factors.get(f"platform_{platform}", 0.0)
                boosted_score *= (1.0 + platform_boost)

            # Content length boost (longer content might be more relevant)
            if "content_length" in boost_factors and "content_preview" in metadata:
                content_length = len(metadata["content_preview"])
                if content_length > 100:  # Boost longer content
                    length_multiplier = min(2.0, content_length / 500.0)
                    boosted_score *= (1.0 +
                                      boost_factors["content_length"] * length_multiplier)

        except Exception as e:
            logger.error(f"Failed to apply vector boost factors: {e}")

        return boosted_score

    def _should_search_entities(self, query: SearchQuery) -> bool:
        """Determine if entity vector search should be performed."""
        from .types import QueryIntent

        # Search entities for specific intents
        return query.intent in [
            QueryIntent.PERSON_SEARCH,
            QueryIntent.TOPIC_SEARCH,
            QueryIntent.COMMITMENT_SEARCH
        ]
