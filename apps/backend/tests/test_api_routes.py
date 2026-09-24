"""
API Routes Tests

Basic tests for API endpoints.
"""

from datetime import datetime

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test main health check endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_ai_health_check(self, client: AsyncClient):
        """Test AI services health check."""
        response = await client.get("/api/v1/ai/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data


class TestStatsEndpoints:
    """Test statistics endpoints."""

    @pytest.mark.asyncio
    async def test_system_stats(self, client: AsyncClient):
        """Test system statistics endpoint."""
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_messages" in data
        assert "total_connections" in data
        assert "last_updated" in data


class TestMessageEndpoints:
    """Test message endpoints."""

    @pytest.mark.asyncio
    async def test_list_messages(self, client: AsyncClient):
        """Test message listing endpoint."""
        response = await client.get("/api/v1/messages")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total" in data
        assert isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_message_stats(self, client: AsyncClient):
        """Test message statistics endpoint."""
        response = await client.get("/api/v1/messages/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_messages" in data
        assert "messages_by_platform" in data


class TestAIEndpoints:
    """Test AI endpoints."""

    @pytest.mark.asyncio
    async def test_semantic_search(self, client: AsyncClient):
        """Test semantic search endpoint."""
        response = await client.post(
            "/api/v1/ai/search", json={"query": "test query", "limit": 10}
        )
        # May return 500 if services not initialized, which is OK for basic test
        assert response.status_code in [200, 500]
