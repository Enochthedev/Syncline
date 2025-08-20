"""
Unit tests for the Search API endpoints.

Tests REST API functionality, request/response handling,
and integration with the hybrid search agent.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from main import app
from services.ai.search.types import (
    SearchResponse as InternalSearchResponse,
    SearchResult, SearchResultType, SearchRanking, SearchStats,
    SearchQuery, QueryIntent
)


class TestSearchAPI:
    """Test suite for Search API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_search_agent(self):
        """Create a mock search agent."""
        agent = Mock()
        agent.initialize = AsyncMock()
        agent.search = AsyncMock()
        agent.search_commitments = AsyncMock()
        agent.search_shared_files = AsyncMock()
        agent.get_search_statistics = AsyncMock()
        agent.health_check = AsyncMock()
        agent.query_processor = Mock()
        agent.query_processor.generate_search_suggestions = Mock()
        return agent

    @pytest.fixture
    def sample_search_response(self):
        """Create a sample search response."""
        now = datetime.utcnow()

        results = [
            SearchResult(
                id="msg_1",
                type=SearchResultType.MESSAGE,
                title="Test Message",
                content="This is a test message about project planning",
                snippet="test message about project planning",
                metadata={
                    "platform": "gmail",
                    "sender": "john@example.com",
                    "thread_title": "Project Discussion"
                },
                ranking=SearchRanking(
                    lexical_score=0.8,
                    vector_score=0.7,
                    combined_score=0.75,
                    explanation="Combined search result"
                ),
                timestamp=now,
                platform="gmail",
                thread_id=uuid4(),
                participant_id=uuid4()
            )
        ]

        stats = SearchStats(
            total_results=1,
            lexical_results=1,
            vector_results=1,
            processing_time_ms=150.0,
            query_intent=QueryIntent.GENERAL_SEARCH,
            filters_applied=0
        )

        query = SearchQuery(
            text="test query",
            processed_text="test query",
            intent=QueryIntent.GENERAL_SEARCH
        )

        return InternalSearchResponse(
            results=results,
            stats=stats,
            query=query,
            suggestions=["test suggestion 1", "test suggestion 2"],
            facets={
                "platforms": [{"value": "gmail", "count": 1}],
                "types": [{"value": "message", "count": 1}]
            }
        )

    @patch('api.routes.search.get_search_agent')
    def test_search_post_endpoint(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test POST /api/v1/search/ endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.return_value = sample_search_response

        # Test request
        request_data = {
            "query": "test search query",
            "platforms": ["gmail", "slack"],
            "limit": 20,
            "include_suggestions": True,
            "include_facets": True
        }

        response = client.post("/api/v1/search/", json=request_data)

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "stats" in data
        assert "query" in data
        assert "suggestions" in data
        assert "facets" in data

        # Verify result structure
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["id"] == "msg_1"
        assert result["type"] == "message"
        assert result["title"] == "Test Message"
        assert "ranking" in result

        # Verify stats
        stats = data["stats"]
        assert stats["total_results"] == 1
        assert stats["processing_time_ms"] == 150.0

        # Verify search agent was called correctly
        mock_search_agent.search.assert_called_once()
        call_args = mock_search_agent.search.call_args
        assert call_args[1]["query_text"] == "test search query"
        assert call_args[1]["limit"] == 20

    @patch('api.routes.search.get_search_agent')
    def test_search_get_endpoint(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test GET /api/v1/search/ endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.return_value = sample_search_response

        # Test request with query parameters
        response = client.get(
            "/api/v1/search/",
            params={
                "q": "test query",
                "platforms": "gmail,slack",
                "limit": 10,
                "has_attachments": True
            }
        )

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1

        # Verify search agent was called with parsed parameters
        mock_search_agent.search.assert_called_once()
        call_args = mock_search_agent.search.call_args
        assert call_args[1]["query_text"] == "test query"
        assert call_args[1]["limit"] == 10

        # Verify filters were parsed correctly
        filters = call_args[1]["filters"]
        assert filters.platforms == ["gmail", "slack"]
        assert filters.has_attachments is True

    @patch('api.routes.search.get_search_agent')
    def test_search_commitments_endpoint(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test POST /api/v1/search/commitments endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search_commitments.return_value = sample_search_response

        # Test request
        request_data = {
            "person": "John",
            "topic": "project",
            "timeframe": "last week",
            "limit": 15
        }

        response = client.post("/api/v1/search/commitments", json=request_data)

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert "results" in data

        # Verify search_commitments was called correctly
        mock_search_agent.search_commitments.assert_called_once_with(
            person="John",
            topic="project",
            timeframe="last week",
            limit=15
        )

    @patch('api.routes.search.get_search_agent')
    def test_search_files_endpoint(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test POST /api/v1/search/files endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search_shared_files.return_value = sample_search_response

        # Test request
        request_data = {
            "contact": "Alice",
            "file_type": "pdf",
            "limit": 25
        }

        response = client.post("/api/v1/search/files", json=request_data)

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert "results" in data

        # Verify search_shared_files was called correctly
        mock_search_agent.search_shared_files.assert_called_once_with(
            contact="Alice",
            file_type="pdf",
            limit=25
        )

    @patch('api.routes.search.get_search_agent')
    def test_search_suggestions_endpoint(self, mock_get_agent, client, mock_search_agent):
        """Test GET /api/v1/search/suggestions endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.query_processor.generate_search_suggestions.return_value = [
            "suggestion 1",
            "suggestion 2",
            "suggestion 3"
        ]

        # Test request
        response = client.get(
            "/api/v1/search/suggestions", params={"q": "test"})

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert "suggestions" in data
        assert "query" in data
        assert data["query"] == "test"
        assert len(data["suggestions"]) == 3

        # Verify suggestions were generated
        mock_search_agent.query_processor.generate_search_suggestions.assert_called_once_with(
            "test")

    @patch('api.routes.search.get_search_agent')
    def test_search_stats_endpoint(self, mock_get_agent, client, mock_search_agent):
        """Test GET /api/v1/search/stats endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.get_search_statistics.return_value = {
            "total_searches": 100,
            "successful_searches": 95,
            "failed_searches": 5,
            "average_response_time": 125.5,
            "intent_distribution": {
                "general_search": 60,
                "person_search": 25,
                "file_search": 15
            }
        }

        # Test request
        response = client.get("/api/v1/search/stats")

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert data["total_searches"] == 100
        assert data["successful_searches"] == 95
        assert data["average_response_time"] == 125.5
        assert "intent_distribution" in data

    @patch('api.routes.search.get_search_agent')
    def test_search_health_endpoint(self, mock_get_agent, client, mock_search_agent):
        """Test GET /api/v1/search/health endpoint."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.health_check.return_value = {
            "status": "healthy",
            "components": {
                "lexical_engine": {"status": "healthy"},
                "vector_engine": {"status": "healthy"},
                "query_processor": {"status": "healthy"},
                "fusion_engine": {"status": "healthy"}
            },
            "last_check": datetime.utcnow().isoformat()
        }

        # Test request
        response = client.get("/api/v1/search/health")

        # Assertions
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "last_check" in data

    @patch('api.routes.search.get_search_agent')
    def test_search_with_custom_fusion_weights(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test search with custom fusion weights."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.return_value = sample_search_response

        # Test request with fusion weights
        request_data = {
            "query": "test query",
            "limit": 20
        }

        fusion_weights = {
            "lexical_weight": 0.7,
            "vector_weight": 0.3,
            "recency_boost": 0.2,
            "relevance_boost": 0.1
        }

        response = client.post(
            "/api/v1/search/",
            json=request_data,
            params={"fusion_weights": fusion_weights}
        )

        # Note: This test assumes the API supports fusion weights as query params
        # In practice, you might want to include them in the request body
        assert response.status_code == 200

    @patch('api.routes.search.get_search_agent')
    def test_search_error_handling(self, mock_get_agent, client, mock_search_agent):
        """Test error handling in search endpoints."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.side_effect = Exception("Search failed")

        # Test request that should fail
        request_data = {
            "query": "test query",
            "limit": 20
        }

        response = client.post("/api/v1/search/", json=request_data)

        # Should return 500 error
        assert response.status_code == 500

        data = response.json()
        assert "detail" in data
        assert "Search failed" in data["detail"]

    def test_search_request_validation(self, client):
        """Test request validation for search endpoints."""
        # Test missing required query parameter
        response = client.post("/api/v1/search/", json={})
        assert response.status_code == 422  # Validation error

        # Test invalid limit
        response = client.post("/api/v1/search/", json={
            "query": "test",
            "limit": 0  # Invalid limit
        })
        assert response.status_code == 422

        # Test invalid confidence score
        response = client.post("/api/v1/search/", json={
            "query": "test",
            "min_confidence": 1.5  # Invalid confidence (> 1.0)
        })
        assert response.status_code == 422

    def test_search_get_missing_query(self, client):
        """Test GET search endpoint with missing query parameter."""
        response = client.get("/api/v1/search/")
        assert response.status_code == 422  # Missing required 'q' parameter

    @patch('api.routes.search.get_search_agent')
    def test_search_pagination(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test search pagination parameters."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.return_value = sample_search_response

        # Test with pagination parameters
        request_data = {
            "query": "test query",
            "limit": 10,
            "offset": 20
        }

        response = client.post("/api/v1/search/", json=request_data)

        assert response.status_code == 200

        # Verify pagination parameters were passed
        mock_search_agent.search.assert_called_once()
        call_args = mock_search_agent.search.call_args
        assert call_args[1]["limit"] == 10
        assert call_args[1]["offset"] == 20

    @patch('api.routes.search.get_search_agent')
    def test_search_date_filters(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test search with date filters."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.return_value = sample_search_response

        # Test with date filters
        date_from = datetime.utcnow() - timedelta(days=7)
        date_to = datetime.utcnow()

        request_data = {
            "query": "test query",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }

        response = client.post("/api/v1/search/", json=request_data)

        assert response.status_code == 200

        # Verify date filters were parsed and passed
        mock_search_agent.search.assert_called_once()
        call_args = mock_search_agent.search.call_args
        filters = call_args[1]["filters"]

        assert filters.date_from is not None
        assert filters.date_to is not None
        assert filters.date_from.date() == date_from.date()
        assert filters.date_to.date() == date_to.date()

    @patch('api.routes.search.get_search_agent')
    def test_search_response_format(self, mock_get_agent, client, mock_search_agent, sample_search_response):
        """Test that search response format matches API specification."""
        mock_get_agent.return_value = mock_search_agent
        mock_search_agent.search.return_value = sample_search_response

        request_data = {
            "query": "test query",
            "include_suggestions": True,
            "include_facets": True
        }

        response = client.post("/api/v1/search/", json=request_data)

        assert response.status_code == 200

        data = response.json()

        # Verify top-level structure
        required_fields = ["results", "stats",
                           "query", "suggestions", "facets"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify result structure
        if data["results"]:
            result = data["results"][0]
            result_fields = [
                "id", "type", "title", "content", "snippet",
                "metadata", "ranking", "timestamp"
            ]
            for field in result_fields:
                assert field in result, f"Missing result field: {field}"

            # Verify ranking structure
            ranking = result["ranking"]
            ranking_fields = [
                "lexical_score", "vector_score", "combined_score", "explanation"
            ]
            for field in ranking_fields:
                assert field in ranking, f"Missing ranking field: {field}"

        # Verify stats structure
        stats = data["stats"]
        stats_fields = [
            "total_results", "lexical_results", "vector_results",
            "processing_time_ms", "filters_applied"
        ]
        for field in stats_fields:
            assert field in stats, f"Missing stats field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
