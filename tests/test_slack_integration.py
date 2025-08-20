"""
Integration tests for Slack connector authentication and real-time processing.

This module tests the complete integration flow including OAuth authentication,
Socket Mode connections, and real-time message processing.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from integrations.slack_connector import SlackConnector, SlackSocketModeError
from integrations.slack_factory import SlackConnectorFactory
from integrations.base_connector import ConnectorStatus
from services.event_bus import EventBus


class TestSlackAuthentication:
    """Test Slack authentication flows."""

    @pytest.fixture
    def auth_config(self) -> Dict[str, Any]:
        """Configuration for authentication testing."""
        return {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'signing_secret': 'test_signing_secret',
            'app_token': 'xapp-test-token',
            'bot_token': 'xoxb-test-bot-token',
            'scopes': ['channels:history', 'chat:write', 'users:read'],
            'redirect_uri': 'http://localhost:8000/slack/oauth/callback',
            'socket_mode_enabled': True,
            'events_api_enabled': True
        }

    @pytest.mark.asyncio
    async def test_oauth_url_generation(self):
        """Test OAuth URL generation."""
        # Mock settings
        with patch('integrations.slack_factory.settings') as mock_settings:
            mock_settings.SLACK_CLIENT_ID = 'test_client_id'
            mock_settings.SLACK_SCOPES = 'channels:history chat:write'
            mock_settings.SLACK_REDIRECT_URI = 'http://localhost:8000/slack/oauth/callback'

            oauth_url = SlackConnectorFactory.get_oauth_url()

            assert 'slack.com/oauth/v2/authorize' in oauth_url
            assert 'client_id=test_client_id' in oauth_url
            assert 'scope=channels%3Ahistory+chat%3Awrite' in oauth_url

    @pytest.mark.asyncio
    async def test_token_validation_success(self, auth_config):
        """Test successful token validation."""
        connector = SlackConnector(config=auth_config)

        # Mock HTTP session and successful auth response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': True,
            'user': 'test_bot',
            'team': 'Test Team',
            'team_id': 'T1234567890',
            'user_id': 'U1234567890'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        connector._session = mock_session
        connector.bot_token = auth_config['bot_token']

        # Should not raise exception
        await connector._validate_tokens()

        # Verify auth.test was called
        mock_session.post.assert_called()
        call_args = mock_session.post.call_args[0][0]
        assert 'auth.test' in call_args

    @pytest.mark.asyncio
    async def test_token_validation_failure(self, auth_config):
        """Test token validation failure."""
        connector = SlackConnector(config=auth_config)

        # Mock HTTP session and failed auth response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': False,
            'error': 'invalid_auth'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        connector._session = mock_session
        connector.bot_token = 'invalid_token'

        # Should raise authentication error
        with pytest.raises(Exception) as exc_info:
            await connector._validate_tokens()

        assert 'invalid_auth' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_workspace_info_loading(self, auth_config):
        """Test loading workspace information during authentication."""
        connector = SlackConnector(config=auth_config)

        # Mock API responses
        mock_session = AsyncMock()

        # Team info response
        team_response = AsyncMock()
        team_response.json.return_value = {
            'ok': True,
            'team': {
                'id': 'T1234567890',
                'name': 'Test Workspace',
                'domain': 'test-workspace',
                'email_domain': 'example.com'
            }
        }
        team_response.raise_for_status.return_value = None

        # Channels response
        channels_response = AsyncMock()
        channels_response.json.return_value = {
            'ok': True,
            'channels': [
                {
                    'id': 'C1234567890',
                    'name': 'general',
                    'is_channel': True,
                    'is_private': False,
                    'is_member': True
                },
                {
                    'id': 'C0987654321',
                    'name': 'private-channel',
                    'is_channel': True,
                    'is_private': True,
                    'is_member': True
                }
            ]
        }
        channels_response.raise_for_status.return_value = None

        # Users response
        users_response = AsyncMock()
        users_response.json.return_value = {
            'ok': True,
            'members': [
                {
                    'id': 'U1234567890',
                    'name': 'testuser',
                    'real_name': 'Test User',
                    'profile': {
                        'email': 'test@example.com',
                        'display_name': 'Test User'
                    }
                },
                {
                    'id': 'U0987654321',
                    'name': 'anotheruser',
                    'real_name': 'Another User',
                    'profile': {
                        'email': 'another@example.com'
                    }
                }
            ]
        }
        users_response.raise_for_status.return_value = None

        # Mock session to return appropriate responses
        def mock_post(url, **kwargs):
            if 'team.info' in url:
                return team_response
            elif 'conversations.list' in url:
                return channels_response
            elif 'users.list' in url:
                return users_response
            return AsyncMock()

        mock_session.post.side_effect = mock_post
        connector._session = mock_session
        connector.bot_token = auth_config['bot_token']

        await connector._load_workspace_info()

        # Verify team info
        assert connector._team_info is not None
        assert connector._team_info['name'] == 'Test Workspace'
        assert connector._team_info['domain'] == 'test-workspace'

        # Verify channels
        assert len(connector._channels_cache) == 2
        assert 'C1234567890' in connector._channels_cache
        assert connector._channels_cache['C1234567890']['name'] == 'general'
        assert 'C0987654321' in connector._channels_cache
        assert connector._channels_cache['C0987654321']['is_private'] is True

        # Verify users
        assert len(connector._users_cache) == 2
        assert 'U1234567890' in connector._users_cache
        assert connector._users_cache['U1234567890']['real_name'] == 'Test User'


class TestSlackSocketMode:
    """Test Slack Socket Mode functionality."""

    @pytest.fixture
    def socket_config(self) -> Dict[str, Any]:
        """Configuration for Socket Mode testing."""
        return {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'app_token': 'xapp-test-token',
            'bot_token': 'xoxb-test-bot-token',
            'socket_mode_enabled': True,
            'events_api_enabled': False
        }

    @pytest.mark.asyncio
    async def test_socket_mode_connection_setup(self, socket_config):
        """Test Socket Mode connection setup."""
        connector = SlackConnector(config=socket_config)

        # Mock HTTP session for apps.connections.open
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': True,
            'url': 'wss://wss-primary.slack.com/websocket/test-connection-id'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        connector._session = mock_session
        connector.bot_token = socket_config['bot_token']

        await connector._start_socket_mode()

        # Verify apps.connections.open was called
        mock_session.post.assert_called()
        call_args = mock_session.post.call_args[0][0]
        assert 'apps.connections.open' in call_args

        # Verify socket task was created
        assert connector._socket_task is not None

    @pytest.mark.asyncio
    async def test_socket_mode_message_handling(self, socket_config):
        """Test Socket Mode message handling."""
        connector = SlackConnector(config=socket_config)

        # Test hello message
        hello_message = {'type': 'hello'}
        await connector._handle_socket_message(hello_message)
        # Should not raise exception

        # Test events_api message
        events_message = {
            'type': 'events_api',
            'envelope_id': 'test-envelope-123',
            'payload': {
                'event': {
                    'type': 'message',
                    'ts': '1234567890.123456',
                    'user': 'U1234567890',
                    'text': 'Hello from Socket Mode!',
                    'channel': 'C1234567890'
                }
            }
        }

        # Mock WebSocket connection for acknowledgment
        mock_ws = AsyncMock()
        connector._socket_connection = mock_ws

        # Mock event handling
        with patch.object(connector, '_handle_slack_event') as mock_handle:
            await connector._handle_socket_message(events_message)

            # Verify acknowledgment was sent
            mock_ws.send.assert_called_once()
            ack_data = json.loads(mock_ws.send.call_args[0][0])
            assert ack_data['envelope_id'] == 'test-envelope-123'

            # Verify event was handled
            mock_handle.assert_called_once()

        # Test disconnect message
        disconnect_message = {
            'type': 'disconnect',
            'reason': 'warning'
        }
        await connector._handle_socket_message(disconnect_message)
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_socket_mode_reconnection(self, socket_config):
        """Test Socket Mode reconnection logic."""
        connector = SlackConnector(config=socket_config)
        connector._running = True
        connector._max_reconnect_attempts = 2

        # Mock apps.connections.open response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': True,
            'url': 'wss://wss-primary.slack.com/websocket/test-connection-id'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        connector._session = mock_session

        # Test that reconnection attempts are tracked
        connector._reconnect_attempts = 0

        # Simulate a connection failure scenario
        with patch('integrations.slack_connector.websockets.connect') as mock_connect:
            mock_connect.side_effect = ConnectionError("Connection failed")

            try:
                await asyncio.wait_for(
                    connector._socket_mode_handler('wss://test-url'),
                    timeout=0.5
                )
            except asyncio.TimeoutError:
                pass  # Expected for this test

        # Verify reconnection attempts were made
        assert connector._reconnect_attempts > 0


class TestSlackRealTimeProcessing:
    """Test real-time message processing."""

    @pytest.fixture
    def processing_config(self) -> Dict[str, Any]:
        """Configuration for real-time processing testing."""
        return {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'bot_token': 'xoxb-test-bot-token',
            'socket_mode_enabled': False,
            'events_api_enabled': True
        }

    @pytest.mark.asyncio
    async def test_message_event_processing(self, processing_config):
        """Test processing of message events."""
        mock_event_bus = AsyncMock(spec=EventBus)
        connector = SlackConnector(
            config=processing_config, event_bus=mock_event_bus)

        # Sample message event
        message_event = {
            'type': 'message',
            'ts': '1234567890.123456',
            'user': 'U1234567890',
            'text': 'Hello, this is a test message!',
            'channel': 'C1234567890',
            'team': 'T1234567890'
        }

        await connector._process_message_event(message_event)

        # Verify event was published to event bus
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args

        assert call_args[0][0] == 'messages.raw'
        event = call_args[0][1]
        assert event.type.value == 'message.received'
        assert event.data['platform'] == 'slack'
        assert 'message' in event.data

    @pytest.mark.asyncio
    async def test_message_filtering(self, processing_config):
        """Test filtering of unwanted messages."""
        connector = SlackConnector(config=processing_config)

        # Bot message (should be filtered)
        bot_message = {
            'type': 'message',
            'ts': '1234567890.123456',
            'bot_id': 'B1234567890',
            'text': 'This is a bot message',
            'channel': 'C1234567890'
        }

        await connector._handle_slack_event(bot_message)
        assert connector._processing_queue.empty()

        # Message with subtype (should be filtered)
        subtype_message = {
            'type': 'message',
            'subtype': 'bot_message',
            'ts': '1234567890.123456',
            'text': 'This is a bot message',
            'channel': 'C1234567890'
        }

        await connector._handle_slack_event(subtype_message)
        assert connector._processing_queue.empty()

        # Regular message (should be processed)
        regular_message = {
            'type': 'message',
            'ts': '1234567890.123456',
            'user': 'U1234567890',
            'text': 'This is a regular message',
            'channel': 'C1234567890'
        }

        await connector._handle_slack_event(regular_message)
        assert not connector._processing_queue.empty()

    @pytest.mark.asyncio
    async def test_message_queue_processing(self, processing_config):
        """Test message queue processing."""
        mock_event_bus = AsyncMock(spec=EventBus)
        connector = SlackConnector(
            config=processing_config, event_bus=mock_event_bus)

        # Add test message to queue
        test_message = {
            'type': 'message',
            'event': {
                'type': 'message',
                'ts': '1234567890.123456',
                'user': 'U1234567890',
                'text': 'Test message',
                'channel': 'C1234567890'
            },
            'timestamp': datetime.now(timezone.utc)
        }

        await connector._processing_queue.put(test_message)

        # Start processor for a short time
        processor_task = asyncio.create_task(
            connector._process_message_queue())
        await asyncio.sleep(0.1)  # Let it process
        processor_task.cancel()

        try:
            await processor_task
        except asyncio.CancelledError:
            pass

        # Verify message was processed and published
        mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_channel_and_user_events(self, processing_config):
        """Test handling of channel and user events."""
        connector = SlackConnector(config=processing_config)

        # Mock the cache loading methods
        with patch.object(connector, '_load_channels') as mock_load_channels, \
                patch.object(connector, '_load_users') as mock_load_users:

            # Channel created event
            channel_event = {
                'type': 'channel_created',
                'channel': {
                    'id': 'C9999999999',
                    'name': 'new-channel'
                }
            }

            await connector._handle_slack_event(channel_event)
            mock_load_channels.assert_called_once()

            # User change event
            user_event = {
                'type': 'user_change',
                'user': {
                    'id': 'U9999999999',
                    'name': 'updated-user'
                }
            }

            await connector._handle_slack_event(user_event)
            mock_load_users.assert_called_once()


class TestSlackConnectorFactory:
    """Test Slack connector factory functionality."""

    @pytest.mark.asyncio
    async def test_factory_config_validation(self):
        """Test configuration validation in factory."""
        # Mock settings with valid configuration
        with patch('integrations.slack_factory.settings') as mock_settings:
            mock_settings.SLACK_CLIENT_ID = 'test_client_id'
            mock_settings.SLACK_CLIENT_SECRET = 'test_client_secret'
            mock_settings.SLACK_BOT_TOKEN = 'xoxb-test-token'

            assert SlackConnectorFactory.validate_config() is True

        # Mock settings with missing required fields
        with patch('integrations.slack_factory.settings') as mock_settings:
            mock_settings.SLACK_CLIENT_ID = None
            mock_settings.SLACK_CLIENT_SECRET = None
            mock_settings.SLACK_BOT_TOKEN = None

            assert SlackConnectorFactory.validate_config() is False

    @pytest.mark.asyncio
    async def test_factory_connector_creation(self):
        """Test connector creation through factory."""
        mock_event_bus = AsyncMock(spec=EventBus)

        # Mock settings
        with patch('integrations.slack_factory.settings') as mock_settings:
            mock_settings.SLACK_CLIENT_ID = 'test_client_id'
            mock_settings.SLACK_CLIENT_SECRET = 'test_client_secret'
            mock_settings.SLACK_BOT_TOKEN = 'xoxb-test-token'
            mock_settings.SLACK_SCOPES = 'channels:history chat:write'
            mock_settings.SLACK_REDIRECT_URI = 'http://localhost:8000/slack/oauth/callback'
            mock_settings.SLACK_SOCKET_MODE_ENABLED = True
            mock_settings.SLACK_EVENTS_API_ENABLED = True
            mock_settings.SLACK_MAX_RESULTS = 100
            mock_settings.SLACK_INCLUDE_PRIVATE_CHANNELS = True
            mock_settings.SLACK_INCLUDE_DIRECT_MESSAGES = True
            mock_settings.SLACK_WEBHOOK_ENDPOINT = '/webhooks/slack'
            mock_settings.SLACK_SIGNING_SECRET = 'test_signing_secret'
            mock_settings.SLACK_APP_TOKEN = 'xapp-test-token'
            mock_settings.SLACK_USER_TOKEN = None

            connector = SlackConnectorFactory.create_connector(
                event_bus=mock_event_bus)

            assert isinstance(connector, SlackConnector)
            assert connector.platform == 'slack'
            assert connector.client_id == 'test_client_id'
            assert connector.event_bus == mock_event_bus

    def test_factory_test_connector_creation(self):
        """Test test connector creation."""
        test_connector = SlackConnectorFactory.create_test_connector()

        assert isinstance(test_connector, SlackConnector)
        assert test_connector.platform == 'slack'
        assert test_connector.client_id == 'test_client_id'
        assert not test_connector.socket_mode_enabled  # Disabled for testing
