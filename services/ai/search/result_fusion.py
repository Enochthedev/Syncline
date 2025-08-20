"""
Search result fusion algorithm for combining lexical and vector search results.

This module implements sophisticated algorithms for merging and ranking
results from different search engines with learned weights and boosting.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any

from .types import SearchResult, SearchRanking, FusionWeights, SearchQuery, QueryIntent

logger = logging.getLogger(__name__)


class SearchResultFusion:
    """
    Advanced search result fusion engine.

    Combines results from lexical and vector search engines using
    sophisticated ranking algorithms and learned weights.
    """

    def __init__(self):
        """Initialize the fusion engine."""
        # Default fusion weights - can be learned/tuned over time
        self.default_weights = FusionWeights(
            lexical_weight=0.6,
            vector_weight=0.4,
            recency_boost=0.1,
            relevance_boost=0.2
        )

        # Intent-specific weight adjustments
        self.intent_weight_adjustments = {
            QueryIntent.GENERAL_SEARCH: FusionWeights(0.6, 0.4),
            # Favor lexical for specific terms
            QueryIntent.COMMITMENT_SEARCH: FusionWeights(0.7, 0.3),
            QueryIntent.PERSON_SEARCH: FusionWeights(0.5, 0.5),     # Balanced
            # Favor semantic for topics
            QueryIntent.TOPIC_SEARCH: FusionWeights(0.4, 0.6),
            # Favor lexical for time queries
            QueryIntent.TIME_BASED_SEARCH: FusionWeights(0.8, 0.2),
            # Favor lexical for file names
            QueryIntent.FILE_SEARCH: FusionWeights(0.7, 0.3),
            QueryIntent.CONVERSATION_SEARCH: FusionWeights(
                0.3, 0.7)  # Favor semantic for conversations
        }

    def fuse_results(
        self,
        lexical_results: List[SearchResult],
        vector_results: List[SearchResult],
        query: SearchQuery,
        custom_weights: Optional[FusionWeights] = None
    ) -> List[SearchResult]:
        """
        Fuse lexical and vector search results into a unified ranked list.

        Args:
            lexical_results: Results from lexical search
            vector_results: Results from vector search
            query: Original search query for context
            custom_weights: Optional custom fusion weights

        Returns:
            Fused and ranked list of search results
        """
        try:
            # Determine fusion weights
            weights = self._get_fusion_weights(query, custom_weights)

            # Create result maps for efficient lookup
            lexical_map = {result.id: result for result in lexical_results}
            vector_map = {result.id: result for result in vector_results}

            # Get all unique result IDs
            all_ids = set(lexical_map.keys()) | set(vector_map.keys())

            # Fuse results
            fused_results = []
            for result_id in all_ids:
                fused_result = self._fuse_single_result(
                    result_id, lexical_map, vector_map, weights, query
                )
                if fused_result:
                    fused_results.append(fused_result)

            # Apply additional ranking factors
            fused_results = self._apply_ranking_boosts(
                fused_results, query, weights)

            # Sort by combined score
            fused_results.sort(
                key=lambda r: r.ranking.combined_score, reverse=True)

            # Remove duplicates and apply final filtering
            fused_results = self._deduplicate_results(fused_results)

            logger.debug(
                f"Fused {len(lexical_results)} lexical + {len(vector_results)} vector results into {len(fused_results)} final results")

            return fused_results

        except Exception as e:
            logger.error(f"Result fusion failed: {e}")
            # Fallback: return lexical results if fusion fails
            return lexical_results[:query.limit]

    def _get_fusion_weights(
        self,
        query: SearchQuery,
        custom_weights: Optional[FusionWeights] = None
    ) -> FusionWeights:
        """Determine the appropriate fusion weights for the query."""
        if custom_weights:
            return custom_weights.normalize()

        # Start with default weights
        weights = FusionWeights(
            lexical_weight=self.default_weights.lexical_weight,
            vector_weight=self.default_weights.vector_weight,
            recency_boost=self.default_weights.recency_boost,
            relevance_boost=self.default_weights.relevance_boost
        )

        # Adjust based on query intent
        if query.intent and query.intent in self.intent_weight_adjustments:
            intent_weights = self.intent_weight_adjustments[query.intent]
            weights.lexical_weight = intent_weights.lexical_weight
            weights.vector_weight = intent_weights.vector_weight

        # Adjust based on query characteristics
        weights = self._adjust_weights_by_query_characteristics(query, weights)

        return weights.normalize()

    def _adjust_weights_by_query_characteristics(
        self,
        query: SearchQuery,
        weights: FusionWeights
    ) -> FusionWeights:
        """Adjust weights based on query characteristics."""
        try:
            query_text = query.text.lower()

            # Favor lexical search for exact terms and names
            if any(char in query_text for char in ['"', "'", "@", "#"]):
                weights.lexical_weight += 0.2
                weights.vector_weight -= 0.2

            # Favor vector search for conceptual queries
            conceptual_words = ["about", "regarding",
                                "similar", "like", "related"]
            if any(word in query_text for word in conceptual_words):
                weights.vector_weight += 0.2
                weights.lexical_weight -= 0.2

            # Favor lexical for short, specific queries
            if len(query.text.split()) <= 2:
                weights.lexical_weight += 0.1
                weights.vector_weight -= 0.1

            # Favor vector for longer, descriptive queries
            elif len(query.text.split()) >= 6:
                weights.vector_weight += 0.1
                weights.lexical_weight -= 0.1

        except Exception as e:
            logger.error(
                f"Failed to adjust weights by query characteristics: {e}")

        return weights

    def _fuse_single_result(
        self,
        result_id: str,
        lexical_map: Dict[str, SearchResult],
        vector_map: Dict[str, SearchResult],
        weights: FusionWeights,
        query: SearchQuery
    ) -> Optional[SearchResult]:
        """Fuse a single result from lexical and vector sources."""
        try:
            lexical_result = lexical_map.get(result_id)
            vector_result = vector_map.get(result_id)

            # Determine the primary result (prefer lexical for metadata completeness)
            primary_result = lexical_result or vector_result
            if not primary_result:
                return None

            # Calculate combined scores
            lexical_score = lexical_result.ranking.lexical_score if lexical_result else 0.0
            vector_score = vector_result.ranking.vector_score if vector_result else 0.0

            # Apply fusion weights
            combined_score = (
                lexical_score * weights.lexical_weight +
                vector_score * weights.vector_weight
            )

            # Create fused ranking
            fused_ranking = SearchRanking(
                lexical_score=lexical_score,
                vector_score=vector_score,
                combined_score=combined_score,
                boost_factors=weights.__dict__.copy(),
                explanation=self._create_ranking_explanation(
                    lexical_score, vector_score, combined_score, weights
                )
            )

            # Create fused result based on primary result
            fused_result = SearchResult(
                id=primary_result.id,
                type=primary_result.type,
                title=primary_result.title,
                content=primary_result.content,
                snippet=primary_result.snippet,
                metadata=primary_result.metadata,
                ranking=fused_ranking,
                timestamp=primary_result.timestamp,
                platform=primary_result.platform,
                thread_id=primary_result.thread_id,
                participant_id=primary_result.participant_id,
                url=primary_result.url,
                context=primary_result.context
            )

            # Enhance with information from both sources
            if lexical_result and vector_result:
                fused_result = self._enhance_fused_result(
                    fused_result, lexical_result, vector_result)

            return fused_result

        except Exception as e:
            logger.error(f"Failed to fuse single result {result_id}: {e}")
            return None

    def _enhance_fused_result(
        self,
        fused_result: SearchResult,
        lexical_result: SearchResult,
        vector_result: SearchResult
    ) -> SearchResult:
        """Enhance fused result with information from both sources."""
        try:
            # Use the better snippet (longer and more informative)
            if len(vector_result.snippet) > len(lexical_result.snippet):
                fused_result.snippet = vector_result.snippet

            # Merge metadata
            merged_metadata = {**lexical_result.metadata,
                               **vector_result.metadata}
            merged_metadata["fusion_info"] = {
                "lexical_score": lexical_result.ranking.lexical_score,
                "vector_score": vector_result.ranking.vector_score,
                "sources": ["lexical", "vector"]
            }
            fused_result.metadata = merged_metadata

            # Use more complete content if available
            if len(vector_result.content) > len(lexical_result.content):
                fused_result.content = vector_result.content

        except Exception as e:
            logger.error(f"Failed to enhance fused result: {e}")

        return fused_result

    def _apply_ranking_boosts(
        self,
        results: List[SearchResult],
        query: SearchQuery,
        weights: FusionWeights
    ) -> List[SearchResult]:
        """Apply additional ranking boosts to fused results."""
        try:
            for result in results:
                boost_multiplier = 1.0

                # Recency boost
                if weights.recency_boost > 0:
                    recency_multiplier = self._calculate_recency_boost(
                        result.timestamp)
                    boost_multiplier += weights.recency_boost * recency_multiplier

                # Relevance boost based on result type and query intent
                if weights.relevance_boost > 0:
                    relevance_multiplier = self._calculate_relevance_boost(
                        result, query)
                    boost_multiplier += weights.relevance_boost * relevance_multiplier

                # Platform-specific boosts
                if result.platform and f"platform_{result.platform}" in weights.platform_boost:
                    platform_boost = weights.platform_boost[f"platform_{result.platform}"]
                    boost_multiplier += platform_boost

                # Apply the boost
                result.ranking.combined_score *= boost_multiplier

                # Update boost factors in ranking
                result.ranking.boost_factors.update({
                    "recency_boost": weights.recency_boost,
                    "relevance_boost": weights.relevance_boost,
                    "total_boost_multiplier": boost_multiplier
                })

        except Exception as e:
            logger.error(f"Failed to apply ranking boosts: {e}")

        return results

    def _calculate_recency_boost(self, timestamp: datetime) -> float:
        """Calculate recency boost multiplier (0.0 to 1.0)."""
        try:
            days_old = (datetime.utcnow() - timestamp).days

            # Boost recent content more
            if days_old <= 1:
                return 1.0  # Today/yesterday gets full boost
            elif days_old <= 7:
                return 0.8  # This week gets high boost
            elif days_old <= 30:
                return 0.5  # This month gets medium boost
            elif days_old <= 90:
                return 0.2  # Last 3 months gets small boost
            else:
                return 0.0  # Older content gets no recency boost

        except Exception as e:
            logger.error(f"Failed to calculate recency boost: {e}")
            return 0.0

    def _calculate_relevance_boost(self, result: SearchResult, query: SearchQuery) -> float:
        """Calculate relevance boost based on result type and query intent."""
        try:
            boost = 0.0

            # Boost based on query intent and result type alignment
            if query.intent == QueryIntent.COMMITMENT_SEARCH:
                if "commitment" in result.metadata.get("entity_types", []):
                    boost += 0.5
                if any(word in result.content.lower() for word in ["promise", "commit", "deadline", "due"]):
                    boost += 0.3

            elif query.intent == QueryIntent.PERSON_SEARCH:
                if result.type == SearchResultType.MESSAGE:
                    boost += 0.3  # Messages are more relevant for person searches
                if query.filters and query.filters.participants:
                    # Check if result involves the searched person
                    for participant in query.filters.participants:
                        if participant.lower() in result.content.lower():
                            boost += 0.4

            elif query.intent == QueryIntent.FILE_SEARCH:
                if result.metadata.get("has_attachments"):
                    boost += 0.6
                if any(ext in result.content.lower() for ext in [".pdf", ".doc", ".jpg", ".png"]):
                    boost += 0.3

            # Boost results with higher confidence entities
            entity_confidence = result.metadata.get("entity_confidence", 0.0)
            if entity_confidence > 0.8:
                boost += 0.2

            return min(1.0, boost)  # Cap at 1.0

        except Exception as e:
            logger.error(f"Failed to calculate relevance boost: {e}")
            return 0.0

    def _create_ranking_explanation(
        self,
        lexical_score: float,
        vector_score: float,
        combined_score: float,
        weights: FusionWeights
    ) -> str:
        """Create human-readable explanation of ranking."""
        try:
            explanation_parts = []

            if lexical_score > 0:
                explanation_parts.append(
                    f"Lexical: {lexical_score:.3f} (weight: {weights.lexical_weight:.2f})")

            if vector_score > 0:
                explanation_parts.append(
                    f"Vector: {vector_score:.3f} (weight: {weights.vector_weight:.2f})")

            explanation_parts.append(f"Combined: {combined_score:.3f}")

            return " | ".join(explanation_parts)

        except Exception as e:
            logger.error(f"Failed to create ranking explanation: {e}")
            return f"Combined score: {combined_score:.3f}"

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results, keeping the highest-scored version."""
        seen_ids = set()
        deduplicated = []

        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                deduplicated.append(result)

        return deduplicated

    def learn_weights_from_feedback(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        user_interactions: Dict[str, Any]
    ) -> FusionWeights:
        """
        Learn and adjust fusion weights based on user feedback.

        This is a placeholder for a machine learning approach to optimize
        fusion weights based on user interactions (clicks, dwell time, etc.).
        """
        # Placeholder implementation - in practice, this would use ML
        # to learn optimal weights based on user behavior

        current_weights = self._get_fusion_weights(query)

        # Simple heuristic adjustments based on interaction patterns
        if user_interactions.get("clicked_lexical_results", 0) > user_interactions.get("clicked_vector_results", 0):
            current_weights.lexical_weight += 0.05
            current_weights.vector_weight -= 0.05
        elif user_interactions.get("clicked_vector_results", 0) > user_interactions.get("clicked_lexical_results", 0):
            current_weights.vector_weight += 0.05
            current_weights.lexical_weight -= 0.05

        return current_weights.normalize()

    def get_fusion_statistics(
        self,
        lexical_results: List[SearchResult],
        vector_results: List[SearchResult],
        fused_results: List[SearchResult]
    ) -> Dict[str, Any]:
        """Get statistics about the fusion process."""
        try:
            lexical_ids = {r.id for r in lexical_results}
            vector_ids = {r.id for r in vector_results}
            fused_ids = {r.id for r in fused_results}

            overlap = len(lexical_ids & vector_ids)
            lexical_only = len(lexical_ids - vector_ids)
            vector_only = len(vector_ids - lexical_ids)

            return {
                "lexical_results_count": len(lexical_results),
                "vector_results_count": len(vector_results),
                "fused_results_count": len(fused_results),
                "overlap_count": overlap,
                "lexical_only_count": lexical_only,
                "vector_only_count": vector_only,
                "overlap_percentage": (overlap / max(len(lexical_ids | vector_ids), 1)) * 100,
                "fusion_effectiveness": len(fused_ids) / max(len(lexical_ids | vector_ids), 1)
            }

        except Exception as e:
            logger.error(f"Failed to calculate fusion statistics: {e}")
            return {}
