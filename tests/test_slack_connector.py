"""
Unit tests for Slack connector functionality.

This module tests the SlackConnector class including authentication,
message processing, and API interactions.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from integrations.slack_connector import SlackConnector, SlackConnectorError
from integrations.base_connector import RawMessage, ConnectorStatus
from services.event_bus import EventBus, Event, EventType


class TestSlackConnector:
    """Test cases for SlackConnector."""

    @pytest.fixture
    def slack_config(self) -> Dict[str, Any]:
        """Slack connector configuration for testing."""
        return {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'signing_secret': 'test_signing_secret',
            'app_token': 'xapp-test-token',
            'bot_token': 'xoxb-test-bot-token',
            'scopes': ['channels:history', 'chat:write', 'users:read'],
            'redirect_uri': 'http://localhost:8000/slack/oauth/callback',
            'socket_mode_enabled': False,  # Disable for testing
            'events_api_enabled': True,
            'max_results': 50
        }

    @pytest.fixture
    def mock_event_bus(self) -> AsyncMock:
        """Mock event bus for testing."""
        return AsyncMock(spec=EventBus)

    @pytest.fixture
    def slack_connector(self, slack_config, mock_event_bus) -> SlackConnector:
        """Create SlackConnector instance for testing."""
        return SlackConnector(config=slack_config, event_bus=mock_event_bus)

    @pytest.fixture
    def sample_slack_message(self) -> Dict[str, Any]:
        """Sample Slack message for testing."""
        return {
            'type': 'message',
            'ts': '1234567890.123456',
            'user': 'U1234567890',
            'text': 'Hello, world!',
            'channel': 'C1234567890',
            'team': 'T1234567890'
        }

    @pytest.fixture
    def sample_channel_history(self) -> Dict[str, Any]:
        """Sample channel history response."""
        return {
            'ok': True,
            'messages': [
                {
                    'type': 'message',
                    'ts': '1234567890.123456',
                    'user': 'U1234567890',
                    'text': 'Hello, world!',
                    'channel': 'C1234567890'
                },
                {
                    'type': 'message',
                    'ts': '1234567891.123456',
                    'user': 'U0987654321',
                    'text': 'Hi there!',
                    'channel': 'C1234567890'
                }
            ],
            'has_more': False
        }

    def test_connector_initialization(self, slack_config, mock_event_bus):
        """Test SlackConnector initialization."""
        connector = SlackConnector(
            config=slack_config, event_bus=mock_event_bus)

        assert connector.platform == "slack"
        assert connector.client_id == "test_client_id"
        assert connector.client_secret == "test_client_secret"
        assert connector.app_token == "xapp-test-token"
        assert connector.bot_token is None  # Not set until authentication
        assert connector.event_bus == mock_event_bus
        assert not connector.socket_mode_enabled  # Disabled in config
        assert connector.events_api_enabled

    @pytest.mark.asyncio
    async def test_authentication_with_bot_token(self, slack_connector):
        """Test authentication using bot token."""
        # Mock the HTTP session and API response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': True,
            'user': 'test_bot',
            'team': 'Test Team',
            'team_id': 'T1234567890'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        slack_connector._session = mock_session
        slack_connector.bot_token = 'xoxb-test-bot-token'

        await slack_connector._validate_tokens()

        # Verify API call was made
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert 'auth.test' in call_args[0][0]

    @pytest.mark.asyncio
    async def test_authentication_failure(self, slack_connector):
        """Test authentication failure handling."""
        # Mock failed API response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': False,
            'error': 'invalid_auth'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        slack_connector._session = mock_session
        slack_connector.bot_token = 'invalid-token'

        with pytest.raises(Exception):
            await slack_connector._validate_tokens()

    @pytest.mark.asyncio
    async def test_load_workspace_info(self, slack_connector):
        """Test loading workspace information."""
        # Mock API responses
        mock_session = AsyncMock()

        # Mock team.info response
        team_response = AsyncMock()
        team_response.json.return_value = {
            'ok': True,
            'team': {
                'id': 'T1234567890',
                'name': 'Test Team',
                'domain': 'test-team'
            }
        }
        team_response.raise_for_status.return_value = None

        # Mock conversations.list response
        channels_response = AsyncMock()
        channels_response.json.return_value = {
            'ok': True,
            'channels': [
                {
                    'id': 'C1234567890',
                    'name': 'general',
                    'is_channel': True,
                    'is_private': False
                },
                {
                    'id': 'C0987654321',
                    'name': 'random',
                    'is_channel': True,
                    'is_private': False
                }
            ]
        }
        channels_response.raise_for_status.return_value = None

        # Mock users.list response
        users_response = AsyncMock()
        users_response.json.return_value = {
            'ok': True,
            'members': [
                {
                    'id': 'U1234567890',
                    'name': 'testuser',
                    'real_name': 'Test User',
                    'profile': {
                        'email': 'test@example.com'
                    }
                }
            ]
        }
        users_response.raise_for_status.return_value = None

        # Set up mock session to return different responses for different endpoints
        def mock_post(url, **kwargs):
            if 'team.info' in url:
                return team_response
            elif 'conversations.list' in url:
                return channels_response
            elif 'users.list' in url:
                return users_response
            else:
                return AsyncMock()

        mock_session.post.side_effect = mock_post
        slack_connector._session = mock_session
        slack_connector.bot_token = 'xoxb-test-token'

        await slack_connector._load_workspace_info()

        # Verify team info was loaded
        assert slack_connector._team_info is not None
        assert slack_connector._team_info['name'] == 'Test Team'

        # Verify channels were loaded
        assert len(slack_connector._channels_cache) == 2
        assert 'C1234567890' in slack_connector._channels_cache
        assert slack_connector._channels_cache['C1234567890']['name'] == 'general'

        # Verify users were loaded
        assert len(slack_connector._users_cache) == 1
        assert 'U1234567890' in slack_connector._users_cache
        assert slack_connector._users_cache['U1234567890']['name'] == 'testuser'

    @pytest.mark.asyncio
    async def test_fetch_historical_messages(self, slack_connector, sample_channel_history):
        """Test fetching historical messages."""
        # Disable DM fetching for this test
        slack_connector.include_direct_messages = False

        # Mock API responses
        mock_session = AsyncMock()

        # Mock conversations.list response (channels only)
        channels_response = AsyncMock()
        channels_response.json.return_value = {
            'ok': True,
            'channels': [
                {
                    'id': 'C1234567890',
                    'name': 'general',
                    'is_channel': True
                }
            ]
        }
        channels_response.raise_for_status.return_value = None

        # Mock conversations.history response
        history_response = AsyncMock()
        history_response.json.return_value = sample_channel_history
        history_response.raise_for_status.return_value = None

        def mock_post(url, **kwargs):
            if 'conversations.list' in url:
                return channels_response
            elif 'conversations.history' in url:
                return history_response
            else:
                return AsyncMock()

        mock_session.post.side_effect = mock_post
        slack_connector._session = mock_session
        slack_connector.bot_token = 'xoxb-test-token'

        messages = await slack_connector.fetch_historical_messages(limit=50)

        # Verify messages were fetched
        assert len(messages) == 2
        assert isinstance(messages[0], RawMessage)
        assert messages[0].platform == "slack"
        assert messages[0].platform_message_id == "1234567890.123456"
        assert messages[0].content['text'] == "Hello, world!"

    def test_extract_message_content(self, slack_connector, sample_slack_message):
        """Test message content extraction."""
        content = slack_connector._extract_message_content(
            sample_slack_message)

        assert content['text'] == 'Hello, world!'
        assert 'attachments' in content
        assert isinstance(content['attachments'], list)

    def test_extract_message_content_with_files(self, slack_connector):
        """Test message content extraction with file attachments."""
        message_with_files = {
            'type': 'message',
            'ts': '1234567890.123456',
            'user': 'U1234567890',
            'text': 'Check out this file!',
            'files': [
                {
                    'id': 'F1234567890',
                    'name': 'document.pdf',
                    'mimetype': 'application/pdf',
                    'size': 1024,
                    'url_private': 'https://files.slack.com/files-pri/...',
                    'permalink': 'https://test-team.slack.com/files/...'
                }
            ]
        }

        content = slack_connector._extract_message_content(message_with_files)

        assert content['text'] == 'Check out this file!'
        assert len(content['attachments']) == 1
        assert content['attachments'][0]['id'] == 'F1234567890'
        assert content['attachments'][0]['name'] == 'document.pdf'
        assert content['attachments'][0]['mimetype'] == 'application/pdf'

    def test_extract_timestamp(self, slack_connector, sample_slack_message):
        """Test timestamp extraction from Slack message."""
        timestamp = slack_connector._extract_timestamp(sample_slack_message)

        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == timezone.utc

    def test_extract_timestamp_invalid(self, slack_connector):
        """Test timestamp extraction with invalid timestamp."""
        message_invalid_ts = {
            'type': 'message',
            'ts': 'invalid_timestamp',
            'user': 'U1234567890',
            'text': 'Hello, world!'
        }

        timestamp = slack_connector._extract_timestamp(message_invalid_ts)

        # Should return current time for invalid timestamp
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_handle_slack_event_message(self, slack_connector, sample_slack_message, mock_event_bus):
        """Test handling Slack message event."""
        # Handle the event
        await slack_connector._handle_slack_event(sample_slack_message)

        # Verify event was queued
        assert not slack_connector._processing_queue.empty()

        # Get the queued item to verify its content
        queued_item = await slack_connector._processing_queue.get()
        assert queued_item['type'] == 'message'
        assert queued_item['event'] == sample_slack_message

    @pytest.mark.asyncio
    async def test_handle_slack_event_bot_message(self, slack_connector):
        """Test handling bot message (should be filtered out)."""
        bot_message = {
            'type': 'message',
            'ts': '1234567890.123456',
            'bot_id': 'B1234567890',
            'text': 'This is a bot message',
            'channel': 'C1234567890'
        }

        await slack_connector._handle_slack_event(bot_message)

        # Verify bot message was not queued
        assert slack_connector._processing_queue.empty()

    @pytest.mark.asyncio
    async def test_process_message_event(self, slack_connector, sample_slack_message, mock_event_bus):
        """Test processing a message event."""
        await slack_connector._process_message_event(sample_slack_message)

        # Verify event was published to event bus
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == 'messages.raw'

        event = call_args[0][1]
        assert isinstance(event, Event)
        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.data['platform'] == 'slack'

    @pytest.mark.asyncio
    async def test_webhook_url_verification(self, slack_connector):
        """Test Slack webhook URL verification challenge."""
        challenge_payload = {
            'type': 'url_verification',
            'challenge': 'test_challenge_string'
        }

        result = await slack_connector.handle_webhook(challenge_payload)
        assert result == 'test_challenge_string'

    @pytest.mark.asyncio
    async def test_webhook_event_callback(self, slack_connector, sample_slack_message):
        """Test Slack webhook event callback."""
        event_payload = {
            'type': 'event_callback',
            'event': sample_slack_message
        }

        # Mock the event handling
        with patch.object(slack_connector, '_handle_slack_event') as mock_handle:
            await slack_connector.handle_webhook(event_payload)
            mock_handle.assert_called_once_with(sample_slack_message)

    @pytest.mark.asyncio
    async def test_health_check_success(self, slack_connector):
        """Test successful health check."""
        # Mock successful API response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': True,
            'user': 'test_bot',
            'team': 'Test Team'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        slack_connector._session = mock_session
        slack_connector.bot_token = 'xoxb-test-token'

        await slack_connector._platform_health_check()

        # Should not raise an exception
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, slack_connector):
        """Test health check failure."""
        # Mock failed API response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'ok': False,
            'error': 'invalid_auth'
        }
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        slack_connector._session = mock_session
        slack_connector.bot_token = 'invalid-token'

        with pytest.raises(SlackConnectorError):
            await slack_connector._platform_health_check()

    def test_get_channel_info(self, slack_connector):
        """Test getting channel information from cache."""
        # Add test data to cache
        slack_connector._channels_cache['C1234567890'] = {
            'id': 'C1234567890',
            'name': 'general',
            'is_channel': True
        }

        channel_info = slack_connector.get_channel_info('C1234567890')
        assert channel_info is not None
        assert channel_info['name'] == 'general'

        # Test non-existent channel
        assert slack_connector.get_channel_info('C9999999999') is None

    def test_get_user_info(self, slack_connector):
        """Test getting user information from cache."""
        # Add test data to cache
        slack_connector._users_cache['U1234567890'] = {
            'id': 'U1234567890',
            'name': 'testuser',
            'real_name': 'Test User'
        }

        user_info = slack_connector.get_user_info('U1234567890')
        assert user_info is not None
        assert user_info['name'] == 'testuser'

        # Test non-existent user
        assert slack_connector.get_user_info('U9999999999') is None

    def test_get_team_info(self, slack_connector):
        """Test getting team information."""
        # Set test team info
        slack_connector._team_info = {
            'id': 'T1234567890',
            'name': 'Test Team',
            'domain': 'test-team'
        }

        team_info = slack_connector.get_team_info()
        assert team_info is not None
        assert team_info['name'] == 'Test Team'


class TestSlackConnectorIntegration:
    """Integration tests for SlackConnector."""

    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """Test complete message processing flow."""
        # This would be an integration test that requires actual Slack API access
        # For now, we'll skip it in unit tests
        pytest.skip("Integration test requires actual Slack API access")

    @pytest.mark.asyncio
    async def test_oauth_flow(self):
        """Test OAuth authentication flow."""
        # This would test the complete OAuth flow
        # For now, we'll skip it in unit tests
        pytest.skip("Integration test requires OAuth server setup")
