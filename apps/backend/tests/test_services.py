"""
Service Tests

Tests for backend services.
"""

from datetime import datetime

import pytest


class TestLoggingService:
    """Test logging configuration."""

    def test_get_logger(self):
        """Test getting a logger."""
        from config.logging_config import get_logger

        logger = get_logger(__name__)
        assert logger is not None

    def test_get_logger_with_correlation_id(self):
        """Test logger with correlation ID."""
        from config.logging_config import get_logger

        logger = get_logger(__name__, correlation_id="test-123")
        assert logger is not None


class TestPrometheusMetrics:
    """Test Prometheus metrics."""

    def test_track_message_collected(self):
        """Test message collection metric."""
        from services.monitoring.prometheus_metrics import track_message_collected

        track_message_collected("gmail")
        # Should not raise

    def test_track_ai_embedding(self):
        """Test AI embedding metric."""
        from services.monitoring.prometheus_metrics import track_ai_embedding

        track_ai_embedding()
        # Should not raise

    def test_get_metrics(self):
        """Test getting metrics."""
        from services.monitoring.prometheus_metrics import get_metrics

        metrics = get_metrics()
        assert metrics is not None
        assert isinstance(metrics, bytes)


class TestFullTextSearch:
    """Test full-text search service."""

    def test_parse_query(self):
        """Test query parsing."""
        from services.search.fulltext_search import FullTextSearchService

        service = FullTextSearchService()

        # Test simple query
        parsed = service._parse_query("hello world")
        assert parsed == "hello & world"

        # Test with special characters
        parsed = service._parse_query("hello-world!")
        assert "hello" in parsed
        assert "world" in parsed


class TestWebSocketManager:
    """Test WebSocket manager."""

    @pytest.mark.asyncio
    async def test_get_manager(self):
        """Test getting WebSocket manager."""
        from services.realtime.websocket_manager import get_websocket_manager

        manager = get_websocket_manager()
        assert manager is not None
        assert manager.get_connection_count() == 0


class TestDataRetention:
    """Test data retention service."""

    def test_retention_policy(self):
        """Test retention policy configuration."""
        from services.retention.data_retention import RetentionPolicy

        policy = RetentionPolicy(
            messages_retention_days=365,
            raw_messages_retention_days=90,
            audit_logs_retention_days=730,
        )

        assert policy.messages_retention_days == 365
        assert policy.raw_messages_retention_days == 90
        assert policy.audit_logs_retention_days == 730


class TestAuditLogger:
    """Test audit logging."""

    def test_audit_action_enum(self):
        """Test audit action enumeration."""
        from services.audit.audit_logger import AuditAction

        assert AuditAction.LOGIN == "login"
        assert AuditAction.READ == "read"
        assert AuditAction.CREATE == "create"
