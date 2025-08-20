"""Monitoring middleware for automatic metrics collection and correlation IDs."""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from services.monitoring.metrics import get_metrics_collector
from services.monitoring.logging import set_correlation_id, get_logger

logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic metrics collection and correlation ID injection."""

    def __init__(self, app, service_name: str = "mesh-api"):
        """Initialize monitoring middleware."""
        super().__init__(app)
        self.service_name = service_name
        self.metrics_collector = get_metrics_collector()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with monitoring."""
        # Generate or extract correlation ID
        correlation_id = (
            request.headers.get("x-correlation-id") or
            request.headers.get("x-request-id") or
            str(uuid.uuid4())
        )

        # Set correlation ID in context
        set_correlation_id(correlation_id)

        # Start timing
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code

            # Record successful request
            self.metrics_collector.record_api_request(
                method, path, status_code)

        except Exception as e:
            # Record failed request
            status_code = 500
            self.metrics_collector.record_api_request(
                method, path, status_code)

            logger.error(
                f"Request failed: {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "correlation_id": correlation_id
                }
            )
            raise

        finally:
            # Calculate duration and record timing
            duration = time.time() - start_time

            async with self.metrics_collector.time_api_request(method, path):
                pass  # Duration already calculated

        # Add correlation ID to response headers
        response.headers["x-correlation-id"] = correlation_id

        # Log request completion
        logger.info(
            f"Request completed: {method} {path} -> {status_code}",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration * 1000,
                "correlation_id": correlation_id
            }
        )

        return response


class MetricsCollectionMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for collecting detailed metrics."""

    def __init__(self, app):
        """Initialize metrics collection middleware."""
        super().__init__(app)
        self.metrics_collector = get_metrics_collector()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect detailed metrics for the request."""
        method = request.method
        path = request.url.path

        # Use the metrics collector's timing context manager
        async with self.metrics_collector.time_api_request(method, path):
            response = await call_next(request)

        # Record the API request
        self.metrics_collector.record_api_request(
            method, path, response.status_code)

        return response
