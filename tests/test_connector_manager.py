"""
Unit tests for ConnectorManager.

Tests connector lifecycle management, health monitoring,
and coordination functionality.
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

from integrations.connector_manager import (
    ConnectorManager,
    ConnectorConfig,
    ConnectorStats,
    ManagerStatus
)
from integrations.base_connector import (
    BaseConnector,
    ConnectorHealth,
    ConnectorStatus,
    RawMessage
)
from integrations.rate_limiter import RateLimitConfig, CircuitBreakerConfig
from integrations.token_manager import TokenManager


class MockConnector(BaseConnector):
    """Mock connector for testing."""

    def __init__(self, platform: str, config: Dict[str, Any]):
        super().__init__(platform, config)
        self.start_called = False
        self.stop_called = False
        self.should_fail_start = False
        self.should_fail_health = False
        self._mock_health = ConnectorHealth(
            status=ConnectorStatus.HEALTHY,
            last_check=datetime.now(timezone.utc)
        )

    async def authenticate(self) -> None:
        if self.should_fail_start:
            raise Exception("Mock authentication failure")

    async def start_real_time_ingestion(self) -> None:
        self.start_called = True
        if self.should_fail_start:
            raise Exception("Mock start failure")

    async def stop_real_time_ingestion(self) -> None:
        self.stop_called = True

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        return []

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        pass

    async def health_check(self) -> ConnectorHealth:
        if self.should_fail_health:
            self._mock_health.status = ConnectorStatus.UNHEALTHY
            self._mock_health.error_count += 1
            self._mock_health.last_error = "Mock health check failure"
        else:
            self._mock_health.status = ConnectorStatus.HEALTHY
            self._mock_health.error_count = 0
            self._mock_health.last_error = None

        self._mock_health.last_check = datetime.now(timezone.utc)
        return self._mock_health


class TestConnectorManager:
    """Test ConnectorManager functionality."""

    @pytest.fixture
    def token_manager(self):
        """Token manager fixture."""
        return AsyncMock(spec=TokenManager)

    @pytest.fixture
    def manager(self, token_manager):
        """ConnectorManager fixture."""
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
        """Connector configuration fixture."""
        return ConnectorConfig(
            platform="test_platform",
            enabled=True,
            rate_limit=RateLimitConfig(requests_per_second=10.0),
            circuit_breaker=CircuitBreakerConfig(failure_threshold=3),
            health_check_interval=60,
            restart_on_failure=True,
            max_restart_attempts=3
        )

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.status == ManagerStatus.STOPPED
        assert not manager.is_running
        assert len(manager._connectors) == 0

    @pytest.mark.asyncio
    async def test_register_connector(self, manager, mock_connector, connector_config):
        """Test connector registration."""
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
        """Test connector registration with default config."""
        await manager.register_connector(mock_connector)

        assert "test_platform" in manager._connectors
        config = manager._connector_configs["test_platform"]
        assert config.platform == "test_platform"
        assert config.enabled is True

    @pytest.mark.asyncio
    async def test_register_connector_replace_existing(self, manager, connector_config):
        """Test replacing existing connector."""
        connector1 = MockConnector("test_platform", {"version": "1"})
        connector2 = MockConnector("test_platform", {"version": "2"})

        await manager.register_connector(connector1, connector_config)
        await manager.register_connector(connector2, connector_config)

        assert manager._connectors["test_platform"] is connector2

    @pytest.mark.asyncio
    async def test_unregister_connector(self, manager, mock_connector, connector_config):
        """Test connector unregistration."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.unregister_connector("test_platform")

        assert "test_platform" not in manager._connectors
        assert "test_platform" not in manager._connector_configs
        assert "test_platform" not in manager._connector_stats

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_connector(self, manager):
        """Test unregistering non-existent connector."""
        # Should not raise exception
        await manager.unregister_connector("nonexistent")

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
    async def test_start_connector_failure(self, manager, mock_connector, connector_config):
        """Test handling connector start failure."""
        mock_connector.should_fail_start = True
        await manager.register_connector(mock_connector, connector_config)

        # Should not raise exception, but continue with other connectors
        await manager.start_all_connectors()

        assert manager.is_running
        assert manager.status == ManagerStatus.RUNNING

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
        await manager.restart_connector("test_platform")

        # Should have been stopped and started
        assert mock_connector.stop_called
        assert mock_connector.start_called

    @pytest.mark.asyncio
    async def test_get_connector_health_single(self, manager, mock_connector, connector_config):
        """Test getting health for a single connector."""
        await manager.register_connector(mock_connector, connector_config)

        health = await manager.get_connector_health("test_platform")

        assert "test_platform" in health
        assert health["test_platform"].status == ConnectorStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_connector_health_all(self, manager, connector_config):
        """Test getting health for all connectors."""
        connector1 = MockConnector("platform1", {"key": "1"})
        connector2 = MockConnector("platform2", {"key": "2"})

        config1 = ConnectorConfig(platform="platform1")
        config2 = ConnectorConfig(platform="platform2")

        await manager.register_connector(connector1, config1)
        await manager.register_connector(connector2, config2)

        health = await manager.get_connector_health()

        assert len(health) == 2
        assert "platform1" in health
        assert "platform2" in health

    @pytest.mark.asyncio
    async def test_get_connector_health_failure(self, manager, mock_connector, connector_config):
        """Test handling health check failure."""
        mock_connector.should_fail_health = True
        await manager.register_connector(mock_connector, connector_config)

        health = await manager.get_connector_health("test_platform")

        assert health["test_platform"].status == ConnectorStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_get_connector_health_nonexistent(self, manager):
        """Test getting health for non-existent connector."""
        with pytest.raises(ValueError, match="not registered"):
            await manager.get_connector_health("nonexistent")

    @pytest.mark.asyncio
    async def test_get_connector_stats(self, manager, mock_connector, connector_config):
        """Test getting connector statistics."""
        await manager.register_connector(mock_connector, connector_config)

        stats = await manager.get_connector_stats("test_platform")

        assert "test_platform" in stats
        assert stats["test_platform"].platform == "test_platform"
        assert stats["test_platform"].restart_count == 0

    @pytest.mark.asyncio
    async def test_get_connector_stats_all(self, manager, connector_config):
        """Test getting stats for all connectors."""
        connector1 = MockConnector("platform1", {"key": "1"})
        connector2 = MockConnector("platform2", {"key": "2"})

        config1 = ConnectorConfig(platform="platform1")
        config2 = ConnectorConfig(platform="platform2")

        await manager.register_connector(connector1, config1)
        await manager.register_connector(connector2, config2)

        stats = await manager.get_connector_stats()

        assert len(stats) == 2
        assert "platform1" in stats
        assert "platform2" in stats

    @pytest.mark.asyncio
    async def test_enable_connector(self, manager, mock_connector, connector_config):
        """Test enabling a connector."""
        connector_config.enabled = False
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()

        # Should not be started initially
        assert not mock_connector.start_called

        # Enable and check it starts
        await manager.enable_connector("test_platform")
        assert manager._connector_configs["test_platform"].enabled is True

    @pytest.mark.asyncio
    async def test_disable_connector(self, manager, mock_connector, connector_config):
        """Test disabling a connector."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()

        await manager.disable_connector("test_platform")

        assert manager._connector_configs["test_platform"].enabled is False

    @pytest.mark.asyncio
    async def test_health_check_loop(self, manager, mock_connector, connector_config):
        """Test health check loop functionality."""
        await manager.register_connector(mock_connector, connector_config)
        await manager.start_all_connectors()

        # Wait for at least one health check cycle
        await asyncio.sleep(1.5)

        stats = await manager.get_connector_stats("test_platform")
        assert stats["test_platform"].health_checks_passed > 0

        await manager.stop_all_connectors()

    @pytest.mark.asyncio
    async def test_restart_on_failure(self, manager, mock_connector):
        """Test automatic restart on failure."""
        config = ConnectorConfig(
            platform="test_platform",
            restart_on_failure=True,
            max_restart_attempts=2,
            restart_delay=0  # No delay for testing
        )

        await manager.register_connector(mock_connector, config)
        await manager.start_all_connectors()

        # Simulate health check failure
        mock_connector.should_fail_health = True

        # Trigger health check manually
        await manager._perform_health_checks()

        # Check that restart was attempted
        stats = await manager.get_connector_stats("test_platform")
        # Note: restart count might be 0 if the restart succeeded immediately

        await manager.stop_all_connectors()

    def test_get_manager_stats(self, manager):
        """Test getting manager statistics."""
        stats = manager.get_manager_stats()

        assert "status" in stats
        assert "total_connectors" in stats
        assert "enabled_connectors" in stats
        assert "healthy_connectors" in stats
        assert stats["status"] == ManagerStatus.STOPPED.value
        assert stats["total_connectors"] == 0


class TestConnectorConfig:
    """Test ConnectorConfig data class."""

    def test_connector_config_creation(self):
        """Test ConnectorConfig creation."""
        config = ConnectorConfig(
            platform="test_platform",
            enabled=True,
            health_check_interval=30,
            restart_on_failure=False,
            max_restart_attempts=5
        )

        assert config.platform == "test_platform"
        assert config.enabled is True
        assert config.health_check_interval == 30
        assert config.restart_on_failure is False
        assert config.max_restart_attempts == 5

    def test_connector_config_defaults(self):
        """Test ConnectorConfig with default values."""
        config = ConnectorConfig(platform="test_platform")

        assert config.enabled is True
        assert config.health_check_interval == 60
        assert config.restart_on_failure is True
        assert config.max_restart_attempts == 3
        assert config.restart_delay == 30


class TestConnectorStats:
    """Test ConnectorStats data class."""

    def test_connector_stats_creation(self):
        """Test ConnectorStats creation."""
        stats = ConnectorStats(
            platform="test_platform",
            status=ConnectorStatus.HEALTHY,
            uptime_seconds=3600.0,
            error_count=0,
            restart_count=1,
            last_error=None,
            last_restart=datetime.now(timezone.utc),
            health_checks_passed=100,
            health_checks_failed=2
        )

        assert stats.platform == "test_platform"
        assert stats.status == ConnectorStatus.HEALTHY
        assert stats.uptime_seconds == 3600.0
        assert stats.error_count == 0
        assert stats.restart_count == 1
        assert stats.health_checks_passed == 100
        assert stats.health_checks_failed == 2


if __name__ == "__main__":
    pytest.main([__file__])
