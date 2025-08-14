"""
Unit tests for base connector framework.

Tests the BaseConnector abstract class, health monitoring,
and core connector functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

from integrations.base_connector import (
    BaseConnector,
    ConnectorHealth,
    ConnectorStatus,
    RawMessage,
    TokenInfo,
    AuthenticationError,
    RateLimitError,
    CircuitBreakerError
)
from integrations.rate_limiter import RateLimiter, CircuitBreaker, RateLimitConfig, CircuitBreakerConfig
from integrations.token_manager import TokenManager


class TestConnector(BaseConnector):
    """Test implementation of BaseConnector."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authenticate_called = False
        self.start_ingestion_called = False
        self.stop_ingestion_called = False
        self.fetch_messages_called = False
        self.handle_webhook_called = False
        self.should_fail_auth = False
        self.should_fail_health = False

    async def authenticate(self) -> None:
        self.authenticate_called = True
        if self.should_fail_auth:
            raise AuthenticationError("Test auth failure")

    async def start_real_time_ingestion(self) -> None:
        self.start_ingestion_called = True

    async def stop_real_time_ingestion(self) -> None:
        self.stop_ingestion_called = True

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        self.fetch_messages_called = True
        return []

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        self.handle_webhook_called = True

    async def _platform_health_check(self) -> None:
        if self.should_fail_health:
            raise Exception("Test health check failure")


class TestTokenInfo:
    """Test TokenInfo model."""

    def test_token_info_creation(self):
        """Test TokenInfo creation and validation."""
        token = TokenInfo(
            access_token="test_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer",
            scope="read write"
        )

        assert token.access_token == "test_token"
        assert token.refresh_token == "refresh_token"
        assert token.token_type == "Bearer"
        assert token.scope == "read write"
        assert not token.is_expired()
        assert not token.expires_soon()

    def test_token_expiration(self):
        """Test token expiration logic."""
        # Expired token
        expired_token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert expired_token.is_expired()

        # Token expiring soon
        expiring_token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=2)
        )
        assert expiring_token.expires_soon()
        assert not expiring_token.is_expired()

    def test_token_no_expiration(self):
        """Test token without expiration."""
        token = TokenInfo(access_token="test_token")
        assert not token.is_expired()
        assert not token.expires_soon()


class TestBaseConnector:
    """Test BaseConnector functionality."""

    @pytest.fixture
    def connector_config(self):
        """Connector configuration fixture."""
        return {
            "api_key": "test_key",
            "base_url": "https://api.example.com"
        }

    @pytest.fixture
    def connector(self, connector_config):
        """Test connector fixture."""
        return TestConnector("test_platform", connector_config)

    @pytest.fixture
    def rate_limiter(self):
        """Rate limiter fixture."""
        config = RateLimitConfig(requests_per_second=10.0, burst_size=20)
        return RateLimiter(config)

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker fixture."""
        config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout_seconds=30)
        return CircuitBreaker(config)

    @pytest.fixture
    def token_manager(self):
        """Token manager fixture."""
        return AsyncMock(spec=TokenManager)

    def test_connector_initialization(self, connector):
        """Test connector initialization."""
        assert connector.platform == "test_platform"
        assert connector.config["api_key"] == "test_key"
        assert not connector.is_running
        assert connector.health.status == ConnectorStatus.DISCONNECTED

    def test_connector_with_utilities(self, connector_config, rate_limiter, circuit_breaker, token_manager):
        """Test connector with rate limiter, circuit breaker, and token manager."""
        connector = TestConnector(
            "test_platform",
            connector_config,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            token_manager=token_manager
        )

        assert connector.rate_limiter is rate_limiter
        assert connector.circuit_breaker is circuit_breaker
        assert connector.token_manager is token_manager

    @pytest.mark.asyncio
    async def test_connector_start_success(self, connector):
        """Test successful connector start."""
        await connector.start()

        assert connector.is_running
        assert connector.authenticate_called
        assert connector.start_ingestion_called
        assert connector.health.status == ConnectorStatus.HEALTHY
        assert connector._session is not None

    @pytest.mark.asyncio
    async def test_connector_start_auth_failure(self, connector):
        """Test connector start with authentication failure."""
        connector.should_fail_auth = True

        with pytest.raises(AuthenticationError):
            await connector.start()

        assert not connector.is_running
        assert connector.health.status == ConnectorStatus.UNHEALTHY
        assert connector.health.error_count == 1

    @pytest.mark.asyncio
    async def test_connector_stop(self, connector):
        """Test connector stop."""
        await connector.start()
        await connector.stop()

        assert not connector.is_running
        assert connector.stop_ingestion_called
        assert connector.health.status == ConnectorStatus.DISCONNECTED
        assert connector._session is None

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, connector):
        """Test health check when connector is healthy."""
        await connector.start()

        # Small delay to ensure uptime > 0
        await asyncio.sleep(0.01)

        health = await connector.health_check()

        assert health.status == ConnectorStatus.HEALTHY
        assert health.error_count == 0
        assert health.last_error is None
        assert health.uptime_seconds > 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, connector):
        """Test health check when connector is unhealthy."""
        await connector.start()
        connector.should_fail_health = True

        health = await connector.health_check()

        assert health.status == ConnectorStatus.UNHEALTHY
        assert health.error_count == 1
        assert health.last_error is not None

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, connector):
        """Test health check when connector is disconnected."""
        health = await connector.health_check()

        assert health.status == ConnectorStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_health_check_with_token_refresh(self, connector, token_manager):
        """Test health check with token refresh."""
        connector.token_manager = token_manager

        # Mock expired token
        expired_token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        token_manager.get_token.return_value = expired_token

        await connector.start()
        health = await connector.health_check()

        # Should attempt to authenticate due to expired token
        assert connector.authenticate_called
        assert health.status in [
            ConnectorStatus.HEALTHY, ConnectorStatus.AUTHENTICATING]

    @pytest.mark.asyncio
    async def test_make_request_success(self, connector):
        """Test successful HTTP request."""
        await connector.start()

        # Mock the session's request method directly
        mock_response = AsyncMock()
        mock_response.status = 200
        connector._session.request = AsyncMock(return_value=mock_response)

        response = await connector._make_request('GET', 'https://api.example.com/test')

        assert response is mock_response
        connector._session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_token(self, connector, token_manager):
        """Test HTTP request with authentication token."""
        connector.token_manager = token_manager

        token = TokenInfo(access_token="test_token", token_type="Bearer")
        token_manager.get_token.return_value = token

        await connector.start()

        # Mock the session's request method directly
        mock_response = AsyncMock()
        connector._session.request = AsyncMock(return_value=mock_response)

        await connector._make_request('GET', 'https://api.example.com/test')

        # Check that Authorization header was added
        call_args = connector._session.request.call_args
        headers = call_args[1].get('headers', {})
        assert headers.get('Authorization') == 'Bearer test_token'

    @pytest.mark.asyncio
    async def test_make_request_rate_limited(self, connector, rate_limiter):
        """Test HTTP request with rate limiting."""
        connector.rate_limiter = rate_limiter
        await connector.start()

        # Mock the session's request method directly
        mock_response = AsyncMock()
        connector._session.request = AsyncMock(return_value=mock_response)

        # Mock rate limiter acquire
        with patch.object(rate_limiter, 'acquire') as mock_acquire:
            await connector._make_request('GET', 'https://api.example.com/test')
            mock_acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_circuit_breaker_open(self, connector, circuit_breaker):
        """Test HTTP request with open circuit breaker."""
        connector.circuit_breaker = circuit_breaker
        await connector.start()

        # Mock circuit breaker as open
        with patch.object(circuit_breaker, 'can_execute', return_value=False):
            with pytest.raises(CircuitBreakerError):
                await connector._make_request('GET', 'https://api.example.com/test')

    @pytest.mark.asyncio
    async def test_make_request_rate_limit_error(self, connector):
        """Test HTTP request with rate limit error."""
        await connector.start()

        with patch('aiohttp.ClientSession.request') as mock_request:
            from aiohttp import ClientResponseError
            error = ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=429,
                headers={'Retry-After': '60'}
            )
            mock_request.side_effect = error

            with pytest.raises(RateLimitError) as exc_info:
                await connector._make_request('GET', 'https://api.example.com/test')

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_make_request_not_started(self, connector):
        """Test HTTP request when connector not started."""
        with pytest.raises(RuntimeError, match="Connector not started"):
            await connector._make_request('GET', 'https://api.example.com/test')


class TestRawMessage:
    """Test RawMessage data class."""

    def test_raw_message_creation(self):
        """Test RawMessage creation."""
        message = RawMessage(
            id="msg_123",
            platform="test_platform",
            platform_message_id="platform_123",
            thread_id="thread_456",
            sender_id="user_789",
            content={"text": "Hello world"},
            timestamp=datetime.now(timezone.utc),
            metadata={"priority": "high"},
            raw_data={"original": "data"}
        )

        assert message.id == "msg_123"
        assert message.platform == "test_platform"
        assert message.content["text"] == "Hello world"
        assert message.metadata["priority"] == "high"
        assert message.raw_data["original"] == "data"


class TestConnectorHealth:
    """Test ConnectorHealth data class."""

    def test_connector_health_creation(self):
        """Test ConnectorHealth creation."""
        health = ConnectorHealth(
            status=ConnectorStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            error_count=0,
            uptime_seconds=3600.0,
            metadata={"version": "1.0"}
        )

        assert health.status == ConnectorStatus.HEALTHY
        assert health.error_count == 0
        assert health.uptime_seconds == 3600.0
        assert health.metadata["version"] == "1.0"

    def test_connector_health_defaults(self):
        """Test ConnectorHealth with default values."""
        health = ConnectorHealth(
            status=ConnectorStatus.HEALTHY,
            last_check=datetime.now(timezone.utc)
        )

        assert health.error_count == 0
        assert health.last_error is None
        assert health.uptime_seconds == 0.0
        assert health.metadata == {}


if __name__ == "__main__":
    pytest.main([__file__])
