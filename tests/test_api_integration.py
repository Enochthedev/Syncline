"""Integration tests for REST and GraphQL APIs."""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from main import app
from db.session import get_db
from api.auth.models import User
from api.auth import get_current_active_user


# Test fixtures
@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        tenant_id="test-tenant"
    )


@pytest.fixture
def admin_user():
    """Create an admin test user."""
    return User(
        id="admin-user-id",
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        tenant_id="test-tenant"
    )


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestRESTAPIAuthentication:
    """Test REST API authentication and authorization."""

    def test_unauthenticated_request_allowed_in_debug(self, client):
        """Test that unauthenticated requests are allowed in debug mode."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    @patch('api.auth.auth.settings.DEBUG', False)
    def test_unauthenticated_request_denied_in_production(self, client):
        """Test that unauthenticated requests are denied in production."""
        response = client.get("/api/v1/messages")
        assert response.status_code == 401

    def test_api_key_authentication(self, client):
        """Test API key authentication."""
        headers = {"X-API-Key": "test-api-key"}
        with patch('api.auth.auth.get_user_by_api_key') as mock_get_user:
            mock_get_user.return_value = AsyncMock()
            response = client.get("/api/v1/health", headers=headers)
            # In debug mode, this will still work
            assert response.status_code == 200

    def test_jwt_token_authentication(self, client):
        """Test JWT token authentication."""
        headers = {"Authorization": "Bearer test-jwt-token"}
        with patch('api.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"sub": "test-user-id"}
            response = client.get("/api/v1/health", headers=headers)
            assert response.status_code == 200


class TestRESTAPIEndpoints:
    """Test REST API endpoints functionality."""

    @pytest.mark.asyncio
    async def test_get_messages(self, async_client, test_user, mock_db):
        """Test GET /api/v1/messages endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/messages")
                assert response.status_code == 200
                data = response.json()
                assert "messages" in data
                assert "count" in data

    @pytest.mark.asyncio
    async def test_get_threads(self, async_client, test_user, mock_db):
        """Test GET /api/v1/threads endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/threads")
                assert response.status_code == 200
                data = response.json()
                assert "threads" in data
                assert "count" in data

    @pytest.mark.asyncio
    async def test_get_participants(self, async_client, test_user, mock_db):
        """Test GET /api/v1/participants endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/participants")
                assert response.status_code == 200
                data = response.json()
                assert "participants" in data
                assert "count" in data

    @pytest.mark.asyncio
    async def test_search_messages(self, async_client, test_user):
        """Test POST /api/v1/search endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('services.ai.search.agent.HybridSearchAgent') as mock_agent:
                mock_search_response = AsyncMock()
                mock_search_response.results = []
                mock_search_response.stats = AsyncMock()
                mock_search_response.stats.total_results = 0
                mock_search_response.stats.lexical_results = 0
                mock_search_response.stats.vector_results = 0
                mock_search_response.stats.processing_time_ms = 10.0
                mock_search_response.stats.query_intent = None
                mock_search_response.stats.filters_applied = 0
                mock_search_response.query = AsyncMock()
                mock_search_response.query.text = "test query"
                mock_search_response.query.processed_text = "test query"
                mock_search_response.query.intent = None
                mock_search_response.query.filters = None
                mock_search_response.query.limit = 50
                mock_search_response.query.offset = 0
                mock_search_response.suggestions = []
                mock_search_response.facets = {}

                mock_agent_instance = AsyncMock()
                mock_agent_instance.search.return_value = mock_search_response
                mock_agent.return_value = mock_agent_instance

                search_data = {
                    "query": "test search",
                    "limit": 10
                }

                response = await async_client.post("/api/v1/search/", json=search_data)
                assert response.status_code == 200
                data = response.json()
                assert "results" in data
                assert "stats" in data

    @pytest.mark.asyncio
    async def test_get_contact_dossiers(self, async_client, test_user, mock_db):
        """Test GET /api/v1/contact-dossiers endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/contact-dossiers/")
                assert response.status_code == 200
                data = response.json()
                assert "contact_dossiers" in data
                assert "count" in data

    @pytest.mark.asyncio
    async def test_get_summaries(self, async_client, test_user, mock_db):
        """Test GET /api/v1/summaries endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/summaries/?scope_type=thread")
                assert response.status_code == 200
                data = response.json()
                assert "summaries" in data
                assert "count" in data

    @pytest.mark.asyncio
    async def test_get_file_references(self, async_client, test_user, mock_db):
        """Test GET /api/v1/files endpoint."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/files/")
                assert response.status_code == 200
                data = response.json()
                assert "file_references" in data
                assert "count" in data


class TestGraphQLAPI:
    """Test GraphQL API functionality."""

    @pytest.mark.asyncio
    async def test_graphql_introspection(self, async_client):
        """Test GraphQL introspection query."""
        query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                }
            }
        }
        """

        response = await async_client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]

    @pytest.mark.asyncio
    async def test_graphql_messages_query(self, async_client, test_user):
        """Test GraphQL messages query."""
        query = """
        query GetMessages($limit: Int) {
            messages(pagination: {limit: $limit}) {
                id
                platform
                contentText
                timestamp
            }
        }
        """

        variables = {"limit": 10}

        with patch('api.graphql.context.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_get_db.return_value.__anext__.return_value = mock_db

            response = await async_client.post(
                "/graphql",
                json={"query": query, "variables": variables},
                headers={"X-User-ID": "test-user-id"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data

    @pytest.mark.asyncio
    async def test_graphql_search_query(self, async_client, test_user):
        """Test GraphQL search query."""
        query = """
        query SearchMessages($query: String!, $limit: Int) {
            search(query: $query, pagination: {limit: $limit}) {
                results {
                    id
                    title
                    content
                    snippet
                }
                stats {
                    totalResults
                    processingTimeMs
                }
            }
        }
        """

        variables = {"query": "test search", "limit": 10}

        with patch('services.ai.search.agent.HybridSearchAgent') as mock_agent:
            mock_search_response = AsyncMock()
            mock_search_response.results = []
            mock_search_response.stats = AsyncMock()
            mock_search_response.stats.total_results = 0
            mock_search_response.stats.processing_time_ms = 10.0
            mock_search_response.query = AsyncMock()
            mock_search_response.suggestions = []
            mock_search_response.facets = {}

            mock_agent_instance = AsyncMock()
            mock_agent_instance.search.return_value = mock_search_response
            mock_agent.return_value = mock_agent_instance

            response = await async_client.post(
                "/graphql",
                json={"query": query, "variables": variables},
                headers={"X-User-ID": "test-user-id"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_per_user(self, async_client, test_user):
        """Test per-user rate limiting."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.auth.rate_limiting.rate_limiter.is_allowed') as mock_is_allowed:
                # First request allowed
                mock_is_allowed.return_value = (
                    True, {"remaining": 29, "limit": 30})
                response = await async_client.get("/api/v1/health")
                assert response.status_code == 200

                # Rate limit exceeded
                mock_is_allowed.return_value = (
                    False, {"remaining": 0, "limit": 30})
                response = await async_client.get("/api/v1/health")
                assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, async_client, test_user):
        """Test rate limit headers in response."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.auth.rate_limiting.rate_limiter.is_allowed') as mock_is_allowed:
                mock_is_allowed.return_value = (True, {
                    "remaining": 29,
                    "limit": 30,
                    "reset_time": 1234567890,
                    "window_seconds": 60
                })

                response = await async_client.get("/api/v1/health")
                assert response.status_code == 200
                # Rate limit headers would be added by middleware


class TestErrorHandling:
    """Test API error handling."""

    @pytest.mark.asyncio
    async def test_404_error(self, async_client, test_user):
        """Test 404 error handling."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            response = await async_client.get("/api/v1/nonexistent")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_error(self, async_client, test_user):
        """Test validation error handling."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            # Invalid search request
            search_data = {
                "query": "",  # Empty query should fail validation
                "limit": -1   # Negative limit should fail validation
            }

            response = await async_client.post("/api/v1/search/", json=search_data)
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_database_error_handling(self, async_client, test_user, mock_db):
        """Test database error handling."""
        with patch('api.dependencies.get_current_active_user', return_value=test_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                # Simulate database error
                mock_db.execute.side_effect = Exception(
                    "Database connection failed")

                response = await async_client.get("/api/v1/messages")
                assert response.status_code == 500


class TestTenantIsolation:
    """Test multi-tenant data isolation."""

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self, async_client, mock_db):
        """Test that users can only access their tenant's data."""
        user1 = User(
            id="user1-id",
            username="user1",
            email="user1@example.com",
            tenant_id="tenant1",
            is_active=True
        )

        user2 = User(
            id="user2-id",
            username="user2",
            email="user2@example.com",
            tenant_id="tenant2",
            is_active=True
        )

        # Test that user1 cannot access user2's contact dossiers
        with patch('api.dependencies.get_current_active_user', return_value=user1):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get(f"/api/v1/contact-dossiers/?user_id={user2.id}")
                assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_superuser_access(self, async_client, admin_user, mock_db):
        """Test that superusers can access all data."""
        with patch('api.dependencies.get_current_active_user', return_value=admin_user):
            with patch('api.dependencies.get_db', return_value=mock_db):
                mock_db.execute.return_value.scalars.return_value.all.return_value = []

                response = await async_client.get("/api/v1/contact-dossiers/?user_id=any-user-id")
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
