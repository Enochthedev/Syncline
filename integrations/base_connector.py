"""
Base connector framework for platform integrations.

This module provides the abstract base class and core utilities for implementing
platform-specific connectors with authentication, health monitoring, and error handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union
from uuid import uuid4

import aiohttp
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ConnectorStatus(Enum):
    """Connector health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"
    AUTHENTICATING = "authenticating"


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class RateLimitError(Exception):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class ConnectorHealth:
    """Connector health status information."""
    status: ConnectorStatus
    last_check: datetime
    error_count: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RawMessage:
    """Raw message data from platform APIs."""
    id: str
    platform: str
    platform_message_id: str
    thread_id: str
    sender_id: str
    content: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)


class TokenInfo(BaseModel):
    """Token information for secure storage."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def expires_soon(self, buffer_minutes: int = 5) -> bool:
        """Check if token expires within buffer time."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(minutes=buffer_minutes))


class BaseConnector(ABC):
    """
    Abstract base class for platform connectors.

    Provides common functionality for authentication, health monitoring,
    rate limiting, and message processing.
    """

    def __init__(
        self,
        platform: str,
        config: Dict[str, Any],
        rate_limiter: Optional['RateLimiter'] = None,
        circuit_breaker: Optional['CircuitBreaker'] = None,
        token_manager: Optional['TokenManager'] = None
    ):
        self.platform = platform
        self.config = config
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.token_manager = token_manager

        self._health = ConnectorHealth(
            status=ConnectorStatus.DISCONNECTED,
            last_check=datetime.now(timezone.utc)
        )
        self._start_time = datetime.now(timezone.utc)
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

    @property
    def health(self) -> ConnectorHealth:
        """Get current health status."""
        self._health.uptime_seconds = (
            datetime.now(timezone.utc) - self._start_time).total_seconds()
        return self._health

    @property
    def is_running(self) -> bool:
        """Check if connector is running."""
        return self._running

    async def start(self) -> None:
        """Start the connector."""
        try:
            logger.info(f"Starting {self.platform} connector")
            self._running = True
            self._start_time = datetime.now(timezone.utc)

            # Initialize HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": f"MESH-Connector/{self.platform}"}
            )

            # Authenticate
            await self._authenticate()

            # Start real-time ingestion
            await self.start_real_time_ingestion()

            self._health.status = ConnectorStatus.HEALTHY
            logger.info(f"{self.platform} connector started successfully")

        except Exception as e:
            logger.error(f"Failed to start {self.platform} connector: {e}")
            self._running = False
            self._health.status = ConnectorStatus.UNHEALTHY
            self._health.last_error = str(e)
            self._health.error_count += 1

            # Clean up session if it was created
            if self._session:
                await self._session.close()
                self._session = None

            raise

    async def stop(self) -> None:
        """Stop the connector."""
        try:
            logger.info(f"Stopping {self.platform} connector")
            self._running = False

            await self.stop_real_time_ingestion()

            if self._session:
                await self._session.close()
                self._session = None

            self._health.status = ConnectorStatus.DISCONNECTED
            logger.info(f"{self.platform} connector stopped")

        except Exception as e:
            logger.error(f"Error stopping {self.platform} connector: {e}")
            self._health.last_error = str(e)
            self._health.error_count += 1

    async def health_check(self) -> ConnectorHealth:
        """Perform health check."""
        try:
            self._health.last_check = datetime.now(timezone.utc)

            if not self._running:
                self._health.status = ConnectorStatus.DISCONNECTED
                return self._health

            # Check authentication
            if self.token_manager:
                token = await self.token_manager.get_token(self.platform)
                if not token or token.is_expired():
                    self._health.status = ConnectorStatus.AUTHENTICATING
                    await self._authenticate()

            # Perform platform-specific health check
            await self._platform_health_check()

            if self._health.status != ConnectorStatus.UNHEALTHY:
                self._health.status = ConnectorStatus.HEALTHY

        except Exception as e:
            logger.error(f"Health check failed for {self.platform}: {e}")
            self._health.status = ConnectorStatus.UNHEALTHY
            self._health.last_error = str(e)
            self._health.error_count += 1

        # Update uptime
        self._health.uptime_seconds = (
            datetime.now(timezone.utc) - self._start_time).total_seconds()

        return self._health

    async def _authenticate(self) -> None:
        """Internal authentication wrapper."""
        try:
            self._health.status = ConnectorStatus.AUTHENTICATING
            await self.authenticate()
            logger.info(f"Authentication successful for {self.platform}")
        except Exception as e:
            logger.error(f"Authentication failed for {self.platform}: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with rate limiting and circuit breaker."""
        if not self._session:
            raise RuntimeError("Connector not started")

        # Check circuit breaker
        if self.circuit_breaker and not await self.circuit_breaker.can_execute():
            raise CircuitBreakerError("Circuit breaker is open")

        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        try:
            # Add authentication headers
            if self.token_manager:
                token = await self.token_manager.get_token(self.platform)
                if token:
                    kwargs.setdefault('headers', {})
                    kwargs['headers']['Authorization'] = f"{token.token_type} {token.access_token}"

            response = await self._session.request(method, url, **kwargs)

            # Record success for circuit breaker
            if self.circuit_breaker:
                await self.circuit_breaker.record_success()

            return response

        except Exception as e:
            # Record failure for circuit breaker
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure()

            # Handle rate limiting
            if isinstance(e, aiohttp.ClientResponseError) and e.status == 429:
                retry_after = None
                if 'Retry-After' in e.headers:
                    retry_after = int(e.headers['Retry-After'])
                raise RateLimitError(f"Rate limit exceeded: {e}", retry_after)

            raise

    # Abstract methods that must be implemented by subclasses

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the platform."""
        pass

    @abstractmethod
    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion."""
        pass

    @abstractmethod
    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        pass

    @abstractmethod
    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """Fetch historical messages."""
        pass

    @abstractmethod
    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Handle incoming webhook payload."""
        pass

    async def _platform_health_check(self) -> None:
        """Platform-specific health check. Override if needed."""
        pass
