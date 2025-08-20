"""Tests for monitoring metrics collection."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from prometheus_client import CollectorRegistry

from services.monitoring.metrics import MetricsCollector, get_metrics_collector


class TestMetricsCollector:
    """Test metrics collection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a custom registry for testing
        self.registry = CollectorRegistry()
        self.metrics_collector = MetricsCollector(registry=self.registry)

    def test_metrics_collector_initialization(self):
        """Test metrics collector initializes correctly."""
        assert self.metrics_collector.registry is not None
        assert hasattr(self.metrics_collector, 'messages_ingested_total')
        assert hasattr(self.metrics_collector, 'api_requests_total')
        assert hasattr(self.metrics_collector, 'ai_operations_total')

    def test_record_message_ingested(self):
        """Test recording message ingestion metrics."""
        # Record successful ingestion
        self.metrics_collector.record_message_ingested("gmail", "success")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_messages_ingested_total' in metrics
        assert 'platform="gmail"' in metrics
        assert 'status="success"' in metrics

    def test_record_api_request(self):
        """Test recording API request metrics."""
        # Record API request
        self.metrics_collector.record_api_request("GET", "/api/v1/health", 200)

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_api_requests_total' in metrics
        assert 'method="GET"' in metrics
        assert 'endpoint="/api/v1/health"' in metrics
        assert 'status_code="200"' in metrics

    def test_record_ai_operation(self):
        """Test recording AI operation metrics."""
        # Record AI operation
        self.metrics_collector.record_ai_operation(
            "entity_extractor", "extract", "success")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_ai_operations_total' in metrics
        assert 'agent_type="entity_extractor"' in metrics
        assert 'operation="extract"' in metrics
        assert 'status="success"' in metrics

    def test_set_connector_health(self):
        """Test setting connector health metrics."""
        # Set connector as healthy
        self.metrics_collector.set_connector_health("gmail", "oauth", True)

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_connector_health' in metrics
        assert 'platform="gmail"' in metrics
        assert 'connector_type="oauth"' in metrics

    def test_set_system_info(self):
        """Test setting system information metrics."""
        # Set system info
        self.metrics_collector.set_system_info("1.0.0", "test", "2024-01-16")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_system_info' in metrics
        assert 'version="1.0.0"' in metrics
        assert 'environment="test"' in metrics

    @pytest.mark.asyncio
    async def test_timing_context_managers(self):
        """Test timing context managers."""
        # Test message ingestion timing
        async with self.metrics_collector.time_message_ingestion("gmail"):
            await asyncio.sleep(0.01)  # Simulate work

        # Test API request timing
        async with self.metrics_collector.time_api_request("GET", "/test"):
            await asyncio.sleep(0.01)  # Simulate work

        # Test AI processing timing
        async with self.metrics_collector.time_ai_processing("test_agent", "test_op"):
            await asyncio.sleep(0.01)  # Simulate work

        # Get metrics and verify histograms exist
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_message_ingestion_duration_seconds' in metrics
        assert 'mesh_api_request_duration_seconds' in metrics
        assert 'mesh_ai_processing_duration_seconds' in metrics

    def test_business_metrics(self):
        """Test business metrics recording."""
        # Set business metrics
        self.metrics_collector.set_active_users(42)
        self.metrics_collector.set_total_threads("gmail", 100)
        self.metrics_collector.set_total_messages("slack", 500)

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_active_users' in metrics
        assert 'mesh_total_threads' in metrics
        assert 'mesh_total_messages' in metrics

    def test_resource_metrics(self):
        """Test resource usage metrics."""
        # Set resource metrics
        self.metrics_collector.set_active_connections("database", 10)
        self.metrics_collector.set_memory_usage(
            "ai_engine", 1024 * 1024 * 100)  # 100MB

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_active_connections' in metrics
        assert 'mesh_memory_usage_bytes' in metrics

    def test_event_bus_metrics(self):
        """Test event bus metrics."""
        # Record event operations
        self.metrics_collector.record_event_published(
            "message_received", "success")
        self.metrics_collector.record_event_consumed(
            "message_received", "ai_processor", "success")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_events_published_total' in metrics
        assert 'mesh_events_consumed_total' in metrics

    def test_database_metrics(self):
        """Test database operation metrics."""
        # Record database operations
        self.metrics_collector.record_database_operation(
            "insert", "messages", "success")
        self.metrics_collector.record_database_operation(
            "select", "threads", "success")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_database_operations_total' in metrics

    def test_vector_db_metrics(self):
        """Test vector database metrics."""
        # Record vector operations
        self.metrics_collector.record_vector_operation("insert", "success")
        self.metrics_collector.record_vector_operation("search", "success")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_vector_operations_total' in metrics

    def test_search_metrics(self):
        """Test search operation metrics."""
        # Record search operations
        self.metrics_collector.record_search_query("hybrid", "success")
        self.metrics_collector.record_search_query("vector", "success")

        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        assert 'mesh_search_queries_total' in metrics

    def test_get_content_type(self):
        """Test getting content type for metrics endpoint."""
        content_type = self.metrics_collector.get_content_type()
        assert content_type == 'text/plain; version=0.0.4; charset=utf-8'

    def test_global_metrics_collector(self):
        """Test global metrics collector singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # Should be the same instance
        assert collector1 is collector2

    @patch('services.monitoring.metrics.psutil')
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, mock_psutil):
        """Test system metrics collection."""
        from services.monitoring.metrics import collect_system_metrics

        # Mock psutil
        mock_memory = Mock()
        mock_memory.used = 1024 * 1024 * 512  # 512MB
        mock_psutil.virtual_memory.return_value = mock_memory

        # Collect metrics
        await collect_system_metrics()

        # Verify psutil was called
        mock_psutil.virtual_memory.assert_called_once()


class TestMetricsIntegration:
    """Test metrics integration with other components."""

    @pytest.mark.asyncio
    async def test_metrics_with_error_handling(self):
        """Test metrics collection handles errors gracefully."""
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        # Test that metrics collection doesn't fail with invalid data
        try:
            collector.record_message_ingested("", "")  # Empty strings
            collector.record_api_request("", "", 0)    # Invalid status code
            collector.set_connector_health("", "", True)  # Empty platform
        except Exception as e:
            pytest.fail(
                f"Metrics collection should handle invalid data gracefully: {e}")

    def test_metrics_format_validation(self):
        """Test that metrics are in valid Prometheus format."""
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        # Record some metrics
        collector.record_message_ingested("gmail", "success")
        collector.record_api_request("GET", "/test", 200)

        # Get metrics
        metrics = collector.get_metrics()

        # Basic format validation
        assert isinstance(metrics, str)
        assert len(metrics) > 0
        assert 'mesh_messages_ingested_total' in metrics
        assert 'mesh_api_requests_total' in metrics

        # Check for proper Prometheus format elements
        lines = metrics.split('\n')
        metric_lines = [
            line for line in lines if not line.startswith('#') and line.strip()]

        for line in metric_lines:
            if line.strip():
                # Each metric line should have a value
                assert ' ' in line or '\t' in line

    @pytest.mark.asyncio
    async def test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection."""
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        async def record_metrics(platform: str, count: int):
            """Record metrics concurrently."""
            for i in range(count):
                collector.record_message_ingested(platform, "success")
                collector.record_api_request("GET", f"/test/{i}", 200)
                await asyncio.sleep(0.001)  # Small delay

        # Run concurrent metric recording
        tasks = [
            record_metrics("gmail", 10),
            record_metrics("slack", 10),
            record_metrics("discord", 10)
        ]

        await asyncio.gather(*tasks)

        # Verify metrics were recorded
        metrics = collector.get_metrics()
        assert 'platform="gmail"' in metrics
        assert 'platform="slack"' in metrics
        assert 'platform="discord"' in metrics
