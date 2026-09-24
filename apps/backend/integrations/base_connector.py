"""
Base Connector Framework

Abstract base class for all platform connectors with:
- Health monitoring and status tracking
- Rate limiting support
- Circuit breaker pattern for fault tolerance
- Standardized connector interface
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Status Types
# =============================================================================


class ConnectorStatus(str, Enum):
    """Connector operational status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# =============================================================================
# Exception Classes
# =============================================================================


class ConnectorException(Exception):
    """Base exception for connector errors."""

    pass


class ConnectionError(ConnectorException):
    """Raised when connection to platform fails."""

    pass


class AuthenticationError(ConnectorException):
    """Raised when authentication fails."""

    pass


class RateLimitError(ConnectorException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class CircuitBreakerOpenError(ConnectorException):
    """Raised when circuit breaker is open."""

    pass


# =============================================================================
# Data Models
# =============================================================================


class ConnectorHealth(BaseModel):
    """Health check result for a connector."""

    status: HealthStatus = Field(description="Overall health status")
    connector_status: ConnectorStatus = Field(
        description="Connector operational status"
    )
    last_check_at: datetime = Field(description="Last health check timestamp")
    last_success_at: Optional[datetime] = Field(
        default=None, description="Last successful operation"
    )
    last_error_at: Optional[datetime] = Field(
        default=None, description="Last error timestamp"
    )
    last_error: Optional[str] = Field(default=None, description="Last error message")
    consecutive_failures: int = Field(
        default=0, description="Number of consecutive failures"
    )
    circuit_breaker_open: bool = Field(
        default=False, description="Whether circuit breaker is open"
    )
    rate_limit_remaining: Optional[int] = Field(
        default=None, description="Remaining rate limit quota"
    )
    rate_limit_reset_at: Optional[datetime] = Field(
        default=None, description="Rate limit reset time"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional platform-specific health data"
    )


class CircuitBreakerState(BaseModel):
    """Circuit breaker state tracking."""

    is_open: bool = Field(default=False, description="Whether circuit is open")
    failure_count: int = Field(default=0, description="Consecutive failure count")
    last_failure_at: Optional[datetime] = Field(
        default=None, description="Last failure timestamp"
    )
    opened_at: Optional[datetime] = Field(
        default=None, description="When circuit was opened"
    )
    half_open_at: Optional[datetime] = Field(
        default=None, description="When circuit enters half-open state"
    )


# =============================================================================
# Base Connector Abstract Class
# =============================================================================


class BaseConnector(ABC):
    """
    Abstract base class for platform connectors.

    Provides:
    - Connection lifecycle management (connect, disconnect, refresh)
    - Health monitoring and status tracking
    - Rate limiting support
    - Circuit breaker pattern for fault tolerance
    - Standardized error handling

    Subclasses must implement:
    - _connect(): Platform-specific connection logic
    - _disconnect(): Platform-specific disconnection logic
    - _refresh_token(): Platform-specific token refresh
    - _check_health(): Platform-specific health check
    - platform_name: Property returning platform identifier
    """

    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 60,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize base connector.

        Args:
            connection_id: Unique identifier for this connection
            credentials: Platform credentials (tokens, API keys, etc.)
            rate_limit_per_minute: Maximum requests per minute
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds before attempting recovery
        """
        self.connection_id = connection_id
        self.credentials = credentials
        self.rate_limit_per_minute = rate_limit_per_minute
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Status tracking
        self._status = ConnectorStatus.DISCONNECTED
        self._last_success_at: Optional[datetime] = None
        self._last_error_at: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._consecutive_failures = 0

        # Circuit breaker state
        self._circuit_breaker = CircuitBreakerState()

        # Rate limiting state
        self._rate_limit_tokens = rate_limit_per_minute
        self._rate_limit_last_reset = datetime.utcnow()

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    # =========================================================================
    # Abstract Methods (Must be implemented by subclasses)
    # =========================================================================

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'gmail', 'slack')."""
        pass

    @abstractmethod
    async def _connect(self) -> None:
        """
        Platform-specific connection logic.

        Should establish connection to the platform API and verify credentials.
        Raises ConnectionError or AuthenticationError on failure.
        """
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """
        Platform-specific disconnection logic.

        Should cleanly close connections and release resources.
        """
        pass

    @abstractmethod
    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Platform-specific token refresh logic.

        Returns:
            Updated credentials dictionary

        Raises:
            AuthenticationError: If token refresh fails
        """
        pass

    @abstractmethod
    async def _check_health(self) -> Dict[str, Any]:
        """
        Platform-specific health check logic.

        Should perform a lightweight API call to verify connectivity.

        Returns:
            Dictionary with platform-specific health metadata

        Raises:
            Exception: If health check fails
        """
        pass

    # =========================================================================
    # Public Interface
    # =========================================================================

    async def connect(self) -> None:
        """
        Connect to the platform.

        Establishes connection with circuit breaker protection.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            CircuitBreakerOpenError: If circuit breaker is open
        """
        async with self._lock:
            # Check circuit breaker
            if self._circuit_breaker.is_open:
                if not self._should_attempt_recovery():
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is open for {self.platform_name}"
                    )
                # Attempt recovery (half-open state)
                self._circuit_breaker.half_open_at = datetime.utcnow()
                logger.info(
                    f"Circuit breaker entering half-open state for {self.platform_name}"
                )

            try:
                self._status = ConnectorStatus.CONNECTING
                logger.info(f"Connecting to {self.platform_name}...")

                await self._connect()

                self._status = ConnectorStatus.CONNECTED
                self._last_success_at = datetime.utcnow()
                self._consecutive_failures = 0

                # Close circuit breaker on success
                if self._circuit_breaker.is_open:
                    self._close_circuit_breaker()

                logger.info(f"Successfully connected to {self.platform_name}")

            except Exception as e:
                self._handle_failure(e)
                raise

    async def disconnect(self) -> None:
        """
        Disconnect from the platform.

        Cleanly closes connection and releases resources.
        """
        async with self._lock:
            try:
                logger.info(f"Disconnecting from {self.platform_name}...")
                await self._disconnect()
                self._status = ConnectorStatus.DISCONNECTED
                logger.info(f"Disconnected from {self.platform_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.platform_name}: {e}")
                self._status = ConnectorStatus.FAILED
                raise

    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh authentication token.

        Returns:
            Updated credentials dictionary

        Raises:
            AuthenticationError: If token refresh fails
        """
        async with self._lock:
            try:
                logger.info(f"Refreshing token for {self.platform_name}...")
                new_credentials = await self._refresh_token()
                self.credentials = new_credentials
                self._last_success_at = datetime.utcnow()
                logger.info(f"Token refreshed for {self.platform_name}")
                return new_credentials
            except Exception as e:
                logger.error(f"Token refresh failed for {self.platform_name}: {e}")
                self._handle_failure(e)
                raise

    async def health_check(self) -> ConnectorHealth:
        """
        Perform health check on the connector.

        Returns:
            ConnectorHealth object with current status
        """
        async with self._lock:
            try:
                # Perform platform-specific health check
                metadata = await self._check_health()

                # Update success tracking
                self._last_success_at = datetime.utcnow()
                self._consecutive_failures = 0

                # Determine health status
                if self._circuit_breaker.is_open:
                    health_status = HealthStatus.UNHEALTHY
                elif self._status == ConnectorStatus.RATE_LIMITED:
                    health_status = HealthStatus.DEGRADED
                elif self._status == ConnectorStatus.CONNECTED:
                    health_status = HealthStatus.HEALTHY
                else:
                    health_status = HealthStatus.DEGRADED

                return ConnectorHealth(
                    status=health_status,
                    connector_status=self._status,
                    last_check_at=datetime.utcnow(),
                    last_success_at=self._last_success_at,
                    last_error_at=self._last_error_at,
                    last_error=self._last_error,
                    consecutive_failures=self._consecutive_failures,
                    circuit_breaker_open=self._circuit_breaker.is_open,
                    rate_limit_remaining=self._rate_limit_tokens,
                    rate_limit_reset_at=self._get_rate_limit_reset_time(),
                    metadata=metadata,
                )

            except Exception as e:
                self._handle_failure(e)

                return ConnectorHealth(
                    status=HealthStatus.UNHEALTHY,
                    connector_status=self._status,
                    last_check_at=datetime.utcnow(),
                    last_success_at=self._last_success_at,
                    last_error_at=self._last_error_at,
                    last_error=str(e),
                    consecutive_failures=self._consecutive_failures,
                    circuit_breaker_open=self._circuit_breaker.is_open,
                    rate_limit_remaining=self._rate_limit_tokens,
                    rate_limit_reset_at=self._get_rate_limit_reset_time(),
                    metadata={},
                )

    async def check_rate_limit(self) -> bool:
        """
        Check if request can be made within rate limit.

        Returns:
            True if request can proceed, False if rate limited
        """
        async with self._lock:
            # Reset rate limit tokens if window has passed
            now = datetime.utcnow()
            if (now - self._rate_limit_last_reset).total_seconds() >= 60:
                self._rate_limit_tokens = self.rate_limit_per_minute
                self._rate_limit_last_reset = now

            # Check if tokens available
            if self._rate_limit_tokens > 0:
                self._rate_limit_tokens -= 1
                if self._status == ConnectorStatus.RATE_LIMITED:
                    self._status = ConnectorStatus.CONNECTED
                return True
            else:
                self._status = ConnectorStatus.RATE_LIMITED
                logger.warning(
                    f"Rate limit exceeded for {self.platform_name}. "
                    f"Reset at {self._get_rate_limit_reset_time()}"
                )
                return False

    # =========================================================================
    # Circuit Breaker Methods
    # =========================================================================

    def _handle_failure(self, error: Exception) -> None:
        """
        Handle operation failure and update circuit breaker state.

        Args:
            error: The exception that occurred
        """
        self._last_error_at = datetime.utcnow()
        self._last_error = str(error)
        self._consecutive_failures += 1

        # Update circuit breaker
        self._circuit_breaker.failure_count += 1
        self._circuit_breaker.last_failure_at = datetime.utcnow()

        # Open circuit if threshold exceeded
        if self._circuit_breaker.failure_count >= self.circuit_breaker_threshold:
            self._open_circuit_breaker()

        # Update status
        if isinstance(error, AuthenticationError):
            self._status = ConnectorStatus.FAILED
        elif isinstance(error, RateLimitError):
            self._status = ConnectorStatus.RATE_LIMITED
        else:
            self._status = ConnectorStatus.FAILED

    def _open_circuit_breaker(self) -> None:
        """Open the circuit breaker."""
        if not self._circuit_breaker.is_open:
            self._circuit_breaker.is_open = True
            self._circuit_breaker.opened_at = datetime.utcnow()
            self._status = ConnectorStatus.CIRCUIT_OPEN
            logger.error(
                f"Circuit breaker opened for {self.platform_name} "
                f"after {self._circuit_breaker.failure_count} failures"
            )

    def _close_circuit_breaker(self) -> None:
        """Close the circuit breaker after successful recovery."""
        self._circuit_breaker.is_open = False
        self._circuit_breaker.failure_count = 0
        self._circuit_breaker.opened_at = None
        self._circuit_breaker.half_open_at = None
        logger.info(f"Circuit breaker closed for {self.platform_name}")

    def _should_attempt_recovery(self) -> bool:
        """
        Check if circuit breaker should attempt recovery.

        Returns:
            True if enough time has passed to attempt recovery
        """
        if not self._circuit_breaker.is_open:
            return True

        if self._circuit_breaker.opened_at is None:
            return True

        time_since_open = (
            datetime.utcnow() - self._circuit_breaker.opened_at
        ).total_seconds()

        return time_since_open >= self.circuit_breaker_timeout

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_rate_limit_reset_time(self) -> datetime:
        """Get the time when rate limit will reset."""
        return self._rate_limit_last_reset + timedelta(minutes=1)

    @property
    def status(self) -> ConnectorStatus:
        """Get current connector status."""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Check if connector is currently connected."""
        return self._status == ConnectorStatus.CONNECTED

    @property
    def is_healthy(self) -> bool:
        """Check if connector is healthy (connected and not circuit broken)."""
        return (
            self._status == ConnectorStatus.CONNECTED
            and not self._circuit_breaker.is_open
        )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"platform={self.platform_name}, "
            f"status={self._status}, "
            f"connection_id={self.connection_id})>"
        )
