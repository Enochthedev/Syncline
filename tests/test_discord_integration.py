"""
Integration tests for Discord connector.

This module tests the Discord connector's integration with the event bus,
message normalization, and end-to-end message processing workflows.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from integrations.discord_connector import DiscordConnector
from integrations.discord_factory import DiscordConnectorFactory
from integrations.connector_manager import ConnectorManager
from services.event_bus import EventBus, Event, EventType
from services.message_normalizer import MessageNormalizer
from services.message_schema import Platform, NormalizedMessage


@pytest.fixture
def discord_config():
    """Discord connector configuration for integration testing."""
    return {
        'bot_token': 'test_bot_token_integration',
        'client_id': '123456789',
        'intents': 513,
        'max_results': 10,
        'include_dm_channels': True,
        'monitored_guilds': ['test_guild_123']
    }


@pytest.fixture
def event_bus():
    """Mock event bus instance for integration testing."""
    return AsyncMock(spec=EventBus)


@pytest.fixture
def message_normalizer():
    """Message normalizer for integration testing."""
    return MessageNormalizer()


@pytest.fixture
def mock_discord_message():
    """Mock Discord message for integration testing."""
    return {
        'id': '123456789012345678',
        'channel_id': '987654321098765432',
        'guild_id': 'test_guild_123',
        'author': {
            'id': '111222333444555666',
            'username': 'testuser',
            'discriminator': '1234',
            'bot': False,
            'avatar': 'avatar_hash'
        },
        'content': 'Hello from Discord! This is a test message.',
        'timestamp': '2024-01-15T10:30:00.000Z',
        'edited_timestamp': None,
        'tts': False,
        'mention_everyone': False,
        'mentions': [],
        'mention_roles': [],
        'mention_channels': [],
        'attachments': [
            {
                'id': '777888999000111222',
                'filename': 'test_image.png',
                'size': 2048,
                'url': 'https://cdn.discord.com/attachments/123/test_image.png',
                'proxy_url': 'https://media.discord.com/attachments/123/test_image.png',
                'content_type': 'image/png',
                'width': 800,
                'height': 600
            }
        ],
        'embeds': [
            {
                'title': 'Test Embed',
                'description': 'This is a test embed',
                'color': 16711680,
                'timestamp': '2024-01-15T10:30:00.000Z',
                'footer': {
                    'text': 'Footer text'
                }
            }
        ],
        'reactions': [],
        'nonce': None,
        'pinned': False,
        'webhook_id': None,
        'type': 0,
        'activity': None,
        'application': None,
        'message_reference': None,
        'flags': 0,
        'referenced_message': None,
        'interaction': None,
        'thread': None,
        'components': [],
        'sticker_items': []
    }


class TestDiscordConnectorIntegration:
    """Test Discord connector integration with other components."""

    @pytest.mark.asyncio
    async def test_connector_factory_creation(self, discord_config, event_bus):
        """Test creating Discord connector through factory."""
        connector = DiscordConnectorFactory.create_connector(
            config=discord_config,
            event_bus=event_bus
        )

        assert isinstance(connector, DiscordConnector)
        assert connector.platform == 'discord'
        assert connector.event_bus == event_bus
        assert connector.bot_token == 'test_bot_token_integration'

    @pytest.mark.asyncio
    async def test_connector_factory_from_env(self, event_bus):
        """Test creating Discord connector from environment variables."""
        env_vars = {
            'DISCORD_BOT_TOKEN': 'env_bot_token',
            'DISCORD_CLIENT_ID': '987654321',
            'DISCORD_INTENTS': '1024',
            'DISCORD_MAX_RESULTS': '25',
            'DISCORD_INCLUDE_DM_CHANNELS': 'false',
            'DISCORD_MONITORED_GUILDS': 'guild1,guild2,guild3'
        }

        with patch.dict('os.environ', env_vars):
            connector = DiscordConnectorFactory.create_from_env(
                event_bus=event_bus)

            assert connector.bot_token == 'env_bot_token'
            assert connector.intents == 1024
            assert connector.max_results == 25
            assert connector.include_dm_channels is False
            assert connector.monitored_guilds == ['guild1', 'guild2', 'guild3']

    @pytest.mark.asyncio
    async def test_end_to_end_message_processing(
        self,
        discord_config,
        event_bus,
        message_normalizer,
        mock_discord_message
    ):
        """Test end-to-end message processing from Discord to normalized message."""
        connector = DiscordConnector(
            config=discord_config, event_bus=event_bus)

        # Mock the event bus publish method to capture events
        published_events = []

        async def capture_event(stream, event):
            published_events.append((stream, event))

        event_bus.publish = capture_event

        # Process the Discord message
        await connector._process_message_create(mock_discord_message)

        # Verify event was published
        assert len(published_events) == 1
        stream, event = published_events[0]

        assert stream == 'messages.raw'
        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.data['platform'] == 'discord'

        # Extract the raw message from the event
        raw_message_data = event.data['message']

        # Verify raw message structure
        assert raw_message_data['platform'] == 'discord'
        assert raw_message_data['platform_message_id'] == '123456789012345678'
        assert raw_message_data['thread_id'] == '987654321098765432'
        assert raw_message_data['sender_id'] == '111222333444555666'

        # Verify content extraction
        content = raw_message_data['content']
        assert content['text'] == 'Hello from Discord! This is a test message.'
        assert len(content['attachments']) == 1
        assert content['attachments'][0]['filename'] == 'test_image.png'
        assert len(content['embeds']) == 1

    @pytest.mark.asyncio
    async def test_connector_manager_integration(self, discord_config, event_bus):
        """Test Discord connector integration with connector manager."""
        # Create connector through factory
        connector = DiscordConnectorFactory.create_connector(
            config=discord_config,
            event_bus=event_bus
        )

        # Create connector manager
        manager = ConnectorManager(event_bus=event_bus)

        # Register connector
        await manager.register_connector(connector)

        # Verify connector is registered
        assert 'discord' in manager._connectors
        assert manager._connectors['discord'] == connector

        # Test health check through manager
        health_status = await manager.get_connector_health('discord')
        assert health_status is not None

    @pytest.mark.asyncio
    async def test_message_normalization_integration(
        self,
        discord_config,
        mock_discord_message,
        message_normalizer
    ):
        """Test integration with message normalization."""
        connector = DiscordConnector(config=discord_config)

        # Extract content using connector
        content = connector._extract_message_content(mock_discord_message)
        timestamp = connector._extract_timestamp(mock_discord_message)

        # Create raw message
        from integrations.base_connector import RawMessage
        raw_message = RawMessage(
            id=f"discord_{mock_discord_message['id']}",
            platform='discord',
            platform_message_id=mock_discord_message['id'],
            thread_id=mock_discord_message['channel_id'],
            sender_id=mock_discord_message['author']['id'],
            content=content,
            timestamp=timestamp,
            raw_data=mock_discord_message
        )

        # Normalize the message (this would typically be done by the message normalizer)
        # For this test, we'll verify the raw message structure is correct for normalization
        assert raw_message.platform == 'discord'
        assert raw_message.content['text'] == 'Hello from Discord! This is a test message.'
        assert len(raw_message.content['attachments']) == 1
        assert raw_message.timestamp.year == 2024

    @pytest.mark.asyncio
    async def test_real_time_event_flow(self, discord_config, event_bus, mock_discord_message):
        """Test real-time event flow from Gateway to event bus."""
        connector = DiscordConnector(
            config=discord_config, event_bus=event_bus)

        # Mock the processing queue
        processed_events = []

        async def mock_process_message_create(data):
            processed_events.append(data)

        connector._process_message_create = mock_process_message_create

        # Simulate Gateway event handling
        await connector._handle_message_event(mock_discord_message)

        # Wait for queue processing
        await asyncio.sleep(0.1)

        # Start the processor to handle queued messages
        processor_task = asyncio.create_task(
            connector._process_message_queue())
        await asyncio.sleep(0.1)
        processor_task.cancel()

        try:
            await processor_task
        except asyncio.CancelledError:
            pass

        # Verify message was processed
        assert len(processed_events) == 1
        assert processed_events[0]['id'] == mock_discord_message['id']

    @pytest.mark.asyncio
    async def test_webhook_to_event_bus_flow(self, discord_config, event_bus, mock_discord_message):
        """Test webhook handling flow to event bus."""
        connector = DiscordConnector(
            config=discord_config, event_bus=event_bus)

        # Mock event bus to capture published events
        published_events = []

        async def capture_event(stream, event):
            published_events.append((stream, event))

        event_bus.publish = capture_event

        # Create webhook payload
        webhook_payload = {
            'type': 'MESSAGE_CREATE',
            **mock_discord_message
        }

        # Process webhook
        await connector.handle_webhook(webhook_payload)

        # Process the queued message
        processor_task = asyncio.create_task(
            connector._process_message_queue())
        await asyncio.sleep(0.1)
        processor_task.cancel()

        try:
            await processor_task
        except asyncio.CancelledError:
            pass

        # Verify event was published
        assert len(published_events) == 1
        stream, event = published_events[0]
        assert stream == 'messages.raw'
        assert event.type == EventType.MESSAGE_RECEIVED

    @pytest.mark.asyncio
    async def test_historical_message_fetching_integration(self, discord_config):
        """Test historical message fetching integration."""
        connector = DiscordConnector(config=discord_config)

        # Mock API responses
        mock_channels = [
            {'id': 'channel_123', 'name': 'general', 'type': 0},
            {'id': 'channel_456', 'name': 'announcements', 'type': 5}
        ]

        mock_messages = [
            {
                'id': 'msg_1',
                'channel_id': 'channel_123',
                'author': {'id': 'user_1', 'bot': False},
                'content': 'Message 1',
                'timestamp': '2024-01-15T10:00:00.000Z',
                'type': 0
            },
            {
                'id': 'msg_2',
                'channel_id': 'channel_123',
                'author': {'id': 'user_2', 'bot': False},
                'content': 'Message 2',
                'timestamp': '2024-01-15T10:01:00.000Z',
                'type': 0
            }
        ]

        with patch.object(connector, '_get_all_channels') as mock_get_channels:
            with patch.object(connector, '_fetch_channel_history') as mock_fetch_history:
                with patch.object(connector, '_handle_rate_limit') as mock_rate_limit:
                    mock_get_channels.return_value = mock_channels

                    # Mock channel history for each channel
                    def mock_history(channel_id, cursor, limit):
                        from integrations.base_connector import RawMessage
                        if channel_id == 'channel_123':
                            return [
                                RawMessage(
                                    id=f"discord_{msg['id']}",
                                    platform='discord',
                                    platform_message_id=msg['id'],
                                    thread_id=msg['channel_id'],
                                    sender_id=msg['author']['id'],
                                    content={'text': msg['content']},
                                    timestamp=datetime.fromisoformat(
                                        msg['timestamp'].replace('Z', '+00:00')),
                                    raw_data=msg
                                ) for msg in mock_messages
                            ]
                        return []

                    mock_fetch_history.side_effect = mock_history

                    # Fetch historical messages
                    messages = await connector.fetch_historical_messages(limit=10)

                    # Verify results
                    assert len(messages) == 2
                    assert messages[0].platform == 'discord'
                    assert messages[0].content['text'] == 'Message 1'
                    assert messages[1].content['text'] == 'Message 2'

                    # Verify rate limiting was applied
                    assert mock_rate_limit.call_count == len(mock_channels)

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, discord_config, event_bus):
        """Test error handling integration across components."""
        connector = DiscordConnector(
            config=discord_config, event_bus=event_bus)

        # Test authentication error handling
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(Exception):  # Should raise authentication error
                await connector.authenticate()

        # Test Gateway connection error handling
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.ws_connect.side_effect = Exception(
                "Connection failed")

            # Should handle connection errors gracefully
            connector._running = True
            connector._reconnect_attempts = 0
            connector.gateway_url = 'wss://test.gateway'

            # Start gateway handler
            gateway_task = asyncio.create_task(connector._gateway_handler())
            await asyncio.sleep(0.1)
            gateway_task.cancel()

            try:
                await gateway_task
            except asyncio.CancelledError:
                pass

            # Should have attempted reconnection
            assert connector._reconnect_attempts > 0

    @pytest.mark.asyncio
    async def test_performance_under_load(self, discord_config, event_bus):
        """Test Discord connector performance under message load."""
        connector = DiscordConnector(
            config=discord_config, event_bus=event_bus)

        # Mock event bus to count published events
        published_count = 0

        async def count_events(stream, event):
            nonlocal published_count
            published_count += 1

        event_bus.publish = count_events

        # Generate multiple messages
        messages = []
        for i in range(100):
            message = {
                'id': f'message_{i}',
                'channel_id': 'channel_123',
                'guild_id': 'test_guild_123',
                'author': {
                    'id': f'user_{i % 10}',
                    'username': f'user{i % 10}',
                    'bot': False
                },
                'content': f'Test message {i}',
                'timestamp': '2024-01-15T10:30:00.000Z',
                'type': 0
            }
            messages.append(message)

        # Process messages concurrently
        start_time = asyncio.get_event_loop().time()

        tasks = [connector._process_message_create(msg) for msg in messages]
        await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        # Verify all messages were processed
        assert published_count == 100

        # Verify reasonable performance (should process 100 messages in under 1 second)
        assert processing_time < 1.0

        print(
            f"Processed {len(messages)} messages in {processing_time:.3f} seconds")


class TestDiscordConnectorConfigurationIntegration:
    """Test Discord connector configuration integration."""

    def test_configuration_validation(self):
        """Test configuration validation integration."""
        # Valid configuration
        valid_config = {
            'bot_token': 'valid_token_12345678901234567890123456789012345678901234567890',
            'intents': 513,
            'max_results': 50
        }

        assert DiscordConnectorFactory.validate_config(valid_config)

        # Invalid configuration - missing bot token
        invalid_config = {
            'intents': 513
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            DiscordConnectorFactory.validate_config(invalid_config)

        # Invalid configuration - invalid intents
        invalid_intents_config = {
            'bot_token': 'valid_token_12345678901234567890123456789012345678901234567890',
            'intents': -1
        }

        with pytest.raises(ValueError, match="Invalid intents value"):
            DiscordConnectorFactory.validate_config(invalid_intents_config)

    @pytest.mark.asyncio
    async def test_environment_configuration_integration(self):
        """Test environment-based configuration integration."""
        env_vars = {
            'DISCORD_BOT_TOKEN': 'env_test_token_12345678901234567890123456789012345678901234567890',
            'DISCORD_CLIENT_ID': '123456789012345678',
            'DISCORD_INTENTS': '1024',
            'DISCORD_MAX_RESULTS': '25',
            'DISCORD_INCLUDE_DM_CHANNELS': 'false',
            'DISCORD_MONITORED_GUILDS': 'guild1,guild2,guild3',
            'DISCORD_STATUS': 'dnd'
        }

        with patch.dict('os.environ', env_vars):
            connector = DiscordConnectorFactory.create_from_env()

            assert connector.bot_token == 'env_test_token_12345678901234567890123456789012345678901234567890'
            assert connector.client_id == '123456789012345678'
            assert connector.intents == 1024
            assert connector.max_results == 25
            assert connector.include_dm_channels is False
            assert connector.monitored_guilds == ['guild1', 'guild2', 'guild3']
            assert connector.presence['status'] == 'dnd'


if __name__ == '__main__':
    pytest.main([__file__])
