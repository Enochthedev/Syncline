"""
Unit tests for connector manager.

Tests ConnectorManager lifecycle management, health monitoring,
and connector coordination functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.base_connector import BaseConnector, ConnectorHealth, ConnectorStatus
from integrations.connector_manager import (
    ConnectorManager,
    ConnectorConfig,
    ConnectorStats,
    ManagerStatus
)
from integrations.rate_limiter import RateLimitConfig, CircuitBreakerConfig
from integrations.token_manager import TokenManager


class MockConnector(BaseConnector):
    """Mock connector for testing."""

    def __init__(self, platform: str, config: dict):
        super().__init__(platform, config)
        self.start_called = False
        self.stop_called = False
        self.authenticate_called = False
        self.should_fail_start = False
        self.should_fail_health = False

    async def authenticate(self) -> None:
        self.authenticate_called = True

    async def start_real_time_ingestion(self) -> None:
        if self.should_fail_start:
            raise Exception("Mock start failure")

    async def stop_real_time_ingestion(self) -> None:
        pass

    async def fetch_historical_messages(self, cursor=None, limit=100):
        return []

    async def handle_webhook(self, payload):
        pass

    async def start(self) -> None:
        self.start_called = True
        await super().start()

    async def stop(self) -> None:
        self.stop_called = True
        await super().stop()

    async def _platform_health_check(self) -> None:
        if self.should_fail_health:
            raise Exception("Mock health check failure")


class TestConnectorConfig:
    """Test ConnectorConfig data class."""

    def test_default_config(self):
        """Test default connector configuration."""
        config = ConnectorConfig(platform="test_platform")

        assert config.platform == "test_platform"
        assert config.enabled is True
        assert config.rate_limit is None
        assert config.circuit_breaker is None
        assert config.health_check_interval == 60
        assert config.restart_on_failure is True
        assert config.max_restart_attempts == 3
        assert config.restart_delay == 30
        assert config.config == {}

    def test_custom_config(self):
        """Test custom connector configuration."""
        rate_limit = RateLimitConfig(requests_per_second=5.0)
        circuit_breaker = CircuitBreakerConfig(failure_threshold=2)

        config = ConnectorConfig(
            platform="test_platform",
            enabled=False,
            rate_limit=rate_limit,
            circuit_breaker=circuit_breaker,
            health_check_interval=30,
            restart_on_failure=False,
            max_restart_attempts=5,
            restart_delay=60,
            config={"api_key": "test"}
        )

        assert config.platform == "test_platform"
        assert config.enabled is False
        assert config.rate_limit is rate_limit
        assert config.circuit_breaker is circuit_breaker
        assert config.health_check_interval == 30
        assert config.restart_on_failure is False
        assert config.max_restart_attempts == 5
        assert config.restart_delay == 60
        assert config.config["api_key"] == "test"


class TestConnectorStats:
    """Test ConnectorStats data class."""

    def test_stats_creation(self):
        """Test connector stats creation."""
        stats = ConnectorStats(
            platform="test_platform",
            status=ConnectorStatus.HEALTHY,
            uptime_seconds=3600.0,
            error_count=2,
            restart_count=1,
            last_error="Test error",
            last_restart=datetime.utcnow(),
            health_checks_passed=10,
            health_checks_failed=2
        )

        assert stats.platform == "test_platform"
        assert stats.status == ConnectorStatus.HEALTHY
        assert stats.uptime_seconds == 3600.0
        assert stats.error_count == 2
        assert stats.restart_count == 1
        assert stats.last_error == "Test error"
        assert stats.health_checks_passed == 10
        assert stats.health_checks_failed == 2


class TestConnectorManager:
    """Test ConnectorManager functionality."""

    @pytest.fixture
    def token_manager(self):
        """Token manager fixture."""
        return AsyncMock(spec=TokenManager)

    @pytest.fixture
    def manager(self, token_manager):
        """Connector manager fixture."""
        return ConnectorManager(
            token_manager=token_manager,
            health_check_interval=1  # Short interval for testing
        )

    @pytest.fixture
    def mock_connector(self):
        """Mock connector fixture."""
        return MockConnector("test_platform", {"api_key": "test"})

    @pytest.fixture
    def connector_config(self):
        """Connector config fixture."""
        return ConnectorConfig(
            platform="test_platform",
            rate_limit=RateLimitConfig(),
            circuit_breaker=CircuitBreakerConfig()
        )

    def test_manager_initialization(self, manager, token_manager):
        """Test manager initialization."""
        assert manager.token_manager is token_manager
        assert manager.health_check_interval == 1
        assert manager.status == ManagerStatus.STOPPED
        assert not manager.is_running

    @pytest.mark.asyncio
    async def test_register_connector(self, manager, mock_connector, connector_config):
        """Test registering a connector."""
        await manager.register_connector(mock_connector, connector_config)

        assert "test_platform" in manager._connectors
        assert manager._connectors["test_platform"] is mock_connector
        assert "test_platform" in manager._connector_configs
        assert "test_platform" in manager._connector_stats

        # Check that utilities were set
        assert mock_connector.rate_limiter is not None
        assert mock_connector.circuit_breaker is not None
        assert mock_connector.token_manager is manager.token_manager

    @pytest.mark.asyncio
    async def test_register_connector_default_config(self, manager, mock_connector):
        """Test registering connector with default config."""
        await manager.register_connector(mock_connector)

        assert "test_platform" in manager._connector_configs
        config = manager._connector_configs["test_platform"]
        assert config.platform == "test_platform"
        assert config.enabled is True

    @pytest.mark.asyncio
    async def test_unregister_connector(self, manager, mock_connector, connector_config):
        """Test unregistering a connector."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.unregister_connector("test_platform")

        assert "test_platform" not in manager._connectors
        assert "test_platform" not in manager._connector_configs
        assert "test_platform" not in manager._connector_stats

    @pytest.mark.asyncio
    async def test_start_all_connectors(self, manager, mock_connector, connector_config):
        """Test starting all connectors."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()

        assert manager.is_running
        assert manager.status == ManagerStatus.RUNNING
        assert mock_connector.start_called
        assert manager._health_check_task is not None

    @pytest.mark.asyncio
    async def test_start_disabled_connector(self, manager, mock_connector):
        """Test that disabled connectors are not started."""
        config = ConnectorConfig(platform="test_platform", enabled=False)
        await manager.register_connector(mock_connector, config)
        await manager.start_all_connectors()

        assert manager.is_running
        assert not mock_connector.start_called

    @pytest.mark.asyncio
    async def test_stop_all_connectors(self, manager, mock_connector, connector_config):
        """Test stopping all connectors."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()
        await manager.stop_all_connectors()

        assert not manager.is_running
        assert manager.status == ManagerStatus.STOPPED
        assert mock_connector.stop_called
        assert manager._health_check_task is None

    @pytest.mark.asyncio
    async def test_start_specific_connector(self, manager, mock_connector, connector_config):
        """Test starting a specific connector."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_connector("test_platform")

        assert mock_connector.start_called

    @pytest.mark.asyncio
    async def test_stop_specific_connector(self, manager, mock_connector, connector_config):
        """Test stopping a specific connector."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_connector("test_platform")
        await manager.stop_connector("test_platform")

        assert mock_connector.stop_called

    @pytest.mark.asyncio
    async def test_restart_connector(self, manager, mock_connector, connector_config):
        """Test restarting a connector."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_connector("test_platform")

        # Reset flags
        mock_connector.start_called = False
        mock_connector.stop_called = False

        await manager.restart_connector("test_platform")

        assert mock_connector.stop_called
        assert mock_connector.start_called

    @pytest.mark.asyncio
    async def test_get_connector_health_single(self, manager, mock_connector, connector_config):
        """Test getting health for a single connector."""
        await manager.register_connector(mock_connector, connector_config)

        health_status = await manager.get_connector_health("test_platform")

        assert "test_platform" in health_status
        assert isinstance(health_status["test_platform"], ConnectorHealth)

    @pytest.mark.asyncio
    async def test_get_connector_health_all(self, manager, connector_config):
        """Test getting health for all connectors."""
        # Register multiple connectors
        connectors = [
            MockConnector("platform1", {}),
            MockConnector("platform2", {}),
            MockConnector("platform3", {})
        ]

        for connector in connectors:
            config = ConnectorConfig(platform=connector.platform)
            await manager.register_connector(connector, config)

        health_status = await manager.get_connector_health()

        assert len(health_status) == 3
        assert "platform1" in health_status
        assert "platform2" in health_status
        assert "platform3" in health_status

    @pytest.mark.asyncio
    async def test_get_connector_stats(self, manager, mock_connector, connector_config):
        """Test getting connector statistics."""
        await manager.register_connector(mock_connector, connector_config)

        stats = await manager.get_connector_stats("test_platform")

        assert "test_platform" in stats
        assert isinstance(stats["test_platform"], ConnectorStats)

    @pytest.mark.asyncio
    async def test_enable_disable_connector(self, manager, mock_connector, connector_config):
        """Test enabling and disabling connectors."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()

        # Disable connector
        await manager.disable_connector("test_platform")
        assert not manager._connector_configs["test_platform"].enabled
        assert mock_connector.stop_called

        # Reset and enable
        mock_connector.start_called = False
        await manager.enable_connector("test_platform")
        assert manager._connector_configs["test_platform"].enabled
        assert mock_connector.start_called

    @pytest.mark.asyncio
    async def test_health_check_loop(self, manager, mock_connector, connector_config):
        """Test health check loop functionality."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()

        # Wait for at least one health check cycle
        await asyncio.sleep(1.5)

        stats = manager._connector_stats["test_platform"]
        assert stats.health_checks_passed > 0

    @pytest.mark.asyncio
    async def test_health_check_failure_restart(self, manager, mock_connector):
        """Test automatic restart on health check failure."""
        config = ConnectorConfig(
            platform="test_platform",
            restart_on_failure=True,
            health_check_interval=1
        )
        await manager.register_connector(mock_connector, config)
        await manager.start_all_connectors()

        # Cause health check to fail
        mock_connector.should_fail_health = True

        # Wait for health check and restart
        await asyncio.sleep(2)

        stats = manager._connector_stats["test_platform"]
        assert stats.health_checks_failed > 0

    @pytest.mark.asyncio
    async def test_restart_limits(self, manager, mock_connector):
        """Test restart attempt limits."""
        config = ConnectorConfig(
            platform="test_platform",
            max_restart_attempts=2,
            restart_delay=0  # No delay for testing
        )
        await manager.register_connector(mock_connector, config)

        # Attempt multiple restarts
        for _ in range(5):
            await manager.restart_connector("test_platform")

        # Should be limited by max_restart_attempts
        assert manager._restart_counts["test_platform"] <= 2

    @pytest.mark.asyncio
    async def test_connector_start_failure(self, manager, mock_connector, connector_config):
        """Test handling connector start failure."""
        mock_connector.should_fail_start = True
        await manager.register_connector(mock_connector, connector_config)

        # Start should not raise exception, but connector should be unhealthy
        await manager.start_all_connectors()

        stats = manager._connector_stats["test_platform"]
        assert stats.status == ConnectorStatus.UNHEALTHY
        assert stats.error_count > 0

    def test_get_manager_stats(self, manager):
        """Test getting manager statistics."""
        stats = manager.get_manager_stats()

        assert "status" in stats
        assert "total_connectors" in stats
        assert "enabled_connectors" in stats
        assert "healthy_connectors" in stats
        assert "health_check_interval" in stats
        assert "uptime_seconds" in stats

        assert stats["status"] == "stopped"
        assert stats["total_connectors"] == 0

    @pytest.mark.asyncio
    async def test_manager_error_handling(self, manager, mock_connector):
        """Test manager error handling."""
        # Register connector that will fail
        mock_connector.should_fail_start = True
        await manager.register_connector(mock_connector)

        # Manager should handle the error gracefully
        await manager.start_all_connectors()

        # Manager should still be running despite connector failure
        assert manager.is_running
        assert manager.status == ManagerStatus.RUNNING

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, manager, mock_connector, connector_config):
        """Test concurrent manager operations."""
        await manager.register_connector(mock_connector, connector_config)

        # Perform concurrent operations
        tasks = [
            manager.start_connector("test_platform"),
            manager.get_connector_health("test_platform"),
            manager.get_connector_stats("test_platform")
        ]

        # Should not raise exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that no exceptions were raised
        for result in results:
            assert not isinstance(result, Exception)


if __name__ == "__main__":
    pytest.main([__file__])
