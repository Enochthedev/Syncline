"""
Tests for experimental platform connectors.

This module provides comprehensive testing for experimental connectors including
TikTok, Snapchat, and the experimental framework itself.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from integrations.experimental.framework import ExperimentalFramework
from integrations.experimental.tiktok_connector import TikTokConnector
from integrations.experimental.snapchat_connector import SnapchatConnector
from integrations.experimental.base_experimental import (
    ExperimentalConnector,
    ExperimentalStatus,
    UnsupportedFeatureError,
    APILimitationError
)


@pytest.fixture
def mock_config():
    """Provide mock configuration for testing."""
    return {
        "experimental": {
            "mock_mode": True,
            "debug_mode": True,
            "api_timeout": 5,
            "max_retries": 2
        },
        "app_id": "test_app_id",
        "app_secret": "test_app_secret",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "redirect_uri": "https://example.com/callback"
    }


@pytest.fixture
async def experimental_framework():
    """Provide experimental framework instance."""
    framework = ExperimentalFramework()
    yield framework
    await framework.cleanup()


class TestExperimentalFramework:
    """Test the experimental connector framework."""

    @pytest.mark.asyncio
    async def test_framework_initialization(self, experimental_framework):
        """Test framework initialization."""
        framework = experimental_framework

        # Check that built-in connectors are registered
        connectors = framework.get_available_connectors()
        assert "tiktok" in connectors
        assert "snapchat" in connectors

        # Check connector registry information
        tiktok_info = framework.get_connector_info("tiktok")
        assert tiktok_info is not None
        assert tiktok_info.name == "tiktok"
        assert tiktok_info.status == ExperimentalStatus.PROOF_OF_CONCEPT

    @pytest.mark.asyncio
    async def test_connector_creation(self, experimental_framework, mock_config):
        """Test creating connector instances."""
        framework = experimental_framework

        # Create TikTok connector
        tiktok_connector = await framework.create_connector("tiktok", mock_config)
        assert isinstance(tiktok_connector, TikTokConnector)
        assert tiktok_connector.platform == "tiktok"
        assert tiktok_connector.mock_mode is True

        # Create Snapchat connector
        snapchat_connector = await framework.create_connector("snapchat", mock_config)
        assert isinstance(snapchat_connector, SnapchatConnector)
        assert snapchat_connector.platform == "snapchat"

    @pytest.mark.asyncio
    async def test_unknown_connector(self, experimental_framework, mock_config):
        """Test handling of unknown connector platforms."""
        framework = experimental_framework

        with pytest.raises(Exception):  # Should raise ExperimentalError
            await framework.create_connector("unknown_platform", mock_config)

    @pytest.mark.asyncio
    async def test_connector_testing(self, experimental_framework, mock_config):
        """Test connector testing functionality."""
        framework = experimental_framework

        # Test TikTok connector
        tiktok_result = await framework.test_connector("tiktok", mock_config)
        assert tiktok_result.platform == "tiktok"
        assert tiktok_result.tests_total > 0
        assert isinstance(tiktok_result.timestamp, datetime)

        # Test Snapchat connector
        snapchat_result = await framework.test_connector("snapchat", mock_config)
        assert snapchat_result.platform == "snapchat"
        assert snapchat_result.tests_total > 0

    @pytest.mark.asyncio
    async def test_all_connectors_testing(self, experimental_framework, mock_config):
        """Test testing all connectors at once."""
        framework = experimental_framework

        results = await framework.test_all_connectors(mock_config)
        assert "tiktok" in results
        assert "snapchat" in results

        for platform, result in results.items():
            assert result.platform == platform
            assert result.tests_total > 0

    @pytest.mark.asyncio
    async def test_documentation_generation(self, experimental_framework):
        """Test documentation generation."""
        framework = experimental_framework

        doc = await framework.generate_documentation()
        assert "title" in doc
        assert "connectors" in doc
        assert "tiktok" in doc["connectors"]
        assert "snapchat" in doc["connectors"]

        # Check TikTok documentation
        tiktok_doc = doc["connectors"]["tiktok"]
        assert "capabilities" in tiktok_doc
        assert "limitations" in tiktok_doc
        assert "requirements" in tiktok_doc

    def test_framework_statistics(self, experimental_framework):
        """Test framework statistics."""
        framework = experimental_framework

        stats = framework.get_framework_statistics()
        assert "registered_connectors" in stats
        assert "platforms" in stats
        assert "statuses" in stats
        # At least TikTok and Snapchat
        assert stats["registered_connectors"] >= 2


class TestTikTokConnector:
    """Test TikTok experimental connector."""

    @pytest.fixture
    async def tiktok_connector(self, mock_config):
        """Provide TikTok connector instance."""
        connector = TikTokConnector(mock_config)
        yield connector
        if connector.is_running:
            await connector.stop()

    @pytest.mark.asyncio
    async def test_tiktok_initialization(self, tiktok_connector):
        """Test TikTok connector initialization."""
        connector = tiktok_connector

        assert connector.platform == "tiktok"
        assert connector.mock_mode is True
        assert connector.capabilities.mock_mode is True
        assert connector.capabilities.real_time_ingestion is False
        assert len(connector.limitations) > 0

    @pytest.mark.asyncio
    async def test_tiktok_capabilities(self, tiktok_connector):
        """Test TikTok connector capabilities."""
        connector = tiktok_connector

        capabilities = connector.capabilities
        assert capabilities.media_support is True
        assert capabilities.rate_limiting is True
        assert capabilities.test_data_generation is True
        assert capabilities.authentication is False  # Not available

    @pytest.mark.asyncio
    async def test_tiktok_mock_authentication(self, tiktok_connector):
        """Test TikTok mock authentication."""
        connector = tiktok_connector

        # Mock authentication should work
        await connector._authenticate_mock()

        # Real authentication should fail
        with pytest.raises(APILimitationError):
            await connector._authenticate_real()

    @pytest.mark.asyncio
    async def test_tiktok_mock_data_generation(self, tiktok_connector):
        """Test TikTok mock data generation."""
        connector = tiktok_connector

        messages = await connector._generate_mock_messages()
        assert len(messages) > 0

        # Check message structure
        for message in messages:
            assert message.platform == "tiktok"
            assert message.id is not None
            assert message.content is not None
            assert message.metadata.get("mock") is True

    @pytest.mark.asyncio
    async def test_tiktok_unsupported_features(self, tiktok_connector):
        """Test TikTok unsupported features."""
        connector = tiktok_connector

        # Real-time ingestion should fail
        with pytest.raises(UnsupportedFeatureError):
            await connector._start_real_time_ingestion_real()

        # Historical fetch should fail
        with pytest.raises(UnsupportedFeatureError):
            await connector._fetch_historical_messages_real()

        # Webhook handling should fail
        with pytest.raises(UnsupportedFeatureError):
            await connector._handle_webhook_real({})

    @pytest.mark.asyncio
    async def test_tiktok_platform_info(self, tiktok_connector):
        """Test TikTok platform information."""
        connector = tiktok_connector

        info = await connector.get_platform_info()
        assert info["platform"] == "tiktok"
        assert "supported_features" in info
        assert "unsupported_features" in info
        assert "requirements" in info

    @pytest.mark.asyncio
    async def test_tiktok_connection_test(self, tiktok_connector):
        """Test TikTok connection testing."""
        connector = tiktok_connector

        test_results = await connector.test_connection()
        assert test_results["platform"] == "tiktok"
        assert "tests" in test_results

        # Check specific tests
        tests = test_results["tests"]
        assert "mock_auth" in tests
        assert "mock_data" in tests
        assert "real_api" in tests


class TestSnapchatConnector:
    """Test Snapchat experimental connector."""

    @pytest.fixture
    async def snapchat_connector(self, mock_config):
        """Provide Snapchat connector instance."""
        config = mock_config.copy()
        config["snap_kit_enabled"] = True
        connector = SnapchatConnector(config)
        yield connector
        if connector.is_running:
            await connector.stop()

    @pytest.mark.asyncio
    async def test_snapchat_initialization(self, snapchat_connector):
        """Test Snapchat connector initialization."""
        connector = snapchat_connector

        assert connector.platform == "snapchat"
        assert connector.mock_mode is True
        assert connector.snap_kit_enabled is True
        assert len(connector.limitations) > 0

    @pytest.mark.asyncio
    async def test_snapchat_capabilities(self, snapchat_connector):
        """Test Snapchat connector capabilities."""
        connector = snapchat_connector

        capabilities = connector.capabilities
        assert capabilities.authentication is True  # OAuth available
        assert capabilities.media_support is True
        assert capabilities.real_time_ingestion is False
        assert capabilities.webhook_support is False

    @pytest.mark.asyncio
    async def test_snapchat_mock_data_generation(self, snapchat_connector):
        """Test Snapchat mock data generation."""
        connector = snapchat_connector

        messages = await connector._generate_mock_messages()
        assert len(messages) > 0

        # Check for Snapchat-specific content types
        content_types = set()
        for message in messages:
            content_type = message.metadata.get("content_type")
            content_types.add(content_type)

        expected_types = {"snap", "chat", "story", "memory", "bitmoji"}
        assert content_types.intersection(expected_types)

    @pytest.mark.asyncio
    async def test_snapchat_ephemeral_content(self, snapchat_connector):
        """Test Snapchat ephemeral content simulation."""
        connector = snapchat_connector

        messages = await connector._generate_mock_messages()

        # Check for ephemeral content
        ephemeral_count = 0
        for message in messages:
            if message.metadata.get("privacy", {}).get("ephemeral"):
                ephemeral_count += 1

        assert ephemeral_count > 0  # Should have some ephemeral content

    @pytest.mark.asyncio
    async def test_snapchat_snap_interaction(self, snapchat_connector):
        """Test Snapchat snap interaction simulation."""
        connector = snapchat_connector

        # Test different interaction types
        interactions = ["view", "screenshot", "replay", "save"]

        for action in interactions:
            result = await connector.simulate_snap_interaction("test_snap_123", action)
            assert result["snap_id"] == "test_snap_123"
            assert result["action"] == action
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_snapchat_invalid_interaction(self, snapchat_connector):
        """Test invalid Snapchat interaction."""
        connector = snapchat_connector

        with pytest.raises(ValueError):
            await connector.simulate_snap_interaction("test_snap", "invalid_action")

    @pytest.mark.asyncio
    async def test_snapchat_platform_info(self, snapchat_connector):
        """Test Snapchat platform information."""
        connector = snapchat_connector

        info = await connector.get_platform_info()
        assert info["platform"] == "snapchat"
        assert "unique_features" in info
        assert "ephemeral content" in str(info).lower()


class TestExperimentalConnectorBase:
    """Test base experimental connector functionality."""

    @pytest.fixture
    async def base_connector(self, mock_config):
        """Provide a concrete experimental connector for testing."""
        connector = TikTokConnector(mock_config)
        yield connector
        if connector.is_running:
            await connector.stop()

    @pytest.mark.asyncio
    async def test_health_check(self, base_connector):
        """Test experimental connector health check."""
        connector = base_connector

        health = await connector.health_check()
        assert health is not None
        assert hasattr(health, 'experimental_status')
        assert hasattr(health, 'capabilities')
        assert hasattr(health, 'limitations')

    @pytest.mark.asyncio
    async def test_debug_logging(self, base_connector):
        """Test debug logging functionality."""
        connector = base_connector

        # Clear existing logs
        connector.clear_debug_logs()

        # Log some debug information
        connector._log_debug("Test message", {"key": "value"})

        # Check logs
        logs = connector.get_debug_logs()
        assert len(logs) == 1
        assert logs[0]["message"] == "Test message"
        assert logs[0]["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_statistics_collection(self, base_connector):
        """Test statistics collection."""
        connector = base_connector

        stats = connector.get_statistics()
        assert "platform" in stats
        assert "experimental_status" in stats
        assert "mock_mode" in stats
        assert "capabilities" in stats

    @pytest.mark.asyncio
    async def test_mock_mode_fallback(self, base_connector):
        """Test mock mode fallback behavior."""
        connector = base_connector

        # Authentication should fall back to mock
        await connector.authenticate()

        # Historical fetch should return mock data
        messages = await connector.fetch_historical_messages()
        assert len(messages) > 0
        assert all(msg.metadata.get("mock") for msg in messages)


@pytest.mark.asyncio
async def test_integration_with_framework():
    """Test integration between connectors and framework."""
    framework = ExperimentalFramework()

    try:
        # Test creating and testing connectors through framework
        config = {
            "experimental": {
                "mock_mode": True,
                "debug_mode": True
            }
        }

        # Test TikTok through framework
        tiktok_connector = await framework.create_connector("tiktok", config)
        tiktok_result = await framework.test_connector("tiktok", config)

        assert tiktok_result.platform == "tiktok"
        assert tiktok_result.tests_total > 0

        # Test Snapchat through framework
        snapchat_connector = await framework.create_connector("snapchat", config)
        snapchat_result = await framework.test_connector("snapchat", config)

        assert snapchat_result.platform == "snapchat"
        assert snapchat_result.tests_total > 0

    finally:
        await framework.cleanup()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
