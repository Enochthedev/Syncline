"""Prometheus metrics collection for MESH system."""

import time
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from prometheus_client import (
    Counter, Histogram, Gauge, Info, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST
)
import asyncio
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Centralized metrics collection for all MESH services."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics collector with optional custom registry."""
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self):
        """Set up all Prometheus metrics."""

        # System info
        self.system_info = Info(
            'mesh_system_info',
            'MESH system information',
            registry=self.registry
        )

        # Message ingestion metrics
        self.messages_ingested_total = Counter(
            'mesh_messages_ingested_total',
            'Total number of messages ingested',
            ['platform', 'status'],
            registry=self.registry
        )

        self.message_ingestion_duration = Histogram(
            'mesh_message_ingestion_duration_seconds',
            'Time spent ingesting messages',
            ['platform'],
            registry=self.registry
        )

        # AI processing metrics
        self.ai_processing_duration = Histogram(
            'mesh_ai_processing_duration_seconds',
            'Time spent in AI processing',
            ['agent_type', 'operation'],
            registry=self.registry
        )

        self.ai_operations_total = Counter(
            'mesh_ai_operations_total',
            'Total AI operations performed',
            ['agent_type', 'operation', 'status'],
            registry=self.registry
        )

        # Search metrics
        self.search_queries_total = Counter(
            'mesh_search_queries_total',
            'Total search queries performed',
            ['query_type', 'status'],
            registry=self.registry
        )

        self.search_duration = Histogram(
            'mesh_search_duration_seconds',
            'Time spent processing search queries',
            ['query_type'],
            registry=self.registry
        )

        # Connector health metrics
        self.connector_health = Gauge(
            'mesh_connector_health',
            'Health status of platform connectors (1=healthy, 0=unhealthy)',
            ['platform', 'connector_type'],
            registry=self.registry
        )

        self.connector_operations_total = Counter(
            'mesh_connector_operations_total',
            'Total connector operations',
            ['platform', 'operation', 'status'],
            registry=self.registry
        )

        # Database metrics
        self.database_operations_total = Counter(
            'mesh_database_operations_total',
            'Total database operations',
            ['operation', 'table', 'status'],
            registry=self.registry
        )

        self.database_operation_duration = Histogram(
            'mesh_database_operation_duration_seconds',
            'Time spent on database operations',
            ['operation', 'table'],
            registry=self.registry
        )

        # Vector database metrics
        self.vector_operations_total = Counter(
            'mesh_vector_operations_total',
            'Total vector database operations',
            ['operation', 'status'],
            registry=self.registry
        )

        self.vector_operation_duration = Histogram(
            'mesh_vector_operation_duration_seconds',
            'Time spent on vector database operations',
            ['operation'],
            registry=self.registry
        )

        # Event bus metrics
        self.events_published_total = Counter(
            'mesh_events_published_total',
            'Total events published to event bus',
            ['event_type', 'status'],
            registry=self.registry
        )

        self.events_consumed_total = Counter(
            'mesh_events_consumed_total',
            'Total events consumed from event bus',
            ['event_type', 'consumer_group', 'status'],
            registry=self.registry
        )

        # API metrics
        self.api_requests_total = Counter(
            'mesh_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.api_request_duration = Histogram(
            'mesh_api_request_duration_seconds',
            'Time spent processing API requests',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # Resource usage metrics
        self.active_connections = Gauge(
            'mesh_active_connections',
            'Number of active connections',
            ['connection_type'],
            registry=self.registry
        )

        self.memory_usage_bytes = Gauge(
            'mesh_memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )

        # Business metrics
        self.active_users = Gauge(
            'mesh_active_users',
            'Number of active users',
            registry=self.registry
        )

        self.total_threads = Gauge(
            'mesh_total_threads',
            'Total number of conversation threads',
            ['platform'],
            registry=self.registry
        )

        self.total_messages = Gauge(
            'mesh_total_messages',
            'Total number of messages stored',
            ['platform'],
            registry=self.registry
        )

    def set_system_info(self, version: str, environment: str, build_date: str):
        """Set system information metrics."""
        self.system_info.info({
            'version': version,
            'environment': environment,
            'build_date': build_date
        })

    # Message ingestion methods
    def record_message_ingested(self, platform: str, status: str = 'success'):
        """Record a message ingestion event."""
        self.messages_ingested_total.labels(
            platform=platform, status=status).inc()

    @asynccontextmanager
    async def time_message_ingestion(self, platform: str):
        """Context manager to time message ingestion."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.message_ingestion_duration.labels(
                platform=platform).observe(duration)

    # AI processing methods
    def record_ai_operation(self, agent_type: str, operation: str, status: str = 'success'):
        """Record an AI operation."""
        self.ai_operations_total.labels(
            agent_type=agent_type,
            operation=operation,
            status=status
        ).inc()

    @asynccontextmanager
    async def time_ai_processing(self, agent_type: str, operation: str):
        """Context manager to time AI processing."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.ai_processing_duration.labels(
                agent_type=agent_type,
                operation=operation
            ).observe(duration)

    # Search methods
    def record_search_query(self, query_type: str, status: str = 'success'):
        """Record a search query."""
        self.search_queries_total.labels(
            query_type=query_type, status=status).inc()

    @asynccontextmanager
    async def time_search_operation(self, query_type: str):
        """Context manager to time search operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.search_duration.labels(
                query_type=query_type).observe(duration)

    # Connector methods
    def set_connector_health(self, platform: str, connector_type: str, healthy: bool):
        """Set connector health status."""
        self.connector_health.labels(
            platform=platform,
            connector_type=connector_type
        ).set(1 if healthy else 0)

    def record_connector_operation(self, platform: str, operation: str, status: str = 'success'):
        """Record a connector operation."""
        self.connector_operations_total.labels(
            platform=platform,
            operation=operation,
            status=status
        ).inc()

    # Database methods
    def record_database_operation(self, operation: str, table: str, status: str = 'success'):
        """Record a database operation."""
        self.database_operations_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()

    @asynccontextmanager
    async def time_database_operation(self, operation: str, table: str):
        """Context manager to time database operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.database_operation_duration.labels(
                operation=operation,
                table=table
            ).observe(duration)

    # Vector database methods
    def record_vector_operation(self, operation: str, status: str = 'success'):
        """Record a vector database operation."""
        self.vector_operations_total.labels(
            operation=operation, status=status).inc()

    @asynccontextmanager
    async def time_vector_operation(self, operation: str):
        """Context manager to time vector database operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.vector_operation_duration.labels(
                operation=operation).observe(duration)

    # Event bus methods
    def record_event_published(self, event_type: str, status: str = 'success'):
        """Record an event publication."""
        self.events_published_total.labels(
            event_type=event_type, status=status).inc()

    def record_event_consumed(self, event_type: str, consumer_group: str, status: str = 'success'):
        """Record an event consumption."""
        self.events_consumed_total.labels(
            event_type=event_type,
            consumer_group=consumer_group,
            status=status
        ).inc()

    # API methods
    def record_api_request(self, method: str, endpoint: str, status_code: int):
        """Record an API request."""
        self.api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

    @asynccontextmanager
    async def time_api_request(self, method: str, endpoint: str):
        """Context manager to time API requests."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.api_request_duration.labels(
                method=method, endpoint=endpoint).observe(duration)

    # Resource usage methods
    def set_active_connections(self, connection_type: str, count: int):
        """Set active connection count."""
        self.active_connections.labels(
            connection_type=connection_type).set(count)

    def set_memory_usage(self, component: str, bytes_used: int):
        """Set memory usage for a component."""
        self.memory_usage_bytes.labels(component=component).set(bytes_used)

    # Business metrics methods
    def set_active_users(self, count: int):
        """Set active user count."""
        self.active_users.set(count)

    def set_total_threads(self, platform: str, count: int):
        """Set total thread count for a platform."""
        self.total_threads.labels(platform=platform).set(count)

    def set_total_messages(self, platform: str, count: int):
        """Set total message count for a platform."""
        self.total_messages.labels(platform=platform).set(count)

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')

    def get_content_type(self) -> str:
        """Get the content type for metrics endpoint."""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        # Set system info
        _metrics_collector.set_system_info(
            version="1.0.0",
            environment="development",
            build_date=time.strftime("%Y-%m-%d")
        )
    return _metrics_collector


async def collect_system_metrics():
    """Collect system-wide metrics periodically."""
    metrics = get_metrics_collector()

    try:
        # This would be expanded to collect actual system metrics
        import psutil

        # Memory usage
        memory = psutil.virtual_memory()
        metrics.set_memory_usage("system", memory.used)

        # Connection counts (placeholder - would integrate with actual connection pools)
        metrics.set_active_connections("database", 10)  # Example
        metrics.set_active_connections("redis", 5)      # Example

        logger.debug("System metrics collected successfully")

    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")
