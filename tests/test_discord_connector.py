"""
Tests for Discord connector functionality.

This module tests the Discord connector's authentication, real-time ingestion,
historical message fetching, and webhook handling capabilities.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from integrations.discord_connector import (
    DiscordConnector,
    DiscordConnectorError,
    DiscordWebhookError,
    DiscordGatewayError
)
from integrations.base_connector import (
    ConnectorStatus,
    AuthenticationError,
    RawMessage
)
from services.event_bus import EventBus, Event, EventType


@pytest.fixture
def discord_config():
    """Discord connector configuration for testing."""
    return {
        'bot_token': 'test_bot_token_12345',
        'client_id': '123456789',
        'client_secret': 'test_client_secret',
        'webhook_secret': 'test_webhook_secret',
        'intents': 513,  # GUILDS + GUILD_MESSAGES
        'max_results': 50,
        'include_dm_channels': True,
        'monitored_guilds': ['guild_123', 'guild_456'],
        'presence': {
            'status': 'online',
            'afk': False,
            'activities': [],
            'since': None
        }
    }


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    event_bus = AsyncMock(spec=EventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def discord_connector(discord_config, mock_event_bus):
    """Discord connector instance for testing."""
    return DiscordConnector(
        config=discord_config,
        event_bus=mock_event_bus
    )


@pytest.fixture
def mock_bot_user():
    """Mock Discord bot user data."""
    return {
        'id': '987654321',
        'username': 'TestBot',
        'discriminator': '0001',
        'bot': True,
        'verified': True
    }


@pytest.fixture
def mock_gateway_data():
    """Mock Discord gateway data."""
    return {
        'url': 'wss://gateway.discord.gg',
        'shards': 1,
        'session_start_limit': {
            'total': 1000,
            'remaining': 999,
            'reset_after': 86400000,
            'max_concurrency': 1
        }
    }


@pytest.fixture
def mock_guild_data():
    """Mock Discord guild data."""
    return {
        'id': 'guild_123',
        'name': 'Test Guild',
        'channels': [
            {
                'id': 'channel_123',
                'name': 'general',
                'type': 0,  # Text channel
                'guild_id': 'guild_123'
            },
            {
                'id': 'channel_456',
                'name': 'announcements',
                'type': 5,  # Announcement channel
                'guild_id': 'guild_123'
            }
        ],
        'members': [
            {
                'user': {
                    'id': 'user_123',
                    'username': 'testuser',
                    'discriminator': '1234'
                }
            }
        ]
    }


@pytest.fixture
def mock_message_data():
    """Mock Discord message data."""
    return {
        'id': 'message_123',
        'channel_id': 'channel_123',
        'guild_id': 'guild_123',
        'author': {
            'id': 'user_123',
            'username': 'testuser',
            'discriminator': '1234',
            'bot': False
        },
        'content': 'Hello, world!',
        'timestamp': '2024-01-15T10:30:00.000Z',
        'type': 0,
        'attachments': [],
        'embeds': []
    }


class TestDiscordConnectorAuthentication:
    """Test Discord connector authentication."""

    @pytest.mark.asyncio
    async def test_successful_authentication(self, discord_connector, mock_bot_user, mock_gateway_data):
        """Test successful Discord bot authentication."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock bot user endpoint
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_bot_user)

            # Mock gateway endpoint
            mock_gateway_response = AsyncMock()
            mock_gateway_response.status = 200
            mock_gateway_response.json = AsyncMock(
                return_value=mock_gateway_data)

            mock_session.return_value.__aenter__.return_value.get.side_effect = [
                mock_response.__aenter__.return_value,
                mock_gateway_response.__aenter__.return_value
            ]

            await discord_connector.authenticate()

            assert discord_connector.gateway_url == 'wss://gateway.discord.gg'

    @pytest.mark.asyncio
    async def test_authentication_invalid_token(self, discord_connector):
        """Test authentication with invalid bot token."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(AuthenticationError, match="Invalid Discord bot token"):
                await discord_connector.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_missing_token(self):
        """Test authentication with missing bot token."""
        config = {'client_id': '123456789'}
        connector = DiscordConnector(config=config)

        with pytest.raises(AuthenticationError, match="Discord bot token is required"):
            await connector.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_gateway_error(self, discord_connector, mock_bot_user):
        """Test authentication when gateway URL request fails."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock successful bot user endpoint
            mock_user_response = AsyncMock()
            mock_user_response.status = 200
            mock_user_response.json = AsyncMock(return_value=mock_bot_user)

            # Mock failed gateway endpoint
            mock_gateway_response = AsyncMock()
            mock_gateway_response.status = 500

            mock_session.return_value.__aenter__.return_value.get.side_effect = [
                mock_user_response.__aenter__.return_value,
                mock_gateway_response.__aenter__.return_value
            ]

            with pytest.raises(AuthenticationError, match="Failed to get Discord gateway URL"):
                await discord_connector.authenticate()


class TestDiscordConnectorRealTimeIngestion:
    """Test Discord connector real-time ingestion."""

    @pytest.mark.asyncio
    async def test_start_real_time_ingestion(self, discord_connector):
        """Test starting real-time ingestion."""
        with patch.object(discord_connector, '_start_gateway_connection') as mock_start_gateway:
            mock_start_gateway.return_value = None

            await discord_connector.start_real_time_ingestion()

            assert discord_connector._processor_task is not None
            mock_start_gateway.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_real_time_ingestion(self, discord_connector):
        """Test stopping real-time ingestion."""
        # Set up mock tasks
        discord_connector._processor_task = AsyncMock()
        discord_connector._gateway_task = AsyncMock()
        discord_connector._heartbeat_task = AsyncMock()

        with patch.object(discord_connector, '_stop_gateway_connection') as mock_stop_gateway:
            mock_stop_gateway.return_value = None

            await discord_connector.stop_real_time_ingestion()

            mock_stop_gateway.assert_called_once()
            discord_connector._processor_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_gateway_message_handling(self, discord_connector):
        """Test Gateway message handling."""
        # Test HELLO message
        hello_data = {
            'op': 10,
            'd': {'heartbeat_interval': 41250}
        }

        with patch.object(discord_connector, '_handle_hello') as mock_handle_hello:
            await discord_connector._handle_gateway_message(hello_data)
            mock_handle_hello.assert_called_once_with(
                {'heartbeat_interval': 41250})

        # Test DISPATCH message
        dispatch_data = {
            'op': 0,
            't': 'MESSAGE_CREATE',
            's': 123,
            'd': {'id': 'message_123'}
        }

        with patch.object(discord_connector, '_handle_gateway_event') as mock_handle_event:
            await discord_connector._handle_gateway_message(dispatch_data)
            mock_handle_event.assert_called_once_with(
                'MESSAGE_CREATE', {'id': 'message_123'})
            assert discord_connector._sequence_number == 123

    @pytest.mark.asyncio
    async def test_identify_payload(self, discord_connector):
        """Test Gateway identify payload."""
        discord_connector._gateway_connection = AsyncMock()
        discord_connector.bot_token = 'test_token'
        discord_connector.intents = 513

        await discord_connector._identify()

        # Verify identify payload was sent
        discord_connector._gateway_connection.send_str.assert_called_once()
        call_args = discord_connector._gateway_connection.send_str.call_args[0][0]
        payload = json.loads(call_args)

        assert payload['op'] == 2
        assert payload['d']['token'] == 'test_token'
        assert payload['d']['intents'] == 513

    @pytest.mark.asyncio
    async def test_heartbeat_loop(self, discord_connector):
        """Test Gateway heartbeat loop."""
        discord_connector._running = True
        discord_connector._heartbeat_interval = 0.1  # Short interval for testing
        discord_connector._last_heartbeat_ack = True
        discord_connector._gateway_connection = AsyncMock()

        # Start heartbeat loop and let it run briefly
        heartbeat_task = asyncio.create_task(
            discord_connector._heartbeat_loop())
        await asyncio.sleep(0.2)
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Verify heartbeat was sent
        assert discord_connector._gateway_connection.send_str.called


class TestDiscordConnectorHistoricalMessages:
    """Test Discord connector historical message fetching."""

    @pytest.mark.asyncio
    async def test_fetch_historical_messages(self, discord_connector, mock_message_data):
        """Test fetching historical messages."""
        with patch.object(discord_connector, '_get_all_channels') as mock_get_channels:
            with patch.object(discord_connector, '_fetch_channel_history') as mock_fetch_history:
                with patch.object(discord_connector, '_handle_rate_limit') as mock_rate_limit:
                    # Mock channels
                    mock_get_channels.return_value = [
                        {'id': 'channel_123', 'name': 'general', 'type': 0}
                    ]

                    # Mock message history
                    raw_message = RawMessage(
                        id='discord_message_123',
                        platform='discord',
                        platform_message_id='message_123',
                        thread_id='channel_123',
                        sender_id='user_123',
                        content={'text': 'Hello, world!'},
                        timestamp=datetime.now(timezone.utc),
                        raw_data=mock_message_data
                    )
                    mock_fetch_history.return_value = [raw_message]

                    messages = await discord_connector.fetch_historical_messages(limit=10)

                    assert len(messages) == 1
                    assert messages[0].platform == 'discord'
                    assert messages[0].platform_message_id == 'message_123'
                    mock_rate_limit.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_channel_history(self, discord_connector, mock_message_data):
        """Test fetching history for a specific channel."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[mock_message_data])
            mock_response.headers = {}

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            messages = await discord_connector._fetch_channel_history('channel_123', limit=10)

            assert len(messages) == 1
            assert messages[0].platform_message_id == 'message_123'
            assert messages[0].thread_id == 'channel_123'

    @pytest.mark.asyncio
    async def test_fetch_guild_channels(self, discord_connector):
        """Test fetching channels for a guild."""
        channels_data = [
            {'id': 'channel_123', 'name': 'general', 'type': 0},
            # Voice channel (filtered out)
            {'id': 'channel_456', 'name': 'voice', 'type': 2},
            {'id': 'channel_789', 'name': 'announcements', 'type': 5}
        ]

        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=channels_data)
            mock_response.headers = {}

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            channels = await discord_connector._fetch_guild_channels('guild_123')

            # Should only return text channels (types 0, 5, 10, 11, 12)
            assert len(channels) == 2
            assert channels[0]['id'] == 'channel_123'
            assert channels[1]['id'] == 'channel_789'


class TestDiscordConnectorWebhooks:
    """Test Discord connector webhook handling."""

    @pytest.mark.asyncio
    async def test_handle_message_webhook(self, discord_connector, mock_message_data):
        """Test handling MESSAGE_CREATE webhook."""
        webhook_payload = {
            'type': 'MESSAGE_CREATE',
            **mock_message_data
        }

        with patch.object(discord_connector, '_handle_message_event') as mock_handle_message:
            await discord_connector.handle_webhook(webhook_payload)
            mock_handle_message.assert_called_once_with(mock_message_data)

    @pytest.mark.asyncio
    async def test_handle_message_update_webhook(self, discord_connector, mock_message_data):
        """Test handling MESSAGE_UPDATE webhook."""
        webhook_payload = {
            'type': 'MESSAGE_UPDATE',
            **mock_message_data
        }

        with patch.object(discord_connector, '_handle_message_update_event') as mock_handle_update:
            await discord_connector.handle_webhook(webhook_payload)
            mock_handle_update.assert_called_once_with(mock_message_data)

    @pytest.mark.asyncio
    async def test_webhook_signature_validation(self, discord_connector):
        """Test webhook signature validation."""
        discord_connector.webhook_secret = 'test_secret'

        with patch.object(discord_connector, '_validate_webhook_signature') as mock_validate:
            await discord_connector.handle_webhook({'type': 'MESSAGE_CREATE'})
            mock_validate.assert_called_once()


class TestDiscordConnectorMessageProcessing:
    """Test Discord connector message processing."""

    @pytest.mark.asyncio
    async def test_process_message_create(self, discord_connector, mock_message_data, mock_event_bus):
        """Test processing MESSAGE_CREATE event."""
        discord_connector.event_bus = mock_event_bus

        await discord_connector._process_message_create(mock_message_data)

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == 'messages.raw'

        event = call_args[0][1]
        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.data['platform'] == 'discord'

    @pytest.mark.asyncio
    async def test_message_filtering(self, discord_connector):
        """Test filtering of bot messages and system messages."""
        # Bot message should be filtered
        bot_message = {
            'id': 'message_123',
            'author': {'id': 'bot_123', 'bot': True},
            'content': 'Bot message'
        }

        await discord_connector._handle_message_event(bot_message)
        assert discord_connector._processing_queue.empty()

        # System message should be filtered
        system_message = {
            'id': 'message_456',
            'author': {'id': 'user_123', 'bot': False},
            'type': 7,  # System message type
            'content': 'System message'
        }

        await discord_connector._handle_message_event(system_message)
        assert discord_connector._processing_queue.empty()

    @pytest.mark.asyncio
    async def test_guild_filtering(self, discord_connector, mock_message_data):
        """Test filtering messages from non-monitored guilds."""
        discord_connector.monitored_guilds = [
            'guild_456']  # Different from mock data

        await discord_connector._handle_message_event(mock_message_data)
        assert discord_connector._processing_queue.empty()

    def test_extract_message_content(self, discord_connector):
        """Test extracting content from Discord message."""
        message_data = {
            'content': 'Hello, world!',
            'attachments': [
                {
                    'id': 'attachment_123',
                    'filename': 'image.png',
                    'size': 1024,
                    'url': 'https://cdn.discord.com/attachments/123/image.png',
                    'content_type': 'image/png'
                }
            ],
            'embeds': [
                {
                    'title': 'Embed Title',
                    'description': 'Embed Description'
                }
            ]
        }

        content = discord_connector._extract_message_content(message_data)

        assert content['text'] == 'Hello, world!'
        assert len(content['attachments']) == 1
        assert content['attachments'][0]['filename'] == 'image.png'
        assert len(content['embeds']) == 1

    def test_extract_timestamp(self, discord_connector):
        """Test extracting timestamp from Discord message."""
        message_data = {
            'timestamp': '2024-01-15T10:30:00.000Z'
        }

        timestamp = discord_connector._extract_timestamp(message_data)

        assert timestamp.year == 2024
        assert timestamp.month == 1
        assert timestamp.day == 15
        assert timestamp.hour == 10
        assert timestamp.minute == 30


class TestDiscordConnectorHealthCheck:
    """Test Discord connector health check."""

    @pytest.mark.asyncio
    async def test_platform_health_check_success(self, discord_connector, mock_bot_user):
        """Test successful platform health check."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_bot_user)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            # Should not raise an exception
            await discord_connector._platform_health_check()

    @pytest.mark.asyncio
    async def test_platform_health_check_failure(self, discord_connector):
        """Test failed platform health check."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(DiscordConnectorError, match="API test failed"):
                await discord_connector._platform_health_check()

    @pytest.mark.asyncio
    async def test_health_check_missing_token(self, discord_connector):
        """Test health check with missing bot token."""
        discord_connector.bot_token = None

        with pytest.raises(DiscordConnectorError, match="Bot token not available"):
            await discord_connector._platform_health_check()


class TestDiscordConnectorRateLimiting:
    """Test Discord connector rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, discord_connector):
        """Test handling of rate limit responses."""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset-After': '1.5',
            'X-RateLimit-Bucket': 'test_bucket',
            'Retry-After': '2.0'
        }

        with patch('asyncio.sleep') as mock_sleep:
            await discord_connector._handle_rate_limit_response(mock_response)
            mock_sleep.assert_called_once_with(2.0)

        assert discord_connector._rate_limit_remaining == 0
        assert discord_connector._rate_limit_reset_after == 1.5

    @pytest.mark.asyncio
    async def test_proactive_rate_limiting(self, discord_connector):
        """Test proactive rate limiting."""
        discord_connector._rate_limit_remaining = 1
        discord_connector._rate_limit_reset_after = 1.0

        with patch('asyncio.sleep') as mock_sleep:
            await discord_connector._handle_rate_limit()
            mock_sleep.assert_called_once_with(1.0)


class TestDiscordConnectorCaching:
    """Test Discord connector caching functionality."""

    def test_guild_caching(self, discord_connector, mock_guild_data):
        """Test guild information caching."""
        guild_id = mock_guild_data['id']
        discord_connector._guilds_cache[guild_id] = mock_guild_data

        guild_info = discord_connector.get_guild_info(guild_id)
        assert guild_info == mock_guild_data

    def test_channel_caching(self, discord_connector):
        """Test channel information caching."""
        channel_data = {
            'id': 'channel_123',
            'name': 'general',
            'type': 0,
            'guild_id': 'guild_123'
        }

        discord_connector._channels_cache['channel_123'] = channel_data

        channel_info = discord_connector.get_channel_info('channel_123')
        assert channel_info == channel_data

    def test_user_caching(self, discord_connector):
        """Test user information caching."""
        user_data = {
            'id': 'user_123',
            'username': 'testuser',
            'discriminator': '1234'
        }

        discord_connector._users_cache['user_123'] = user_data

        user_info = discord_connector.get_user_info('user_123')
        assert user_info == user_data


class TestDiscordConnectorConfiguration:
    """Test Discord connector configuration."""

    def test_default_configuration(self):
        """Test connector with default configuration."""
        config = {'bot_token': 'test_token'}
        connector = DiscordConnector(config=config)

        assert connector.intents == 513  # Default intents
        assert connector.max_results == 100
        assert connector.include_dm_channels is True
        assert connector.monitored_guilds == []

    def test_custom_configuration(self):
        """Test connector with custom configuration."""
        config = {
            'bot_token': 'test_token',
            'intents': 1024,
            'max_results': 50,
            'include_dm_channels': False,
            'monitored_guilds': ['guild_123'],
            'presence': {
                'status': 'dnd',
                'afk': True
            }
        }

        connector = DiscordConnector(config=config)

        assert connector.intents == 1024
        assert connector.max_results == 50
        assert connector.include_dm_channels is False
        assert connector.monitored_guilds == ['guild_123']
        assert connector.presence['status'] == 'dnd'


if __name__ == '__main__':
    pytest.main([__file__])
