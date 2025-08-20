"""
Tests for Twitter connector with OAuth 2.0 authentication and DM ingestion.

This module contains comprehensive tests for the Twitter connector including
authentication, message fetching, webhook handling, and integration scenarios.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.twitter_connector import TwitterConnector, TwitterConnectorError
from integrations.twitter_factory import TwitterConnectorFactory
from integrations.base_connector import RawMessage, AuthenticationError, RateLimitError
from services.event_bus import EventBus, Event, EventType


class TestTwitterConnector:
    """Test cases for TwitterConnector."""

    @pytest.fixture
    def twitter_config(self) -> Dict[str, Any]:
        """Twitter connector configuration for testing."""
        return {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'bearer_token': 'test_bearer_token',
            'access_token': 'test_access_token',
            'access_token_secret': 'test_access_token_secret',
            'webhook_secret': 'test_webhook_secret',
            'webhook_url': 'https://example.com/webhooks/twitter',
            'max_results': 50,
            'scopes': ['dm.read', 'dm.write', 'users.read']
        }

    @pytest.fixture
    def mock_event_bus(self) -> AsyncMock:
        """Mock event bus for testing."""
        return AsyncMock(spec=EventBus)

    @pytest.fixture
    def twitter_connector(self, twitter_config, mock_event_bus) -> TwitterConnector:
        """Twitter connector instance for testing."""
        return TwitterConnector(
            config=twitter_config,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def sample_dm_event(self) -> Dict[str, Any]:
        """Sample DM event from Twitter API."""
        return {
            'id': '1234567890',
            'text': 'Hello, this is a test DM!',
            'created_at': '2024-01-15T10:30:00.000Z',
            'sender_id': '987654321',
            'event_type': 'MessageCreate',
            'attachments': {
                'media_keys': ['3_1234567890']
            }
        }

    @pytest.fixture
    def sample_includes(self) -> Dict[str, Any]:
        """Sample includes data from Twitter API."""
        return {
            'users': [
                {
                    'id': '987654321',
                    'username': 'testuser',
                    'name': 'Test User',
                    'profile_image_url': 'https://example.com/avatar.jpg'
                }
            ],
            'media': [
                {
                    'media_key': '3_1234567890',
                    'type': 'photo',
                    'url': 'https://example.com/photo.jpg',
                    'width': 800,
                    'height': 600
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_connector_initialization(self, twitter_config, mock_event_bus):
        """Test Twitter connector initialization."""
        connector = TwitterConnector(
            config=twitter_config,
            event_bus=mock_event_bus
        )

        assert connector.platform == "twitter"
        assert connector.client_id == "test_client_id"
        assert connector.client_secret == "test_client_secret"
        assert connector.api_key == "test_api_key"
        assert connector.bearer_token == "test_bearer_token"
        assert connector.max_results == 50
        assert connector.event_bus == mock_event_bus
        assert 'dm.read' in connector.scopes

    @pytest.mark.asyncio
    async def test_authentication_with_existing_tokens(self, twitter_connector):
        """Test authentication with existing valid tokens."""
        # Mock token manager
        mock_token_manager = AsyncMock()
        mock_token_info = MagicMock()
        mock_token_info.is_expired.return_value = False
        mock_token_info.access_token = "valid_access_token"
        mock_token_info.refresh_token = "valid_refresh_token"
        mock_token_manager.get_token.return_value = mock_token_info
        twitter_connector.token_manager = mock_token_manager

        # Mock helper methods
        with patch.object(twitter_connector, '_initialize_clients') as mock_init, \
                patch.object(twitter_connector, '_validate_tokens') as mock_validate:

            await twitter_connector.authenticate()

            mock_token_manager.get_token.assert_called_once_with("twitter")
            mock_init.assert_called_once()
            mock_validate.assert_called_once()
            assert twitter_connector.access_token == "valid_access_token"
            assert twitter_connector.refresh_token == "valid_refresh_token"

    @pytest.mark.asyncio
    async def test_authentication_missing_credentials(self, twitter_config, mock_event_bus):
        """Test authentication failure with missing credentials."""
        # Remove required credentials
        del twitter_config['client_id']

        connector = TwitterConnector(
            config=twitter_config,
            event_bus=mock_event_bus
        )

        with pytest.raises(AuthenticationError, match="client_id and client_secret are required"):
            await connector.authenticate()

    @pytest.mark.asyncio
    async def test_start_real_time_ingestion(self, twitter_connector):
        """Test starting real-time ingestion."""
        with patch.object(twitter_connector, '_load_user_info') as mock_load_user, \
                patch.object(twitter_connector, '_setup_webhooks') as mock_setup_webhooks, \
                patch('asyncio.create_task') as mock_create_task:

            await twitter_connector.start_real_time_ingestion()

            mock_load_user.assert_called_once()
            mock_setup_webhooks.assert_called_once()
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_success(self, twitter_connector, sample_dm_event, sample_includes):
        """Test successful historical message fetching."""
        # Mock async client
        twitter_connector.async_client = AsyncMock()

        # Mock API response
        api_response = {
            'data': [sample_dm_event],
            'includes': sample_includes,
            'meta': {
                'result_count': 1,
                'next_token': 'next_page_token'
            }
        }

        with patch.object(twitter_connector, '_check_dm_rate_limits') as mock_rate_check, \
                patch.object(twitter_connector, '_make_twitter_api_call', return_value=api_response) as mock_api_call, \
                patch.object(twitter_connector, '_process_dm_event') as mock_process:

            # Mock processed message
            mock_raw_message = RawMessage(
                id="twitter_dm_1234567890",
                platform="twitter",
                platform_message_id="1234567890",
                thread_id="twitter_dm_123_456",
                sender_id="987654321",
                content={'text': 'Hello, this is a test DM!'},
                timestamp=datetime.now(timezone.utc)
            )
            mock_process.return_value = mock_raw_message

            messages = await twitter_connector.fetch_historical_messages(limit=50)

            mock_rate_check.assert_called_once()
            mock_api_call.assert_called_once()
            mock_process.assert_called_once_with(
                sample_dm_event, sample_includes)

            assert len(messages) == 1
            assert messages[0].id == "twitter_dm_1234567890"
            assert messages[0].platform == "twitter"

    @pytest.mark.asyncio
    async def test_handle_webhook_direct_message(self, twitter_connector):
        """Test webhook handling for direct messages."""
        webhook_payload = {
            'direct_message_events': [
                {
                    'id': '1234567890',
                    'text': 'Webhook DM test',
                    'sender_id': '987654321',
                    'created_at': '2024-01-15T10:30:00.000Z'
                }
            ]
        }

        with patch.object(twitter_connector, '_validate_webhook_signature') as mock_validate:
            await twitter_connector.handle_webhook(webhook_payload)

            mock_validate.assert_called_once_with(webhook_payload)

            # Check that message was queued
            assert not twitter_connector._processing_queue.empty()
            queued_item = await twitter_connector._processing_queue.get()
            assert queued_item['type'] == 'direct_message'
            assert queued_item['event']['id'] == '1234567890'

    @pytest.mark.asyncio
    async def test_process_dm_event(self, twitter_connector, sample_dm_event, sample_includes):
        """Test processing DM event into RawMessage."""
        twitter_connector._authenticated_user = {'id': '123456789'}

        raw_message = await twitter_connector._process_dm_event(sample_dm_event, sample_includes)

        assert raw_message is not None
        assert raw_message.id == "twitter_dm_1234567890"
        assert raw_message.platform == "twitter"
        assert raw_message.platform_message_id == "1234567890"
        assert raw_message.sender_id == "987654321"
        assert raw_message.content['text'] == "Hello, this is a test DM!"

    @pytest.mark.asyncio
    async def test_platform_health_check_success(self, twitter_connector):
        """Test successful platform health check."""
        mock_client = AsyncMock()
        mock_me_response = MagicMock()
        mock_me_response.data.username = "testuser"
        mock_client.get_me.return_value = mock_me_response
        twitter_connector.async_client = mock_client

        # Should not raise exception
        await twitter_connector._platform_health_check()

        mock_client.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_direct_message_success(self, twitter_connector):
        """Test successful direct message sending."""
        # Mock async client
        twitter_connector.async_client = AsyncMock()

        api_response = {
            'data': {
                'dm_event_id': '1234567890',
                'dm_conversation_id': 'conversation_123'
            }
        }

        with patch.object(twitter_connector, '_make_twitter_api_call', return_value=api_response) as mock_api_call:
            message_id = await twitter_connector.send_direct_message(
                recipient_id="987654321",
                text="Test message",
                media_id="media_123"
            )

            assert message_id == "1234567890"
            mock_api_call.assert_called_once()

    def test_get_next_page_token(self, twitter_connector):
        """Test extracting next page token from API response."""
        response = {
            'data': [],
            'meta': {
                'result_count': 0,
                'next_token': 'next_page_token_123'
            }
        }

        token = twitter_connector.get_next_page_token(response)
        assert token == 'next_page_token_123'


class TestTwitterConnectorFactory:
    """Test cases for TwitterConnectorFactory."""

    def test_create_connector_success(self):
        """Test successful connector creation."""
        config = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret'
        }

        connector = TwitterConnectorFactory.create_connector(config)

        assert isinstance(connector, TwitterConnector)
        assert connector.client_id == 'test_client_id'
        assert connector.client_secret == 'test_client_secret'

    def test_create_connector_missing_config(self):
        """Test connector creation with missing configuration."""
        config = {
            'client_id': 'test_client_id'
            # Missing client_secret
        }

        with pytest.raises(ValueError, match="Missing required Twitter configuration"):
            TwitterConnectorFactory.create_connector(config)

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'max_results': '50',
            'rate_limit_requests': '200'
        }

        validated = TwitterConnectorFactory.validate_config(config)

        assert validated['client_id'] == 'test_client_id'
        assert validated['max_results'] == 50  # Converted to int
        assert validated['rate_limit_requests'] == 200
        assert 'scopes' in validated  # Default added
        assert 'redirect_uri' in validated  # Default added

    def test_validate_config_missing_required(self):
        """Test configuration validation with missing required fields."""
        config = {
            'client_secret': 'test_client_secret'
            # Missing client_id
        }

        with pytest.raises(ValueError, match="Missing required field: client_id"):
            TwitterConnectorFactory.validate_config(config)
