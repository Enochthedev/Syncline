"""
Integration tests for Telegram connector with real Telegram Bot API.

These tests require a valid Telegram bot token and should be run manually
or in a CI environment with proper credentials configured.
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone
from typing import Optional

from integrations.telegram_connector import TelegramConnector
from integrations.telegram_factory import TelegramConnectorFactory
from services.event_bus import EventBus


class TestTelegramIntegration:
    """Integration tests for Telegram connector."""

    @pytest.fixture
    def bot_token(self) -> Optional[str]:
        """Get bot token from environment."""
        return os.getenv('TELEGRAM_BOT_TOKEN')

    @pytest.fixture
    def telegram_config(self, bot_token):
        """Telegram configuration for integration tests."""
        if not bot_token:
            pytest.skip("TELEGRAM_BOT_TOKEN not set")

        return {
            'bot_token': bot_token,
            'webhook_url': None,  # Use polling for tests
            'max_messages_per_request': 10,
            'include_private_chats': True,
            'include_group_chats': False,
            'include_channels': False
        }

    @pytest.fixture
    async def telegram_connector(self, telegram_config):
        """Create Telegram connector for integration tests."""
        connector = TelegramConnector(config=telegram_config)
        yield connector

        # Cleanup
        if connector.is_running:
            await connector.stop()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_authentication(self, telegram_connector):
        """Test real Telegram authentication."""
        await telegram_connector.authenticate()

        assert telegram_connector.bot is not None
        assert telegram_connector.application is not None

        bot_info = telegram_connector.get_bot_info()
        assert bot_info is not None
        assert bot_info['is_bot'] is True
        assert 'username' in bot_info

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_health_check(self, telegram_connector):
        """Test Telegram health check."""
        await telegram_connector.authenticate()

        health = await telegram_connector.health_check()
        assert health.status.value in ['healthy', 'degraded']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_historical_messages(self, telegram_connector):
        """Test fetching historical messages."""
        await telegram_connector.authenticate()

        # Fetch recent messages
        messages = await telegram_connector.fetch_historical_messages(limit=5)

        # Should return a list (may be empty if no messages)
        assert isinstance(messages, list)

        # If there are messages, verify structure
        for message in messages:
            assert hasattr(message, 'id')
            assert hasattr(message, 'platform')
            assert hasattr(message, 'platform_message_id')
            assert hasattr(message, 'thread_id')
            assert hasattr(message, 'sender_id')
            assert hasattr(message, 'content')
            assert hasattr(message, 'timestamp')
            assert message.platform == 'telegram'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_connector_factory(self, telegram_config):
        """Test creating connector via factory."""
        connector = await TelegramConnectorFactory.create_connector(telegram_config)

        assert isinstance(connector, TelegramConnector)
        assert connector.platform == 'telegram'

        # Test authentication
        await connector.authenticate()
        bot_info = connector.get_bot_info()
        assert bot_info is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_start_stop_polling(self, telegram_connector):
        """Test starting and stopping polling mode."""
        await telegram_connector.authenticate()

        # Start real-time ingestion (polling mode)
        await telegram_connector.start_real_time_ingestion()

        assert telegram_connector.is_running
        assert telegram_connector._processor_task is not None
        assert telegram_connector._polling_task is not None

        # Let it run for a short time
        await asyncio.sleep(2)

        # Stop ingestion
        await telegram_connector.stop_real_time_ingestion()

        assert telegram_connector._processor_task is None
        assert telegram_connector._polling_task is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_webhook_setup(self, bot_token):
        """Test webhook setup (requires webhook URL)."""
        if not bot_token:
            pytest.skip("TELEGRAM_BOT_TOKEN not set")

        # Skip if no webhook URL configured
        webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL')
        if not webhook_url:
            pytest.skip("TELEGRAM_WEBHOOK_URL not set")

        config = {
            'bot_token': bot_token,
            'webhook_url': webhook_url,
            'webhook_secret': 'test_secret_123'
        }

        connector = TelegramConnector(config=config)

        try:
            await connector.authenticate()
            await connector.start_real_time_ingestion()

            assert connector._webhook_configured

        finally:
            await connector.stop_real_time_ingestion()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_send_message(self, telegram_connector):
        """Test sending a message (requires a test chat)."""
        test_chat_id = os.getenv('TELEGRAM_TEST_CHAT_ID')
        if not test_chat_id:
            pytest.skip("TELEGRAM_TEST_CHAT_ID not set")

        await telegram_connector.authenticate()

        message_id = await telegram_connector.send_message(
            chat_id=int(test_chat_id),
            text=f"Test message from integration test at {datetime.now(timezone.utc).isoformat()}"
        )

        assert message_id is not None
        assert isinstance(message_id, int)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_get_chat_member_count(self, telegram_connector):
        """Test getting chat member count."""
        test_chat_id = os.getenv('TELEGRAM_TEST_CHAT_ID')
        if not test_chat_id:
            pytest.skip("TELEGRAM_TEST_CHAT_ID not set")

        await telegram_connector.authenticate()

        count = await telegram_connector.get_chat_member_count(int(test_chat_id))

        # Should return a non-negative integer
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_error_handling(self, telegram_config):
        """Test error handling with invalid operations."""
        # Test with invalid bot token
        invalid_config = telegram_config.copy()
        invalid_config['bot_token'] = 'invalid_token'

        connector = TelegramConnector(config=invalid_config)

        with pytest.raises(Exception):  # Should raise authentication error
            await connector.authenticate()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_with_event_bus(self, telegram_config):
        """Test Telegram connector with event bus integration."""
        # Create a simple event bus mock that tracks published events
        class TestEventBus:
            def __init__(self):
                self.published_events = []

            async def publish(self, stream_name: str, event):
                self.published_events.append((stream_name, event))

        event_bus = TestEventBus()
        connector = TelegramConnector(
            config=telegram_config, event_bus=event_bus)

        await connector.authenticate()

        # Start polling for a short time to see if any messages come in
        await connector.start_real_time_ingestion()
        await asyncio.sleep(3)
        await connector.stop_real_time_ingestion()

        # Check if any events were published (may be empty if no messages)
        # This mainly tests that the integration doesn't crash
        assert isinstance(event_bus.published_events, list)


class TestTelegramConnectorFactory:
    """Integration tests for Telegram connector factory."""

    @pytest.mark.integration
    def test_validate_config_valid(self):
        """Test config validation with valid configuration."""
        config = {
            'bot_token': 'valid_token_format',
            'webhook_url': 'https://example.com/webhook',
            'webhook_secret': 'secret123',
            'max_messages_per_request': 50
        }

        validated = TelegramConnectorFactory.validate_config(config)

        assert validated['bot_token'] == 'valid_token_format'
        assert validated['webhook_url'] == 'https://example.com/webhook'
        assert validated['max_messages_per_request'] == 50

    @pytest.mark.integration
    def test_validate_config_missing_token(self):
        """Test config validation with missing bot token."""
        config = {'webhook_url': 'https://example.com'}

        with pytest.raises(ValueError, match="bot_token is required"):
            TelegramConnectorFactory.validate_config(config)

    @pytest.mark.integration
    def test_validate_config_invalid_webhook_url(self):
        """Test config validation with invalid webhook URL."""
        config = {
            'bot_token': 'valid_token',
            'webhook_url': 'invalid_url'
        }

        with pytest.raises(ValueError, match="webhook_url must be a valid HTTP"):
            TelegramConnectorFactory.validate_config(config)

    @pytest.mark.integration
    def test_validate_config_invalid_timeout(self):
        """Test config validation with invalid timeout."""
        config = {
            'bot_token': 'valid_token',
            'read_timeout': -1
        }

        with pytest.raises(ValueError, match="read_timeout must be positive"):
            TelegramConnectorFactory.validate_config(config)

    @pytest.mark.integration
    def test_validate_config_defaults(self):
        """Test config validation applies correct defaults."""
        config = {'bot_token': 'valid_token'}

        validated = TelegramConnectorFactory.validate_config(config)

        assert validated['webhook_path'] == '/webhooks/telegram'
        assert validated['drop_pending_updates'] is True
        assert validated['max_messages_per_request'] == 100
        assert validated['include_private_chats'] is True
        assert validated['read_timeout'] == 30
