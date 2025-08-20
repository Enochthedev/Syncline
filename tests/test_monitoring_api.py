"""Tests for monitoring API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.routes.monitoring import router as monitoring_router
from services.monitoring.health import HealthStatus, HealthCheckResult


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(monitoring_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @patch('api.routes.monitoring.get_metrics_collector')
    def test_get_metrics_success(self, mock_get_collector, client):
        """Test successful metrics retrieval."""
        # Mock metrics collector
        mock_collector = Mock()
        mock_collector.get_metrics.return_value = """# HELP mesh_test_metric Test metric
# TYPE mesh_test_metric counter
mesh_test_metric{platform="gmail"} 42.0
"""
        mock_collector.get_content_type.return_value = "text/plain; version=0.0.4; charset=utf-8"
        mock_get_collector.return_value = mock_collector

        # Make request
        response = client.get("/monitoring/metrics")

        assert response.status_code == 200
        assert "mesh_test_metric" in response.text
        assert 'platform="gmail"' in response.text
