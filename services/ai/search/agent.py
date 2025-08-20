"""
Hybrid Search Agent combining lexical and vector search capabilities.

This is the main search agent that orchestrates query processing,
lexical search, vector search, and result fusion to provide
intelligent search results across all message data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .types import (
    SearchQuery, SearchResponse, SearchResult, SearchStats,
    FusionWeights, QueryIntent, SearchFilters
)
from .query_processor import QueryProcessor
from .lexical_search import LexicalSearchEngine
from .vector_search import VectorSearchEngine
from .result_fusion import SearchResultFusion

logger = logging.getLogger(__name__)


class HybridSearchAgent:
    """
    Advanced hybrid search agent combining lexical and vector search.

    Provides intelligent search capabilities with natural language query
    processing, intent detection, and sophisticated result fusion.
    """

    def __init__(self):
        """Initialize the hybrid search agent."""
        self.query_processor = QueryProcessor()
        self.lexical_engine = LexicalSearchEngine()
        self.vector_engine = VectorSearchEngine()
        self.fusion_engine = SearchResultFusion()

        # Search statistics
        self.stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "average_response_time": 0.0,
            "intent_distribution": {},
            "last_search": None
        }

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all search components."""
        try:
            await self.query_processor.initialize()
            await self.vector_engine.initialize()

            self._initialized = True
            logger.info("HybridSearchAgent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize HybridSearchAgent: {e}")
            raise

    async def search(
        self,
        query_text: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
        offset: int = 0,
        fusion_weights: Optional[FusionWeights] = None,
        include_suggestions: bool = True,
        include_facets: bool = False
    ) -> SearchResponse:
        """
        Perform hybrid search combining lexical and vector search.

        Args:
            query_text: The search query text
            filters: Optional search filters
            limit: Maximum number of results to return
            offset: Offset for pagination
            fusion_weights: Optional custom fusion weights
            include_suggestions: Whether to include search suggestions
            include_facets: Whether to include search facets

        Returns:
            Complete search response with results and metadata
        """
        start_time = datetime.utcnow()

        try:
            if not self._initialized:
                await self.initialize()

            # Create search query object
            query = SearchQuery(
                text=query_text,
                filters=filters,
                limit=limit,
                offset=offset
            )

            # Process the query
            processed_query = await self.query_processor.process_query(query)

            # Perform parallel searches
            lexical_results, vector_results = await self._perform_parallel_search(
                processed_query, fusion_weights
            )

            # Fuse results
            fused_results = self.fusion_engine.fuse_results(
                lexical_results, vector_results, processed_query, fusion_weights
            )

            # Apply final filtering and pagination
            final_results = self._apply_final_filtering(
                fused_results, processed_query)

            # Generate suggestions if requested
            suggestions = None
            if include_suggestions:
                suggestions = self.query_processor.generate_search_suggestions(
                    query_text)

            # Generate facets if requested
            facets = None
            if include_facets:
                facets = self._generate_facets(final_results)

            # Calculate processing time
            processing_time = (datetime.utcnow() -
                               start_time).total_seconds() * 1000

            # Create search statistics
            search_stats = SearchStats(
                total_results=len(final_results),
                lexical_results=len(lexical_results),
                vector_results=len(vector_results),
                processing_time_ms=processing_time,
                query_intent=processed_query.intent,
                filters_applied=self._count_applied_filters(
                    processed_query.filters)
            )

            # Update internal statistics
            self._update_stats(processed_query, search_stats, success=True)

            # Create response
            response = SearchResponse(
                results=final_results,
                stats=search_stats,
                query=processed_query,
                suggestions=suggestions,
                facets=facets
            )

            logger.info(
                f"Search completed: {len(final_results)} results in {processing_time:.1f}ms")

            return response

        except Exception as e:
            processing_time = (datetime.utcnow() -
                               start_time).total_seconds() * 1000
            logger.error(f"Search failed after {processing_time:.1f}ms: {e}")

            # Update failure statistics
            self._update_stats(query, None, success=False)

            # Return empty response on failure
            return SearchResponse(
                results=[],
                stats=SearchStats(processing_time_ms=processing_time),
                query=query
            )

    async def _perform_parallel_search(
        self,
        query: SearchQuery,
        fusion_weights: Optional[FusionWeights] = None
    ) -> tuple[List[SearchResult], List[SearchResult]]:
        """Perform lexical and vector searches in parallel."""
        import asyncio

        try:
            # Create boost factors from fusion weights
            boost_factors = {}
            if fusion_weights:
                boost_factors = {
                    "recency": fusion_weights.recency_boost,
                    "relevance": fusion_weights.relevance_boost,
                    **fusion_weights.platform_boost,
                    **fusion_weights.participant_boost
                }

            # Perform searches in parallel
            lexical_task = self.lexical_engine.search(query, boost_factors)
            vector_task = self.vector_engine.search(query, boost_factors)

            lexical_results, vector_results = await asyncio.gather(
                lexical_task, vector_task, return_exceptions=True
            )

            # Handle exceptions
            if isinstance(lexical_results, Exception):
                logger.error(f"Lexical search failed: {lexical_results}")
                lexical_results = []

            if isinstance(vector_results, Exception):
                logger.error(f"Vector search failed: {vector_results}")
                vector_results = []

            return lexical_results, vector_results

        except Exception as e:
            logger.error(f"Parallel search failed: {e}")
            return [], []

    def _apply_final_filtering(
        self,
        results: List[SearchResult],
        query: SearchQuery
    ) -> List[SearchResult]:
        """Apply final filtering and pagination to results."""
        try:
            # Apply confidence filtering if specified
            if query.filters and query.filters.min_confidence:
                results = [
                    r for r in results
                    if r.ranking.combined_score >= query.filters.min_confidence
                ]

            # Apply pagination
            start_idx = query.offset
            end_idx = start_idx + query.limit

            return results[start_idx:end_idx]

        except Exception as e:
            logger.error(f"Final filtering failed: {e}")
            return results[:query.limit]

    def _generate_facets(self, results: List[SearchResult]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate search facets from results."""
        try:
            facets = {}

            # Platform facets
            platform_counts = {}
            for result in results:
                if result.platform:
                    platform_counts[result.platform] = platform_counts.get(
                        result.platform, 0) + 1

            facets["platforms"] = [
                {"value": platform, "count": count}
                for platform, count in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            # Result type facets
            type_counts = {}
            for result in results:
                type_counts[result.type.value] = type_counts.get(
                    result.type.value, 0) + 1

            facets["types"] = [
                {"value": result_type, "count": count}
                for result_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            # Time period facets
            time_periods = {"today": 0, "this_week": 0,
                            "this_month": 0, "older": 0}
            now = datetime.utcnow()

            for result in results:
                days_old = (now - result.timestamp).days
                if days_old == 0:
                    time_periods["today"] += 1
                elif days_old <= 7:
                    time_periods["this_week"] += 1
                elif days_old <= 30:
                    time_periods["this_month"] += 1
                else:
                    time_periods["older"] += 1

            facets["time_periods"] = [
                {"value": period, "count": count}
                for period, count in time_periods.items() if count > 0
            ]

            return facets

        except Exception as e:
            logger.error(f"Facet generation failed: {e}")
            return {}

    def _count_applied_filters(self, filters: Optional[SearchFilters]) -> int:
        """Count the number of applied filters."""
        if not filters:
            return 0

        count = 0
        if filters.platforms:
            count += 1
        if filters.participants:
            count += 1
        if filters.date_from or filters.date_to:
            count += 1
        if filters.thread_ids:
            count += 1
        if filters.entity_types:
            count += 1
        if filters.has_attachments is not None:
            count += 1
        if filters.content_types:
            count += 1
        if filters.min_confidence is not None:
            count += 1

        return count

    def _update_stats(
        self,
        query: SearchQuery,
        search_stats: Optional[SearchStats],
        success: bool
    ) -> None:
        """Update internal search statistics."""
        try:
            self.stats["total_searches"] += 1

            if success:
                self.stats["successful_searches"] += 1

                if search_stats:
                    # Update average response time
                    current_avg = self.stats["average_response_time"]
                    total_searches = self.stats["successful_searches"]
                    new_avg = ((current_avg * (total_searches - 1)) +
                               search_stats.processing_time_ms) / total_searches
                    self.stats["average_response_time"] = new_avg

                    # Update intent distribution
                    if query.intent:
                        intent_key = query.intent.value
                        self.stats["intent_distribution"][intent_key] = (
                            self.stats["intent_distribution"].get(
                                intent_key, 0) + 1
                        )
            else:
                self.stats["failed_searches"] += 1

            self.stats["last_search"] = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to update search statistics: {e}")

    async def search_commitments(
        self,
        person: Optional[str] = None,
        topic: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 20
    ) -> SearchResponse:
        """
        Specialized search for commitments and promises.

        Args:
            person: Optional person name to filter by
            topic: Optional topic to filter by
            timeframe: Optional timeframe (e.g., "last week", "this month")
            limit: Maximum number of results

        Returns:
            Search response focused on commitments
        """
        # Build commitment-focused query
        query_parts = ["commitments", "promises", "agreed to"]

        if person:
            query_parts.append(f"with {person}")
        if topic:
            query_parts.append(f"about {topic}")
        if timeframe:
            query_parts.append(timeframe)

        query_text = " ".join(query_parts)

        # Create filters for commitment search
        filters = SearchFilters(
            entity_types=["commitment", "task", "deadline"]
        )

        if person:
            filters.participants = [person]

        # Use commitment-specific fusion weights
        fusion_weights = FusionWeights(
            lexical_weight=0.7,  # Favor lexical for specific commitment terms
            vector_weight=0.3,
            recency_boost=0.2,   # Recent commitments are more important
            relevance_boost=0.3
        )

        return await self.search(
            query_text=query_text,
            filters=filters,
            limit=limit,
            fusion_weights=fusion_weights
        )

    async def search_shared_files(
        self,
        contact: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: int = 20
    ) -> SearchResponse:
        """
        Specialized search for shared files and attachments.

        Args:
            contact: Optional contact name to filter by
            file_type: Optional file type (e.g., "pdf", "image")
            limit: Maximum number of results

        Returns:
            Search response focused on shared files
        """
        query_parts = ["files", "attachments", "shared"]

        if contact:
            query_parts.append(f"with {contact}")
        if file_type:
            query_parts.append(file_type)

        query_text = " ".join(query_parts)

        # Create filters for file search
        filters = SearchFilters(
            has_attachments=True
        )

        if contact:
            filters.participants = [contact]
        if file_type:
            filters.content_types = [file_type]

        # Use file-specific fusion weights
        fusion_weights = FusionWeights(
            lexical_weight=0.8,  # Favor lexical for file names and types
            vector_weight=0.2,
            recency_boost=0.1,
            relevance_boost=0.2
        )

        return await self.search(
            query_text=query_text,
            filters=filters,
            limit=limit,
            fusion_weights=fusion_weights
        )

    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get comprehensive search statistics."""
        try:
            # Add fusion statistics if available
            fusion_stats = {}
            if hasattr(self.fusion_engine, 'get_fusion_statistics'):
                # This would require storing recent fusion results
                pass

            return {
                **self.stats,
                "fusion_statistics": fusion_stats,
                "component_status": {
                    "query_processor": "initialized" if self.query_processor.ai_engine else "basic",
                    "lexical_engine": "ready",
                    "vector_engine": "initialized" if self.vector_engine.vector_db else "not_initialized",
                    "fusion_engine": "ready"
                }
            }

        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return self.stats

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all search components."""
        try:
            health_status = {
                "status": "healthy",
                "components": {},
                "last_check": datetime.utcnow().isoformat()
            }

            # Check vector engine
            if self.vector_engine.vector_db:
                vector_health = await self.vector_engine.vector_db.health_check()
                health_status["components"]["vector_engine"] = vector_health
            else:
                health_status["components"]["vector_engine"] = {
                    "status": "not_initialized"}

            # Check query processor (AI engine)
            if self.query_processor.ai_engine:
                # Would need to implement health check in AI engine
                health_status["components"]["query_processor"] = {
                    "status": "healthy"}
            else:
                health_status["components"]["query_processor"] = {
                    "status": "basic_mode"}

            # Check lexical engine (always available)
            health_status["components"]["lexical_engine"] = {
                "status": "healthy"}

            # Check fusion engine (always available)
            health_status["components"]["fusion_engine"] = {
                "status": "healthy"}

            # Overall health
            component_statuses = [
                comp.get("status", "unknown")
                for comp in health_status["components"].values()
            ]

            if any(status in ["unhealthy", "error"] for status in component_statuses):
                health_status["status"] = "degraded"
            elif any(status in ["not_initialized", "basic_mode"] for status in component_statuses):
                health_status["status"] = "limited"

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
