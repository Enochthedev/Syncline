"""
Prometheus Metrics

Provides Prometheus metrics for monitoring:
- HTTP request metrics (duration, count, errors)
- Message processing metrics
- Collection job metrics
- AI processing metrics
- Database metrics
- WebSocket connection metrics
"""

import logging
import time
from functools import wraps
from typing import Callable, Any

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)

logger = logging.getLogger(__name__)

# Create registry
registry = CollectorRegistry()

# =============================================================================
# HTTP Metrics
# =============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests in progress",
    registry=registry,
)

# =============================================================================
# Message Processing Metrics
# =============================================================================

messages_collected_total = Counter(
    "messages_collected_total",
    "Total messages collected",
    ["platform"],
    registry=registry,
)

messages_processed_total = Counter(
    "messages_processed_total",
    "Total messages processed/normalized",
    ["platform"],
    registry=registry,
)

messages_failed_total = Counter(
    "messages_failed_total",
    "Total messages that failed processing",
    ["platform", "stage"],
    registry=registry,
)

message_processing_duration_seconds = Histogram(
    "message_processing_duration_seconds",
    "Message processing duration in seconds",
    ["stage"],
    registry=registry,
)

messages_in_queue = Gauge(
    "messages_in_queue",
    "Messages waiting in processing queue",
    ["stage"],
    registry=registry,
)

# =============================================================================
# Collection Job Metrics
# =============================================================================

collection_jobs_total = Counter(
    "collection_jobs_total",
    "Total collection jobs",
    ["platform", "status"],
    registry=registry,
)

collection_job_duration_seconds = Histogram(
    "collection_job_duration_seconds",
    "Collection job duration in seconds",
    ["platform"],
    registry=registry,
)

collection_jobs_active = Gauge(
    "collection_jobs_active",
    "Active collection jobs",
    ["platform"],
    registry=registry,
)

# =============================================================================
# AI Processing Metrics
# =============================================================================

ai_embeddings_generated_total = Counter(
    "ai_embeddings_generated_total",
    "Total embeddings generated",
    registry=registry,
)

ai_entities_extracted_total = Counter(
    "ai_entities_extracted_total",
    "Total entities extracted",
    ["entity_type"],
    registry=registry,
)

ai_summaries_generated_total = Counter(
    "ai_summaries_generated_total",
    "Total summaries generated",
    ["summary_type"],
    registry=registry,
)

ai_processing_duration_seconds = Histogram(
    "ai_processing_duration_seconds",
    "AI processing duration in seconds",
    ["operation"],
    registry=registry,
)

ai_processing_errors_total = Counter(
    "ai_processing_errors_total",
    "Total AI processing errors",
    ["operation"],
    registry=registry,
)

# =============================================================================
# Database Metrics
# =============================================================================

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    registry=registry,
)

db_errors_total = Counter(
    "db_errors_total",
    "Total database errors",
    ["operation"],
    registry=registry,
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

websocket_connections_active = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
    registry=registry,
)

websocket_messages_sent_total = Counter(
    "websocket_messages_sent_total",
    "Total WebSocket messages sent",
    ["message_type"],
    registry=registry,
)

websocket_messages_received_total = Counter(
    "websocket_messages_received_total",
    "Total WebSocket messages received",
    ["message_type"],
    registry=registry,
)

# =============================================================================
# Platform Connection Metrics
# =============================================================================

platform_connections_total = Gauge(
    "platform_connections_total",
    "Total platform connections",
    ["platform", "status"],
    registry=registry,
)

platform_connection_errors_total = Counter(
    "platform_connection_errors_total",
    "Total platform connection errors",
    ["platform", "error_type"],
    registry=registry,
)

# =============================================================================
# Application Info
# =============================================================================

app_info = Info(
    "remi_app",
    "Application information",
    registry=registry,
)

# Set app info
app_info.info({
    "name": "R.E.M.I Backend",
    "version": "1.0.0",
    "environment": "development",
})

# =============================================================================
# Metric Helpers
# =============================================================================


def track_request_metrics(method: str, endpoint: str, status: int, duration: float):
    """
    Track HTTP request metrics.

    Args:
        method: HTTP method
        endpoint: Endpoint path
        status: Status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_message_collected(platform: str):
    """Track message collection."""
    messages_collected_total.labels(platform=platform).inc()


def track_message_processed(platform: str):
    """Track message processing."""
    messages_processed_total.labels(platform=platform).inc()


def track_message_failed(platform: str, stage: str):
    """Track message processing failure."""
    messages_failed_total.labels(platform=platform, stage=stage).inc()


def track_collection_job(platform: str, status: str):
    """Track collection job."""
    collection_jobs_total.labels(platform=platform, status=status).inc()


def track_ai_embedding():
    """Track embedding generation."""
    ai_embeddings_generated_total.inc()


def track_ai_entity(entity_type: str):
    """Track entity extraction."""
    ai_entities_extracted_total.labels(entity_type=entity_type).inc()


def track_ai_summary(summary_type: str):
    """Track summary generation."""
    ai_summaries_generated_total.labels(summary_type=summary_type).inc()


def track_websocket_connection(delta: int):
    """
    Track WebSocket connection change.

    Args:
        delta: +1 for new connection, -1 for disconnection
    """
    if delta > 0:
        websocket_connections_active.inc(delta)
    else:
        websocket_connections_active.dec(abs(delta))


def track_websocket_message_sent(message_type: str):
    """Track WebSocket message sent."""
    websocket_messages_sent_total.labels(message_type=message_type).inc()


def track_websocket_message_received(message_type: str):
    """Track WebSocket message received."""
    websocket_messages_received_total.labels(message_type=message_type).inc()


# =============================================================================
# Decorators
# =============================================================================


def track_time(metric: Histogram, *labels):
    """
    Decorator to track execution time.

    Args:
        metric: Histogram metric to track
        *labels: Label values for the metric
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.labels(*labels).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.labels(*labels).observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """
    Get content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST


__all__ = [
    "registry",
    "track_request_metrics",
    "track_message_collected",
    "track_message_processed",
    "track_message_failed",
    "track_collection_job",
    "track_ai_embedding",
    "track_ai_entity",
    "track_ai_summary",
    "track_websocket_connection",
    "track_websocket_message_sent",
    "track_websocket_message_received",
    "track_time",
    "get_metrics",
    "get_metrics_content_type",
    # Metrics
    "http_requests_total",
    "http_request_duration_seconds",
    "messages_collected_total",
    "messages_processed_total",
    "ai_embeddings_generated_total",
    "websocket_connections_active",
]
