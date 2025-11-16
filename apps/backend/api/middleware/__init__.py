"""
API Middleware

Provides middleware for:
- Correlation ID tracking
- Request tracing
- Metrics collection
"""

from api.middleware.correlation import (
    CorrelationIdMiddleware,
    get_correlation_id,
    get_request_id,
)

__all__ = [
    "CorrelationIdMiddleware",
    "get_correlation_id",
    "get_request_id",
]
