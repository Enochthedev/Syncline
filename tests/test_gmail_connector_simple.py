"""
Simplified Gmail connector tests focusing on core functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from integrations.gmail_connector import GmailConnector, GmailConnectorError
from integrations.base_connector import RawMessage
from services.event_bus import EventBus


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Mock configuration for Gmail connector."""
    return {
        'scopes': ['https://www.googleapis.com/auth/gmail.readonly'],
        'credentials_file': 'test_credentials.json',
        'token_file': 'test_token.json',
        'webhook_endpoint': '/webhooks/gmail',
        'max_results': 50,
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


class TestGmailConnectorCore:
    """Test core Gmail connector functionality."""

    def test_initialization(self, gmail_connector):
        """Test Gmail connector initialization."""
        assert gmail_connector.platform == "gmail"
        assert gmail_connector.scopes == [
            'https://www.googleapis.com/auth/gmail.readonly']
        assert gmail_connector.credentials_file == 'test_credentials.json'
        assert gmail_connector.token_file == 'test_token.json'

    def test_extract_sender_id_with_name_and_email(self, gmail_connector):
        """Test sender ID extraction from message headers with name and email."""
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

    def test_extract_sender_id_email_only(self, gmail_connector):
        """Test sender ID extraction with email only."""
        message = {
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'john@example.com'},
                ]
            }
        }

        sender_id = gmail_connector._extract_sender_id(message)
        assert sender_id == 'john@example.com'

    def test_extract_sender_id_no_from_header(self, gmail_connector):
        """Test sender ID extraction when no From header exists."""
        message = {
            'payload': {
                'headers': [
                    {'name': 'To', 'value': 'test@example.com'}
                ]
            }
        }

        sender_id = gmail_connector._extract_sender_id(message)
        assert sender_id == 'unknown'

    def test_extract_content_text_plain(self, gmail_connector):
        """Test content extraction from plain text message."""
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
        assert len(content['attachments']) == 0

    def test_extract_content_html(self, gmail_connector):
        """Test content extraction from HTML message."""
        message = {
            'payload': {
                'mimeType': 'text/html',
                'body': {
                    'data': 'PGI+VGVzdCBIVE1MPC9iPg=='  # Base64 for "<b>Test HTML</b>"
                }
            }
        }

        content = gmail_connector._extract_content(message)
        assert content['html'] == '<b>Test HTML</b>'
        assert content['text'] is None

    def test_extract_content_multipart(self, gmail_connector):
        """Test content extraction from multipart message."""
        message = {
            'payload': {
                'mimeType': 'multipart/alternative',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': 'VGVzdCB0ZXh0'  # Base64 for "Test text"
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': 'PGI+VGVzdCBIVE1MPC9iPg=='  # Base64 for "<b>Test HTML</b>"
                        }
                    }
                ]
            }
        }

        content = gmail_connector._extract_content(message)
        assert content['text'] == 'Test text'
        assert content['html'] == '<b>Test HTML</b>'

    def test_extract_content_with_attachment(self, gmail_connector):
        """Test content extraction with attachment."""
        message = {
            'payload': {
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': 'VGVzdCB0ZXh0'  # Base64 for "Test text"
                        }
                    },
                    {
                        'mimeType': 'application/pdf',
                        'filename': 'document.pdf',
                        'body': {
                            'attachmentId': 'attachment123',
                            'size': 12345
                        }
                    }
                ]
            }
        }

        content = gmail_connector._extract_content(message)
        assert content['text'] == 'Test text'
        assert len(content['attachments']) == 1
        assert content['attachments'][0]['filename'] == 'document.pdf'
        assert content['attachments'][0]['mime_type'] == 'application/pdf'
        assert content['attachments'][0]['attachment_id'] == 'attachment123'

    def test_extract_timestamp_with_internal_date(self, gmail_connector):
        """Test timestamp extraction from internal date."""
        message = {
            'internalDate': '1640995200000'  # 2022-01-01 00:00:00 UTC
        }

        timestamp = gmail_connector._extract_timestamp(message)
        expected = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert timestamp == expected

    def test_extract_timestamp_no_internal_date(self, gmail_connector):
        """Test timestamp extraction when no internal date exists."""
        message = {}

        timestamp = gmail_connector._extract_timestamp(message)
        # Should return current time, so just check it's a datetime with timezone
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None

    def test_get_next_page_token_exists(self, gmail_connector):
        """Test extracting next page token when it exists."""
        response = {'nextPageToken': 'token123'}
        token = gmail_connector.get_next_page_token(response)
        assert token == 'token123'

    def test_get_next_page_token_none(self, gmail_connector):
        """Test extracting next page token when it doesn't exist."""
        response = {}
        token = gmail_connector.get_next_page_token(response)
        assert token is None

    @pytest.mark.asyncio
    async def test_get_message_count_no_service(self, gmail_connector):
        """Test getting message count when service is not initialized."""
        count = await gmail_connector.get_message_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_no_service(self, gmail_connector):
        """Test message fetching failure when service is not initialized."""
        with pytest.raises(GmailConnectorError, match="Gmail service not initialized"):
            await gmail_connector.fetch_historical_messages()

    @pytest.mark.asyncio
    async def test_platform_health_check_no_service(self, gmail_connector):
        """Test health check failure when service is not initialized."""
        with pytest.raises(GmailConnectorError, match="Gmail service not initialized"):
            await gmail_connector._platform_health_check()

    @pytest.mark.asyncio
    async def test_handle_webhook_empty_payload(self, gmail_connector):
        """Test handling empty webhook payload."""
        payload = {}

        # Should not raise exception
        await gmail_connector.handle_webhook(payload)

    @pytest.mark.asyncio
    async def test_handle_webhook_valid_payload(self, gmail_connector):
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
    async def test_handle_webhook_invalid_base64(self, gmail_connector):
        """Test handling webhook with invalid base64 data."""
        payload = {
            'message': {
                'data': 'invalid_base64_data',
                'messageId': 'msg123'
            }
        }

        # Should handle gracefully without raising exception
        await gmail_connector.handle_webhook(payload)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
