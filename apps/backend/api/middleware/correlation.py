"""
Correlation ID Middleware

Adds correlation IDs to all requests for distributed tracing:
- Generates or accepts correlation ID from headers
- Adds correlation ID to response headers
- Propagates correlation ID through the request context
- Enables request tracing across services
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Context variable to store correlation ID for the current request
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds correlation IDs to all requests.

    The correlation ID can be:
    - Provided by the client via X-Correlation-ID header
    - Generated automatically if not provided

    The correlation ID is:
    - Added to the response headers
    - Made available in the request context
    - Included in all log messages during the request
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Correlation-ID",
        request_id_header: str = "X-Request-ID",
    ):
        """
        Initialize middleware.

        Args:
            app: ASGI application
            header_name: Header name for correlation ID
            request_id_header: Header name for request ID
        """
        super().__init__(app)
        self.header_name = header_name
        self.request_id_header = request_id_header

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and add correlation ID.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with correlation ID header
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            self.header_name, str(uuid.uuid4())
        )

        # Get or generate request ID
        request_id = request.headers.get(
            self.request_id_header, str(uuid.uuid4())
        )

        # Set in context vars
        correlation_id_var.set(correlation_id)
        request_id_var.set(request_id)

        # Add to request state for access in handlers
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        # Process request
        start_time = time.time()

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Add headers to response
            response.headers[self.header_name] = correlation_id
            response.headers[self.request_id_header] = request_id
            response.headers["X-Request-Duration"] = f"{duration:.3f}"

            # Log request completion
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.3f}s",
                extra={
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            )

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"Duration: {duration:.3f}s",
                exc_info=True,
                extra={
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "duration": duration,
                    "client_ip": request.client.host if request.client else None,
                }
            )

            raise

        finally:
            # Clear context vars
            correlation_id_var.set(None)
            request_id_var.set(None)


def get_correlation_id() -> str | None:
    """
    Get the correlation ID for the current request.

    Returns:
        Correlation ID or None if not in request context
    """
    return correlation_id_var.get()


def get_request_id() -> str | None:
    """
    Get the request ID for the current request.

    Returns:
        Request ID or None if not in request context
    """
    return request_id_var.get()


__all__ = [
    "CorrelationIdMiddleware",
    "get_correlation_id",
    "get_request_id",
    "correlation_id_var",
    "request_id_var",
]
