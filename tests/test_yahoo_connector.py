"""
Comprehensive tests for Yahoo Mail connector.
"""

import pytest
import asyncio
import email
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from integrations.yahoo_connector import YahooConnector, YahooCredentials
from integrations.yahoo_factory import YahooConnectorFactory
from integrations.base_connector import ConnectorStatus
from services.event_bus import EventBus
from services.message_schema import RawMessage, MessageContent, Participant, Attachment
from config.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    return settings


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    event_bus = Mock(spec=EventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def yahoo_credentials():
    """Test Yahoo credentials."""
    return YahooCredentials(
        email="test@yahoo.com",
        app_password="test_app_password"
    )


@pytest.fixture
def sample_email_message():
    """Sample email message for testing."""
    msg = email.message.EmailMessage()
    msg['From'] = 'sender@example.com'
    msg['To'] = 'test@yahoo.com'
    msg['Subject'] = 'Test Subject'
    msg['Date'] = 'Mon, 15 Jan 2024 10:30:00 +0000'
    msg['Message-ID'] = '<test123@example.com>'
    msg.set_content('This is a test message.')
    return msg


class TestYahooCredentials:
    """Test Yahoo credentials dataclass."""

    def test_credentials_creation(self):
        """Test creating Yahoo credentials."""
        creds = YahooCredentials(
            email="test@yahoo.com",
            app_password="password123"
        )

        assert creds.email == "test@yahoo.com"
        assert creds.app_password == "password123"
        assert creds.imap_server == "imap.mail.yahoo.com"
        assert creds.imap_port == 993

    def test_credentials_with_custom_server(self):
        """Test creating credentials with custom server settings."""
        creds = YahooCredentials(
            email="test@yahoo.com",
            app_password="password123",
            imap_server="custom.imap.server.com",
            imap_port=143
        )

        assert creds.imap_server == "custom.imap.server.com"
        assert creds.imap_port == 143


class TestYahooConnector:
    """Test Yahoo Mail connector."""

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_authentication_success(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test successful authentication."""
        # Mock IMAP client
        mock_client = Mock()
        mock_client.login.return_value = None
        mock_client.logout.return_value = None
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Test authentication
        result = await connector.authenticate({
            "email": "test@yahoo.com",
            "app_password": "test_password"
        })

        assert result is True
        assert connector.status == ConnectorStatus.CONNECTED
        mock_client.login.assert_called_once()
        mock_client.logout.assert_called_once()

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_authentication_failure(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test authentication failure."""
        # Mock IMAP client to raise exception
        mock_imap_class.side_effect = Exception("Authentication failed")

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Test authentication
        result = await connector.authenticate({
            "email": "test@yahoo.com",
            "app_password": "wrong_password"
        })

        assert result is False
        assert connector.status == ConnectorStatus.ERROR
        assert "Authentication failed" in connector.last_error

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_fetch_message_success(self, mock_imap_class, mock_event_bus, mock_settings, sample_email_message):
        """Test successful message fetching."""
        # Mock IMAP client
        mock_client = Mock()
        mock_client.fetch.return_value = (
            'OK', [(b'1', sample_email_message.as_bytes())])
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)
        connector.imap_client = mock_client

        # Test message fetching
        raw_message = await connector._fetch_message("1")

        assert raw_message is not None
        assert raw_message.platform == "yahoo"
        assert raw_message.platform_message_id == "1"
        assert raw_message.sender.email == "sender@example.com"
        assert raw_message.content.text == "This is a test message."
        assert raw_message.metadata["subject"] == "Test Subject"

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_fetch_message_with_attachments(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test fetching message with attachments."""
        # Create multipart message with attachment
        msg = email.message.EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'test@yahoo.com'
        msg['Subject'] = 'Message with attachment'
        msg['Date'] = 'Mon, 15 Jan 2024 10:30:00 +0000'

        # Add text content
        msg.set_content('Message with attachment.')

        # Add attachment
        attachment_data = b'This is attachment content'
        msg.add_attachment(attachment_data,
                           maintype='application',
                           subtype='octet-stream',
                           filename='test.txt')

        # Mock IMAP client
        mock_client = Mock()
        mock_client.fetch.return_value = ('OK', [(b'1', msg.as_bytes())])
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)
        connector.imap_client = mock_client

        # Test message fetching
        raw_message = await connector._fetch_message("1")

        assert raw_message is not None
        assert len(raw_message.attachments) == 1
        assert raw_message.attachments[0].filename == 'test.txt'
        assert raw_message.attachments[0].size > 0

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_poll_messages(self, mock_imap_class, mock_event_bus, mock_settings, sample_email_message):
        """Test polling for new messages."""
        # Mock IMAP client
        mock_client = Mock()
        mock_client.select.return_value = ('OK', [b'1'])
        mock_client.search.return_value = ('OK', [b'1 2 3'])
        mock_client.fetch.return_value = (
            'OK', [(b'1', sample_email_message.as_bytes())])
        mock_client.logout.return_value = None
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Test polling
        await connector._poll_messages()

        # Verify event bus was called for each message
        assert mock_event_bus.publish.call_count == 3
        mock_event_bus.publish.assert_called_with("MESSAGE_RECEIVED", {
            "platform": "yahoo",
            "message": pytest.any(dict)
        })

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_fetch_historical_messages(self, mock_imap_class, mock_event_bus, mock_settings, sample_email_message):
        """Test fetching historical messages."""
        # Mock IMAP client
        mock_client = Mock()
        mock_client.select.return_value = ('OK', [b'1'])
        mock_client.search.return_value = ('OK', [b'1 2 3 4 5'])
        mock_client.fetch.return_value = (
            'OK', [(b'1', sample_email_message.as_bytes())])
        mock_client.logout.return_value = None
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Test historical fetch with limit
        messages = await connector.fetch_historical_messages(cursor="0", limit=3)

        assert len(messages) == 3
        for message in messages:
            assert isinstance(message, RawMessage)
            assert message.platform == "yahoo"

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_start_stop_real_time_ingestion(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test starting and stopping real-time ingestion."""
        # Mock IMAP client
        mock_client = Mock()
        mock_client.select.return_value = ('OK', [b'1'])
        mock_client.search.return_value = ('OK', [b''])
        mock_client.logout.return_value = None
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)
        connector.polling_interval = 0.1  # Fast polling for test

        # Start ingestion in background
        ingestion_task = asyncio.create_task(
            connector.start_real_time_ingestion())

        # Let it run briefly
        await asyncio.sleep(0.2)

        # Stop ingestion
        await connector.stop_real_time_ingestion()

        # Wait for task to complete
        try:
            await asyncio.wait_for(ingestion_task, timeout=1.0)
        except asyncio.TimeoutError:
            ingestion_task.cancel()

        assert connector.status == ConnectorStatus.CONNECTED
        assert not connector._running

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_health_check_healthy(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test health check when connector is healthy."""
        # Mock IMAP client
        mock_client = Mock()
        mock_client.login.return_value = None
        mock_client.logout.return_value = None
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Test health check
        health = await connector.get_health_status()

        assert health.status == ConnectorStatus.CONNECTED
        assert "healthy" in health.message.lower()
        assert health.details["email"] == "test@yahoo.com"

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_health_check_unhealthy(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test health check when connector is unhealthy."""
        # Mock IMAP client to raise exception
        mock_imap_class.side_effect = Exception("Connection failed")

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Test health check
        health = await connector.get_health_status()

        assert health.status == ConnectorStatus.ERROR
        assert "error" in health.message.lower()
        assert "Connection failed" in health.details["error"]

    @pytest.mark.asyncio
    async def test_handle_webhook_not_supported(self, mock_event_bus, mock_settings):
        """Test that webhook handling is not supported."""
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        # Should not raise exception, just log warning
        await connector.handle_webhook({"test": "data"})

    def test_connector_initialization(self, mock_event_bus, mock_settings):
        """Test connector initialization."""
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)

        assert connector.platform == "yahoo"
        assert connector.credentials.email == "test@yahoo.com"
        assert connector.last_uid == 0
        assert connector.polling_interval == 30
        assert not connector._running


class TestYahooConnectorFactory:
    """Test Yahoo connector factory."""

    @pytest.mark.asyncio
    @patch('integrations.yahoo_connector.YahooConnector.authenticate')
    async def test_create_connector_success(self, mock_auth, mock_event_bus, mock_settings):
        """Test successful connector creation."""
        mock_auth.return_value = True

        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        credentials = {
            "email": "test@yahoo.com",
            "app_password": "test_password"
        }

        connector = await factory.create_connector(credentials)

        assert connector is not None
        assert connector.credentials.email == "test@yahoo.com"
        mock_auth.assert_called_once()

    @pytest.mark.asyncio
    @patch('integrations.yahoo_connector.YahooConnector.authenticate')
    async def test_create_connector_auth_failure(self, mock_auth, mock_event_bus, mock_settings):
        """Test connector creation with authentication failure."""
        mock_auth.return_value = False

        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        credentials = {
            "email": "test@yahoo.com",
            "app_password": "wrong_password"
        }

        connector = await factory.create_connector(credentials)

        assert connector is None

    @pytest.mark.asyncio
    async def test_create_connector_missing_credentials(self, mock_event_bus, mock_settings):
        """Test connector creation with missing credentials."""
        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        credentials = {
            "email": "test@yahoo.com"
            # Missing app_password
        }

        connector = await factory.create_connector(credentials)

        assert connector is None

    @pytest.mark.asyncio
    @patch('integrations.yahoo_connector.YahooConnector.authenticate')
    async def test_create_connector_with_custom_settings(self, mock_auth, mock_event_bus, mock_settings):
        """Test connector creation with custom IMAP settings."""
        mock_auth.return_value = True

        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        credentials = {
            "email": "test@yahoo.com",
            "app_password": "test_password",
            "imap_server": "custom.imap.server.com",
            "imap_port": 143
        }

        connector = await factory.create_connector(credentials)

        assert connector is not None
        assert connector.credentials.imap_server == "custom.imap.server.com"
        assert connector.credentials.imap_port == 143

    def test_get_required_credentials(self, mock_event_bus, mock_settings):
        """Test getting required credentials."""
        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        creds = factory.get_required_credentials()

        assert "email" in creds
        assert "app_password" in creds
        assert "imap_server" in creds
        assert "imap_port" in creds

    def test_get_setup_instructions(self, mock_event_bus, mock_settings):
        """Test getting setup instructions."""
        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        instructions = factory.get_setup_instructions()

        assert "2-factor authentication" in instructions
        assert "app-specific password" in instructions
        assert "IMAP polling" in instructions


class TestYahooConnectorIntegration:
    """Integration tests for Yahoo connector."""

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_end_to_end_message_processing(self, mock_imap_class, mock_event_bus, mock_settings, sample_email_message):
        """Test end-to-end message processing flow."""
        # Mock IMAP client for full flow
        mock_client = Mock()
        mock_client.login.return_value = None
        mock_client.logout.return_value = None
        mock_client.select.return_value = ('OK', [b'1'])
        mock_client.search.return_value = ('OK', [b'1'])
        mock_client.fetch.return_value = (
            'OK', [(b'1', sample_email_message.as_bytes())])
        mock_imap_class.return_value = mock_client

        # Create factory and connector
        factory = YahooConnectorFactory(mock_event_bus, mock_settings)

        credentials = {
            "email": "test@yahoo.com",
            "app_password": "test_password"
        }

        # Create connector
        connector = await factory.create_connector(credentials)
        assert connector is not None

        # Test message polling
        await connector._poll_messages()

        # Verify message was published to event bus
        mock_event_bus.publish.assert_called_once_with("MESSAGE_RECEIVED", {
            "platform": "yahoo",
            "message": pytest.any(dict)
        })

        # Verify message content
        call_args = mock_event_bus.publish.call_args[0][1]
        message_data = call_args["message"]
        assert message_data["platform"] == "yahoo"
        assert message_data["sender"]["email"] == "sender@example.com"

    @pytest.mark.asyncio
    @patch('imaplib.IMAP4_SSL')
    async def test_error_recovery(self, mock_imap_class, mock_event_bus, mock_settings):
        """Test error recovery during polling."""
        # Mock IMAP client to fail first, then succeed
        mock_client = Mock()
        mock_client.login.return_value = None
        mock_client.logout.return_value = None
        mock_client.select.side_effect = [
            Exception("Temporary failure"), ('OK', [b'1'])]
        mock_client.search.return_value = ('OK', [b''])
        mock_imap_class.return_value = mock_client

        # Create connector
        creds = YahooCredentials(
            email="test@yahoo.com", app_password="test_pass")
        connector = YahooConnector(creds, mock_event_bus, mock_settings)
        connector.polling_interval = 0.1

        # First poll should fail
        await connector._poll_messages()

        # Second poll should succeed
        await connector._poll_messages()

        # Verify both attempts were made
        assert mock_client.select.call_count == 2
