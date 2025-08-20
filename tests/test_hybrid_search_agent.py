"""
Unit tests for the Hybrid Search Agent.

Tests search accuracy, performance, and functionality across
different query types and search scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID

from services.ai.search.agent import HybridSearchAgent
from services.ai.search.types import (
    SearchQuery, SearchResult, SearchResultType, SearchRanking,
    SearchFilters, QueryIntent, FusionWeights, SearchResponse
)
from services.ai.search.query_processor import QueryProcessor
from services.ai.search.lexical_search import LexicalSearchEngine
from services.ai.search.vector_search import VectorSearchEngine
from services.ai.search.result_fusion import SearchResultFusion


class TestHybridSearchAgent:
    """Test suite for HybridSearchAgent."""

    @pytest.fixture
    async def search_agent(self):
        """Create a test search agent with mocked dependencies."""
        agent = HybridSearchAgent()

        # Mock the components
        agent.query_processor = Mock(spec=QueryProcessor)
        agent.lexical_engine = Mock(spec=LexicalSearchEngine)
        agent.vector_engine = Mock(spec=VectorSearchEngine)
        agent.fusion_engine = Mock(spec=SearchResultFusion)

        # Mock async methods
        agent.query_processor.initialize = AsyncMock()
        agent.query_processor.process_query = AsyncMock()
        agent.query_processor.generate_search_suggestions = Mock()

        agent.lexical_engine.search = AsyncMock()
        agent.vector_engine.initialize = AsyncMock()
        agent.vector_engine.search = AsyncMock()

        agent.fusion_engine.fuse_results = Mock()

        agent._initialized = True

        return agent

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results for testing."""
        now = datetime.utcnow()

        lexical_results = [
            SearchResult(
                id="msg_1",
                type=SearchResultType.MESSAGE,
                title="Test Message 1",
                content="This is a test message about project planning",
                snippet="test message about project planning",
                metadata={"platform": "gmail", "sender": "john@example.com"},
                ranking=SearchRanking(
                    lexical_score=0.8, vector_score=0.0, combined_score=0.8),
                timestamp=now - timedelta(days=1),
                platform="gmail",
                thread_id=uuid4(),
                participant_id=uuid4()
            ),
            SearchResult(
                id="msg_2",
                type=SearchResultType.MESSAGE,
                title="Test Message 2",
                content="Another message discussing project deadlines",
                snippet="message discussing project deadlines",
                metadata={"platform": "slack", "sender": "jane@example.com"},
                ranking=SearchRanking(
                    lexical_score=0.6, vector_score=0.0, combined_score=0.6),
                timestamp=now - timedelta(days=2),
                platform="slack",
                thread_id=uuid4(),
                participant_id=uuid4()
            )
        ]

        vector_results = [
            SearchResult(
                id="msg_1",  # Same as lexical result
                type=SearchResultType.MESSAGE,
                title="Test Message 1",
                content="This is a test message about project planning",
                snippet="test message about project planning",
                metadata={"platform": "gmail", "sender": "john@example.com"},
                ranking=SearchRanking(
                    lexical_score=0.0, vector_score=0.9, combined_score=0.9),
                timestamp=now - timedelta(days=1),
                platform="gmail",
                thread_id=uuid4(),
                participant_id=uuid4()
            ),
            SearchResult(
                id="msg_3",
                type=SearchResultType.MESSAGE,
                title="Test Message 3",
                content="Semantic similarity test for project management",
                snippet="semantic similarity test for project management",
                metadata={"platform": "discord", "sender": "bob@example.com"},
                ranking=SearchRanking(
                    lexical_score=0.0, vector_score=0.7, combined_score=0.7),
                timestamp=now - timedelta(days=3),
                platform="discord",
                thread_id=uuid4(),
                participant_id=uuid4()
            )
        ]

        return lexical_results, vector_results

    @pytest.mark.asyncio
    async def test_basic_search(self, search_agent, sample_search_results):
        """Test basic search functionality."""
        lexical_results, vector_results = sample_search_results

        # Setup mocks
        processed_query = SearchQuery(
            text="project planning",
            processed_text="project planning",
            intent=QueryIntent.GENERAL_SEARCH
        )

        search_agent.query_processor.process_query.return_value = processed_query
        search_agent.lexical_engine.search.return_value = lexical_results
        search_agent.vector_engine.search.return_value = vector_results

        # Mock fusion result
        fused_results = lexical_results + \
            [vector_results[1]]  # Combine unique results
        search_agent.fusion_engine.fuse_results.return_value = fused_results

        # Perform search
        response = await search_agent.search("project planning")

        # Assertions
        assert isinstance(response, SearchResponse)
        assert len(response.results) == 3
        assert response.stats.total_results == 3
        assert response.stats.lexical_results == 2
        assert response.stats.vector_results == 2
        assert response.query.text == "project planning"

        # Verify method calls
        search_agent.query_processor.process_query.assert_called_once()
        search_agent.lexical_engine.search.assert_called_once()
        search_agent.vector_engine.search.assert_called_once()
        search_agent.fusion_engine.fuse_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_agent, sample_search_results):
        """Test search with various filters."""
        lexical_results, vector_results = sample_search_results

        # Create search filters
        filters = SearchFilters(
            platforms=["gmail", "slack"],
            participants=["john@example.com"],
            date_from=datetime.utcnow() - timedelta(days=7),
            has_attachments=True
        )

        # Setup mocks
        processed_query = SearchQuery(
            text="test query",
            filters=filters,
            intent=QueryIntent.PERSON_SEARCH
        )

        search_agent.query_processor.process_query.return_value = processed_query
        # Filtered results
        search_agent.lexical_engine.search.return_value = lexical_results[:1]
        search_agent.vector_engine.search.return_value = vector_results[:1]
        search_agent.fusion_engine.fuse_results.return_value = lexical_results[:1]

        # Perform search
        response = await search_agent.search(
            query_text="test query",
            filters=filters,
            limit=10
        )

        # Assertions
        assert response.stats.filters_applied > 0
        assert response.query.filters is not None

        # Verify filters were passed to engines
        call_args = search_agent.lexical_engine.search.call_args[0]
        assert call_args[0].filters == filters

    @pytest.mark.asyncio
    async def test_commitment_search(self, search_agent):
        """Test specialized commitment search."""
        # Mock commitment search results
        commitment_results = [
            SearchResult(
                id="msg_commit_1",
                type=SearchResultType.MESSAGE,
                title="Commitment Message",
                content="I promise to deliver the report by Friday",
                snippet="promise to deliver the report by Friday",
                metadata={"entity_types": ["commitment", "deadline"]},
                ranking=SearchRanking(
                    lexical_score=0.9, vector_score=0.8, combined_score=0.85),
                timestamp=datetime.utcnow() - timedelta(days=1)
            )
        ]

        # Setup mocks for the internal search call
        with patch.object(search_agent, 'search', new_callable=AsyncMock) as mock_search:
            mock_response = SearchResponse(
                results=commitment_results,
                stats=Mock(),
                query=Mock()
            )
            mock_search.return_value = mock_response

            # Perform commitment search
            response = await search_agent.search_commitments(
                person="john",
                topic="report",
                timeframe="last week"
            )

            # Assertions
            assert len(response.results) == 1
            assert "commitment" in response.results[0].metadata.get(
                "entity_types", [])

            # Verify search was called with commitment-specific parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert "commitments" in call_args[1]["query_text"]
            assert call_args[1]["filters"].entity_types == [
                "commitment", "task", "deadline"]

    @pytest.mark.asyncio
    async def test_file_search(self, search_agent):
        """Test specialized file search."""
        # Mock file search results
        file_results = [
            SearchResult(
                id="msg_file_1",
                type=SearchResultType.MESSAGE,
                title="File Share Message",
                content="Here's the PDF document we discussed",
                snippet="PDF document we discussed",
                metadata={"has_attachments": True, "file_types": ["pdf"]},
                ranking=SearchRanking(
                    lexical_score=0.8, vector_score=0.6, combined_score=0.7),
                timestamp=datetime.utcnow() - timedelta(hours=2)
            )
        ]

        # Setup mocks for the internal search call
        with patch.object(search_agent, 'search', new_callable=AsyncMock) as mock_search:
            mock_response = SearchResponse(
                results=file_results,
                stats=Mock(),
                query=Mock()
            )
            mock_search.return_value = mock_response

            # Perform file search
            response = await search_agent.search_shared_files(
                contact="alice",
                file_type="pdf"
            )

            # Assertions
            assert len(response.results) == 1
            assert response.results[0].metadata.get("has_attachments") is True

            # Verify search was called with file-specific parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert "files" in call_args[1]["query_text"]
            assert call_args[1]["filters"].has_attachments is True

    @pytest.mark.asyncio
    async def test_search_with_custom_fusion_weights(self, search_agent, sample_search_results):
        """Test search with custom fusion weights."""
        lexical_results, vector_results = sample_search_results

        # Custom fusion weights favoring vector search
        custom_weights = FusionWeights(
            lexical_weight=0.3,
            vector_weight=0.7,
            recency_boost=0.2,
            relevance_boost=0.1
        )

        # Setup mocks
        processed_query = SearchQuery(
            text="test", intent=QueryIntent.TOPIC_SEARCH)
        search_agent.query_processor.process_query.return_value = processed_query
        search_agent.lexical_engine.search.return_value = lexical_results
        search_agent.vector_engine.search.return_value = vector_results
        search_agent.fusion_engine.fuse_results.return_value = vector_results  # Favor vector

        # Perform search
        response = await search_agent.search(
            query_text="test",
            fusion_weights=custom_weights
        )

        # Verify fusion was called with custom weights
        fusion_call_args = search_agent.fusion_engine.fuse_results.call_args
        # Fourth argument is fusion_weights
        assert fusion_call_args[0][3] == custom_weights

    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_agent):
        """Test search error handling and fallback behavior."""
        # Setup mocks to raise exceptions
        search_agent.query_processor.process_query.side_effect = Exception(
            "Query processing failed")

        # Perform search
        response = await search_agent.search("test query")

        # Should return empty response on failure
        assert len(response.results) == 0
        assert response.stats.processing_time_ms > 0

        # Verify failure statistics are updated
        assert search_agent.stats["failed_searches"] > 0

    @pytest.mark.asyncio
    async def test_parallel_search_execution(self, search_agent, sample_search_results):
        """Test that lexical and vector searches execute in parallel."""
        lexical_results, vector_results = sample_search_results

        # Track call order
        call_order = []

        async def mock_lexical_search(*args, **kwargs):
            call_order.append("lexical_start")
            await asyncio.sleep(0.1)  # Simulate processing time
            call_order.append("lexical_end")
            return lexical_results

        async def mock_vector_search(*args, **kwargs):
            call_order.append("vector_start")
            await asyncio.sleep(0.1)  # Simulate processing time
            call_order.append("vector_end")
            return vector_results

        # Setup mocks
        processed_query = SearchQuery(
            text="test", intent=QueryIntent.GENERAL_SEARCH)
        search_agent.query_processor.process_query.return_value = processed_query
        search_agent.lexical_engine.search = mock_lexical_search
        search_agent.vector_engine.search = mock_vector_search
        search_agent.fusion_engine.fuse_results.return_value = lexical_results

        # Perform search
        start_time = datetime.utcnow()
        await search_agent.search("test")
        end_time = datetime.utcnow()

        # Verify parallel execution (should complete in ~0.1s, not ~0.2s)
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 0.15  # Allow some overhead

        # Verify both searches started before either ended
        lexical_start_idx = call_order.index("lexical_start")
        vector_start_idx = call_order.index("vector_start")
        lexical_end_idx = call_order.index("lexical_end")
        vector_end_idx = call_order.index("vector_end")

        # Both should start before either ends
        assert min(lexical_start_idx, vector_start_idx) < min(
            lexical_end_idx, vector_end_idx)

    def test_search_statistics_tracking(self, search_agent):
        """Test that search statistics are properly tracked."""
        initial_stats = search_agent.stats.copy()

        # Mock a successful search
        mock_query = SearchQuery(
            text="test", intent=QueryIntent.GENERAL_SEARCH)
        mock_stats = Mock()
        mock_stats.processing_time_ms = 150.0

        search_agent._update_stats(mock_query, mock_stats, success=True)

        # Verify statistics were updated
        assert search_agent.stats["total_searches"] == initial_stats["total_searches"] + 1
        assert search_agent.stats["successful_searches"] == initial_stats["successful_searches"] + 1
        assert search_agent.stats["intent_distribution"]["general_search"] == 1
        assert search_agent.stats["last_search"] is not None

    @pytest.mark.asyncio
    async def test_search_suggestions(self, search_agent):
        """Test search suggestion generation."""
        # Mock suggestions
        mock_suggestions = [
            "commitments from last week",
            "files shared with john",
            "messages about project"
        ]

        search_agent.query_processor.generate_search_suggestions.return_value = mock_suggestions

        # Setup basic search mocks
        processed_query = SearchQuery(
            text="test", intent=QueryIntent.GENERAL_SEARCH)
        search_agent.query_processor.process_query.return_value = processed_query
        search_agent.lexical_engine.search.return_value = []
        search_agent.vector_engine.search.return_value = []
        search_agent.fusion_engine.fuse_results.return_value = []

        # Perform search with suggestions
        response = await search_agent.search(
            query_text="test",
            include_suggestions=True
        )

        # Verify suggestions are included
        assert response.suggestions == mock_suggestions
        search_agent.query_processor.generate_search_suggestions.assert_called_once_with(
            "test")

    @pytest.mark.asyncio
    async def test_search_facets_generation(self, search_agent, sample_search_results):
        """Test search facet generation."""
        lexical_results, vector_results = sample_search_results

        # Setup mocks
        processed_query = SearchQuery(
            text="test", intent=QueryIntent.GENERAL_SEARCH)
        search_agent.query_processor.process_query.return_value = processed_query
        search_agent.lexical_engine.search.return_value = lexical_results
        search_agent.vector_engine.search.return_value = vector_results
        search_agent.fusion_engine.fuse_results.return_value = lexical_results + vector_results

        # Perform search with facets
        response = await search_agent.search(
            query_text="test",
            include_facets=True
        )

        # Verify facets are generated
        assert response.facets is not None
        assert "platforms" in response.facets
        assert "types" in response.facets
        assert "time_periods" in response.facets

        # Verify platform facets
        platform_facets = response.facets["platforms"]
        platform_names = [f["value"] for f in platform_facets]
        assert "gmail" in platform_names
        assert "slack" in platform_names

    @pytest.mark.asyncio
    async def test_health_check(self, search_agent):
        """Test search agent health check."""
        # Mock component health checks
        search_agent.vector_engine.vector_db = Mock()
        search_agent.vector_engine.vector_db.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )
        search_agent.query_processor.ai_engine = Mock()

        # Perform health check
        health = await search_agent.health_check()

        # Verify health response
        assert "status" in health
        assert "components" in health
        assert "last_check" in health

        # Verify component statuses
        components = health["components"]
        assert "vector_engine" in components
        assert "query_processor" in components
        assert "lexical_engine" in components
        assert "fusion_engine" in components

    @pytest.mark.asyncio
    async def test_search_performance_metrics(self, search_agent, sample_search_results):
        """Test that performance metrics are properly calculated."""
        lexical_results, vector_results = sample_search_results

        # Setup mocks with artificial delay
        async def slow_lexical_search(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return lexical_results

        async def slow_vector_search(*args, **kwargs):
            await asyncio.sleep(0.03)  # 30ms delay
            return vector_results

        processed_query = SearchQuery(
            text="test", intent=QueryIntent.GENERAL_SEARCH)
        search_agent.query_processor.process_query.return_value = processed_query
        search_agent.lexical_engine.search = slow_lexical_search
        search_agent.vector_engine.search = slow_vector_search
        search_agent.fusion_engine.fuse_results.return_value = lexical_results

        # Perform search
        response = await search_agent.search("test")

        # Verify performance metrics
        assert response.stats.processing_time_ms > 50  # Should be at least 50ms
        assert response.stats.processing_time_ms < 200  # But not too slow

        # Verify statistics are updated
        stats = await search_agent.get_search_statistics()
        assert stats["average_response_time"] > 0


class TestQueryIntentDetection:
    """Test query intent detection accuracy."""

    @pytest.fixture
    def query_processor(self):
        """Create a query processor for testing."""
        processor = QueryProcessor()
        processor.ai_engine = None  # Use basic mode for testing
        return processor

    def test_commitment_intent_detection(self, query_processor):
        """Test detection of commitment-related queries."""
        commitment_queries = [
            "what did I promise John about the project",
            "my commitments to the team",
            "what am I supposed to deliver",
            "deadline for the report"
        ]

        for query in commitment_queries:
            intent = query_processor._detect_intent(query)
            assert intent == QueryIntent.COMMITMENT_SEARCH, f"Failed for query: {query}"

    def test_person_intent_detection(self, query_processor):
        """Test detection of person-related queries."""
        person_queries = [
            "messages from Alice",
            "conversation with Bob",
            "John said something about",
            "talk to Sarah about the meeting"
        ]

        for query in person_queries:
            intent = query_processor._detect_intent(query)
            assert intent == QueryIntent.PERSON_SEARCH, f"Failed for query: {query}"

    def test_file_intent_detection(self, query_processor):
        """Test detection of file-related queries."""
        file_queries = [
            "files shared with team",
            "PDF from yesterday",
            "shared document with Alice",
            "attachments in this thread"
        ]

        for query in file_queries:
            intent = query_processor._detect_intent(query)
            assert intent == QueryIntent.FILE_SEARCH, f"Failed for query: {query}"

    def test_time_intent_detection(self, query_processor):
        """Test detection of time-based queries."""
        time_queries = [
            "messages from yesterday",
            "last week's discussions",
            "before 2024-01-15",
            "3 days ago"
        ]

        for query in time_queries:
            intent = query_processor._detect_intent(query)
            assert intent == QueryIntent.TIME_BASED_SEARCH, f"Failed for query: {query}"

    def test_general_intent_fallback(self, query_processor):
        """Test fallback to general search for unclear queries."""
        general_queries = [
            "hello world",
            "random text",
            "search everything",
            "find stuff"
        ]

        for query in general_queries:
            intent = query_processor._detect_intent(query)
            assert intent == QueryIntent.GENERAL_SEARCH, f"Failed for query: {query}"


class TestSearchResultFusion:
    """Test search result fusion algorithms."""

    @pytest.fixture
    def fusion_engine(self):
        """Create a fusion engine for testing."""
        return SearchResultFusion()

    @pytest.fixture
    def test_results(self):
        """Create test results for fusion testing."""
        now = datetime.utcnow()

        lexical_results = [
            SearchResult(
                id="result_1",
                type=SearchResultType.MESSAGE,
                title="Test 1",
                content="Content 1",
                snippet="Snippet 1",
                metadata={},
                ranking=SearchRanking(
                    lexical_score=0.9, vector_score=0.0, combined_score=0.9),
                timestamp=now
            ),
            SearchResult(
                id="result_2",
                type=SearchResultType.MESSAGE,
                title="Test 2",
                content="Content 2",
                snippet="Snippet 2",
                metadata={},
                ranking=SearchRanking(
                    lexical_score=0.7, vector_score=0.0, combined_score=0.7),
                timestamp=now - timedelta(days=1)
            )
        ]

        vector_results = [
            SearchResult(
                id="result_1",  # Overlap with lexical
                type=SearchResultType.MESSAGE,
                title="Test 1",
                content="Content 1",
                snippet="Snippet 1",
                metadata={},
                ranking=SearchRanking(
                    lexical_score=0.0, vector_score=0.8, combined_score=0.8),
                timestamp=now
            ),
            SearchResult(
                id="result_3",  # Unique to vector
                type=SearchResultType.MESSAGE,
                title="Test 3",
                content="Content 3",
                snippet="Snippet 3",
                metadata={},
                ranking=SearchRanking(
                    lexical_score=0.0, vector_score=0.6, combined_score=0.6),
                timestamp=now - timedelta(hours=12)
            )
        ]

        return lexical_results, vector_results

    def test_basic_fusion(self, fusion_engine, test_results):
        """Test basic result fusion functionality."""
        lexical_results, vector_results = test_results

        query = SearchQuery(text="test", intent=QueryIntent.GENERAL_SEARCH)

        fused_results = fusion_engine.fuse_results(
            lexical_results, vector_results, query
        )

        # Should have 3 unique results (2 lexical + 1 unique vector)
        assert len(fused_results) == 3

        # Results should be sorted by combined score
        scores = [r.ranking.combined_score for r in fused_results]
        assert scores == sorted(scores, reverse=True)

        # Overlapping result should have both lexical and vector scores
        overlapping_result = next(
            r for r in fused_results if r.id == "result_1")
        assert overlapping_result.ranking.lexical_score > 0
        assert overlapping_result.ranking.vector_score > 0

    def test_intent_based_weight_adjustment(self, fusion_engine, test_results):
        """Test that fusion weights are adjusted based on query intent."""
        lexical_results, vector_results = test_results

        # Test commitment search (should favor lexical)
        commitment_query = SearchQuery(
            text="test", intent=QueryIntent.COMMITMENT_SEARCH)
        weights = fusion_engine._get_fusion_weights(commitment_query)
        assert weights.lexical_weight > weights.vector_weight

        # Test topic search (should favor vector)
        topic_query = SearchQuery(text="test", intent=QueryIntent.TOPIC_SEARCH)
        weights = fusion_engine._get_fusion_weights(topic_query)
        assert weights.vector_weight > weights.lexical_weight

    def test_recency_boost(self, fusion_engine, test_results):
        """Test that recent results get boosted in ranking."""
        lexical_results, vector_results = test_results

        query = SearchQuery(text="test", intent=QueryIntent.GENERAL_SEARCH)
        weights = FusionWeights(recency_boost=0.5)  # High recency boost

        fused_results = fusion_engine.fuse_results(
            lexical_results, vector_results, query, weights
        )

        # More recent results should be ranked higher
        # (assuming similar base scores)
        recent_result = next(r for r in fused_results if r.id == "result_1")
        older_result = next(r for r in fused_results if r.id == "result_2")

        # Recent result should have higher combined score due to recency boost
        assert recent_result.ranking.combined_score >= older_result.ranking.combined_score

    def test_fusion_statistics(self, fusion_engine, test_results):
        """Test fusion statistics calculation."""
        lexical_results, vector_results = test_results

        fused_results = [lexical_results[0],
                         lexical_results[1], vector_results[1]]

        stats = fusion_engine.get_fusion_statistics(
            lexical_results, vector_results, fused_results
        )

        assert stats["lexical_results_count"] == 2
        assert stats["vector_results_count"] == 2
        assert stats["fused_results_count"] == 3
        assert stats["overlap_count"] == 1  # result_1 appears in both
        assert stats["lexical_only_count"] == 1  # result_2
        assert stats["vector_only_count"] == 1  # result_3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
