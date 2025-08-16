"""
Integration tests for Gmail connector with real-time capabilities.

Tests Gmail authentication, message fetching, webhook handling,
and integration with the event bus system.
"""

import asyncio
import json
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from integrations.gmail_connector import GmailConnector, GmailConnectorError
from integrations.base_connector import AuthenticationError, RawMessage
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform


# Test fixtures - available to all test classes
@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Mock configuration for Gmail connector."""
    return {
        'scopes': [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ],
        'credentials_file': 'test_credentials.json',
        'token_file': 'test_token.json',
        'webhook_endpoint': '/webhooks/gmail',
        'webhook_secret': 'test_secret',
        'topic_name': 'projects/test-project/topics/gmail-push',
        'max_results': 50,
        'include_spam_trash': False
    }


@pytest.fixture
def mock_event_bus() -> Mock:
    """Mock event bus for testing."""
    event_bus = Mock(spec=EventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def gmail_connector(mock_config, mock_event_bus) -> GmailConnector:
    """Create Gmail connector instance for testing."""
    return GmailConnector(
        config=mock_config,
        event_bus=mock_event_bus
    )


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service for API calls."""
    service = Mock()

    # Mock users().getProfile()
    profile_mock = Mock()
    profile_mock.execute.return_value = {
        'emailAddress': 'test@example.com',
        'messagesTotal': 100
    }
    service.users().getProfile.return_value = profile_mock

    # Mock users().messages().list()
    messages_list_mock = Mock()
    messages_list_mock.execute.return_value = {
        'messages': [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'}
        ],
        'nextPageToken': 'next_token_123'
    }
    service.users().messages().list.return_value = messages_list_mock

    # Mock users().messages().get()
    message_get_mock = Mock()
    message_get_mock.execute.return_value = {
        'id': 'msg1',
        'threadId': 'thread1',
        'internalDate': '1640995200000',  # 2022-01-01 00:00:00 UTC
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'test@example.com'},
                {'name': 'Subject', 'value': 'Test Subject'}
            ],
            'mimeType': 'text/plain',
            'body': {
                'data': 'VGVzdCBtZXNzYWdlIGNvbnRlbnQ='  # Base64 for "Test message content"
            }
        }
    }
    service.users().messages().get.return_value = message_get_mock

    # Mock users().watch()
    watch_mock = Mock()
    watch_mock.execute.return_value = {
        'historyId': '12345',
        'expiration': '1641081600000'
    }
    service.users().watch.return_value = watch_mock

    # Mock users().stop()
    stop_mock = Mock()
    stop_mock.execute.return_value = {}
    service.users().stop.return_value = stop_mock

    # Mock users().history().list()
    history_mock = Mock()
    history_mock.execute.return_value = {
        'history': [
            {
                'messagesAdded': [
                    {'message': {'id': 'new_msg1'}}
                ]
            }
        ]
    }
    service.users().history().list.return_value = history_mock

    return service


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth credentials."""
    creds = Mock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = 'refresh_token_123'
    creds.to_json.return_value = '{"token": "test_token"}'
    creds.universe_domain = 'googleapis.com'
    return creds


class TestGmailAuthentication:
    """Test Gmail OAuth 2.0 authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_with_existing_valid_credentials(
        self, gmail_connector, mock_credentials, mock_gmail_service
    ):
        """Test authentication with existing valid credentials."""
        with patch('os.path.exists', return_value=True), \
                patch('google.oauth2.credentials.Credentials.from_authorized_user_file',
                      return_value=mock_credentials), \
                patch('googleapiclient.discovery.build', return_value=mock_gmail_service), \
                patch('builtins.open', create=True):

            await gmail_connector.authenticate()

            assert gmail_connector.credentials == mock_credentials
            assert gmail_connector.service == mock_gmail_service

    @pytest.mark.asyncio
    async def test_authenticate_with_expired_credentials(
        self, gmail_connector, mock_credentials, mock_gmail_service
    ):
        """Test authentication with expired credentials that need refresh."""
        mock_credentials.valid = False
        mock_credentials.expired = True

        with patch('os.path.exists', return_value=True), \
                patch('google.oauth2.credentials.Credentials.from_authorized_user_file',
                      return_value=mock_credentials), \
                patch('googleapiclient.discovery.build', return_value=mock_gmail_service), \
                patch('builtins.open', create=True) as mock_open:

            await gmail_connector.authenticate()

            mock_credentials.refresh.assert_called_once()
            assert gmail_connector.credentials == mock_credentials

    @pytest.mark.asyncio
    async def test_authenticate_new_oauth_flow(
        self, gmail_connector, mock_credentials, mock_gmail_service
    ):
        """Test authentication with new OAuth flow."""
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_credentials

        with patch('os.path.exists', side_effect=lambda x: x.endswith('credentials.json')), \
                patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file',
                      return_value=mock_flow), \
                patch('googleapiclient.discovery.build', return_value=mock_gmail_service), \
                patch('builtins.open', create=True) as mock_open:

            await gmail_connector.authenticate()

            mock_flow.run_local_server.assert_called_once_with(port=0)
            assert gmail_connector.credentials == mock_credentials

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials_file(self, gmail_connector):
        """Test authentication failure when credentials file is missing."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(AuthenticationError, match="Credentials file not found"):
                await gmail_connector.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_api_error(self, gmail_connector, mock_credentials):
        """Test authentication failure due to API error."""
        with patch('os.path.exists', return_value=True), \
                patch('google.oauth2.credentials.Credentials.from_authorized_user_file',
                      return_value=mock_credentials), \
                patch('googleapiclient.discovery.build', side_effect=Exception("API Error")):

            with pytest.raises(AuthenticationError, match="Gmail authentication failed"):
                await gmail_connector.authenticate()


class TestGmailMessageFetching:
    """Test Gmail message fetching functionality."""

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_success(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test successful historical message fetching."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        messages = await gmail_connector.fetch_historical_messages(limit=10)

        assert len(messages) == 2
        assert all(isinstance(msg, RawMessage) for msg in messages)
        assert messages[0].platform == "gmail"
        assert messages[0].platform_message_id == "msg1"

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_with_cursor(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test historical message fetching with pagination cursor."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        messages = await gmail_connector.fetch_historical_messages(
            cursor="page_token_123",
            limit=5
        )

        # Verify pageToken was passed to API call
        mock_gmail_service.users().messages().list.assert_called_with(
            userId='me',
            maxResults=5,
            includeSpamTrash=False,
            pageToken="page_token_123"
        )

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_no_service(self, gmail_connector):
        """Test message fetching failure when service is not initialized."""
        with pytest.raises(GmailConnectorError, match="Gmail service not initialized"):
            await gmail_connector.fetch_historical_messages()

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_empty_result(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test message fetching with empty result."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        # Mock empty response
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': []
        }

        messages = await gmail_connector.fetch_historical_messages()

        assert len(messages) == 0

    def test_extract_sender_id(self, gmail_connector):
        """Test sender ID extraction from message headers."""
        message = {
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'John Doe <john@example.com>'},
                    {'name': 'To', 'value': 'test@example.com'}
                ]
            }
        }

        sender_id = gmail_connector._extract_sender_id(message)
        assert sender_id == 'john@example.com'

    def test_extract_content_text(self, gmail_connector):
        """Test content extraction from text message."""
        message = {
            'payload': {
                'mimeType': 'text/plain',
                'body': {
                    'data': 'VGVzdCBtZXNzYWdlIGNvbnRlbnQ='  # Base64 for "Test message content"
                }
            }
        }

        content = gmail_connector._extract_content(message)
        assert content['text'] == 'Test message content'
        assert content['html'] is None

    def test_extract_timestamp(self, gmail_connector):
        """Test timestamp extraction from message."""
        message = {
            'internalDate': '1640995200000'  # 2022-01-01 00:00:00 UTC
        }

        timestamp = gmail_connector._extract_timestamp(message)
        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert timestamp == expected


class TestGmailRealTimeIngestion:
    """Test Gmail real-time ingestion capabilities."""

    @pytest.mark.asyncio
    async def test_start_real_time_ingestion(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test starting real-time ingestion."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        await gmail_connector.start_real_time_ingestion()

        # Verify push notifications were set up
        mock_gmail_service.users().watch.assert_called_once()

        # Verify processor task was started
        assert gmail_connector._processor_task is not None

    @pytest.mark.asyncio
    async def test_stop_real_time_ingestion(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test stopping real-time ingestion."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        # Start first
        await gmail_connector.start_real_time_ingestion()

        # Then stop
        await gmail_connector.stop_real_time_ingestion()

        # Verify push notifications were stopped
        mock_gmail_service.users().stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_valid_payload(
        self, gmail_connector, mock_event_bus
    ):
        """Test handling valid webhook payload."""
        payload = {
            'message': {
                # Base64 for {"historyId": "12345"}
                'data': 'eyJoaXN0b3J5SWQiOiAiMTIzNDUifQ==',
                'messageId': 'msg123',
                'publishTime': '2022-01-01T00:00:00Z'
            }
        }

        await gmail_connector.handle_webhook(payload)

        # Verify message was queued for processing
        assert not gmail_connector._processing_queue.empty()

    @pytest.mark.asyncio
    async def test_handle_webhook_empty_payload(self, gmail_connector):
        """Test handling empty webhook payload."""
        payload = {}

        # Should not raise exception
        await gmail_connector.handle_webhook(payload)

    @pytest.mark.asyncio
    async def test_process_new_message_with_event_bus(
        self, gmail_connector, mock_gmail_service, mock_credentials, mock_event_bus
    ):
        """Test processing new message and publishing to event bus."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials
        gmail_connector.event_bus = mock_event_bus

        await gmail_connector._process_new_message('msg1')

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == 'messages.raw'  # Stream name
        assert call_args[0][1].type == EventType.MESSAGE_RECEIVED


class TestGmailHealthCheck:
    """Test Gmail connector health check functionality."""

    @pytest.mark.asyncio
    async def test_platform_health_check_success(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test successful health check."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        # Should not raise exception
        await gmail_connector._platform_health_check()

    @pytest.mark.asyncio
    async def test_platform_health_check_no_service(self, gmail_connector):
        """Test health check failure when service is not initialized."""
        with pytest.raises(GmailConnectorError, match="Gmail service not initialized"):
            await gmail_connector._platform_health_check()

    @pytest.mark.asyncio
    async def test_platform_health_check_api_error(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test health check failure due to API error."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        # Mock API error
        mock_gmail_service.users().getProfile.return_value.execute.side_effect = Exception("API Error")

        with pytest.raises(GmailConnectorError, match="Health check failed"):
            await gmail_connector._platform_health_check()


class TestGmailUtilityMethods:
    """Test Gmail connector utility methods."""

    def test_get_next_page_token(self, gmail_connector):
        """Test extracting next page token from API response."""
        response = {'nextPageToken': 'token123'}
        token = gmail_connector.get_next_page_token(response)
        assert token == 'token123'

    def test_get_next_page_token_none(self, gmail_connector):
        """Test extracting next page token when none exists."""
        response = {}
        token = gmail_connector.get_next_page_token(response)
        assert token is None

    @pytest.mark.asyncio
    async def test_get_message_count(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test getting total message count."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        count = await gmail_connector.get_message_count()
        assert count == 100

    @pytest.mark.asyncio
    async def test_get_message_count_no_service(self, gmail_connector):
        """Test getting message count when service is not initialized."""
        count = await gmail_connector.get_message_count()
        assert count == 0


class TestGmailIntegration:
    """Integration tests for Gmail connector with other system components."""

    @pytest.mark.asyncio
    async def test_full_message_processing_flow(
        self, gmail_connector, mock_gmail_service, mock_credentials, mock_event_bus
    ):
        """Test complete message processing flow from fetch to event publishing."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials
        gmail_connector.event_bus = mock_event_bus

        # Fetch messages
        messages = await gmail_connector.fetch_historical_messages(limit=2)

        # Verify messages were fetched
        assert len(messages) == 2

        # Process a new message (simulating webhook)
        await gmail_connector._process_new_message('new_msg1')

        # Verify event was published
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_connector_lifecycle(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test complete connector lifecycle: authenticate -> start -> stop."""
        with patch('os.path.exists', return_value=True), \
                patch('google.oauth2.credentials.Credentials.from_authorized_user_file',
                      return_value=mock_credentials), \
                patch('googleapiclient.discovery.build', return_value=mock_gmail_service), \
                patch('builtins.open', create=True):

            # Authenticate
            await gmail_connector.authenticate()
            assert gmail_connector.service is not None

            # Start real-time ingestion
            await gmail_connector.start_real_time_ingestion()
            assert gmail_connector._processor_task is not None

            # Stop real-time ingestion
            await gmail_connector.stop_real_time_ingestion()
            assert gmail_connector._processor_task is None

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self, gmail_connector, mock_gmail_service, mock_credentials
    ):
        """Test error handling and recovery mechanisms."""
        gmail_connector.service = mock_gmail_service
        gmail_connector.credentials = mock_credentials

        # Mock API error for one call, then success
        mock_gmail_service.users().messages().get.return_value.execute.side_effect = [
            Exception("Temporary API error"),
            {
                'id': 'msg1',
                'threadId': 'thread1',
                'internalDate': '1640995200000',
                'payload': {
                    'headers': [{'name': 'From', 'value': 'test@example.com'}],
                    'mimeType': 'text/plain',
                    'body': {'data': 'VGVzdA=='}
                }
            }
        ]

        # Should handle error gracefully and continue processing
        messages = await gmail_connector.fetch_historical_messages(limit=2)

        # Should get one successful message (the second call)
        assert len(messages) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
