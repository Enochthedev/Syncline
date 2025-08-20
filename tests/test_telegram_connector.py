"""
Tests for Telegram connector functionality.

This module contains unit and integration tests for the Telegram connector,
including authentication, message processing, webhook handling, and error scenarios.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from telegram import Bot, Update, Message as TelegramMessage, User, Chat
from telegram.error import TelegramError, BadRequest, Forbidden

from integrations.telegram_connector import TelegramConnector, TelegramConnectorError, TelegramWebhookError
from integrations.base_connector import AuthenticationError, RawMessage
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform


class TestTelegramConnector:
    """Test cases for TelegramConnector."""

    @pytest.fixture
    def telegram_config(self):
        """Telegram connector configuration for testing."""
        return {
            'bot_token': 'test_bot_token_123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'webhook_url': 'https://example.com',
            'webhook_secret': 'test_webhook_secret',
            'webhook_path': '/webhooks/telegram',
            'allowed_updates': ['message', 'edited_message'],
            'drop_pending_updates': True,
            'max_messages_per_request': 50,
            'include_private_chats': True,
            'include_group_chats': True,
            'include_channels': False
        }

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus for testing."""
        event_bus = AsyncMock(spec=EventBus)
        return event_bus

    @pytest.fixture
    def telegram_connector(self, telegram_config, mock_event_bus):
        """Create TelegramConnector instance for testing."""
        return TelegramConnector(
            config=telegram_config,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def mock_bot_info(self):
        """Mock bot information."""
        bot_info = MagicMock()
        bot_info.id = 123456789
        bot_info.username = 'test_bot'
        bot_info.first_name = 'Test Bot'
        bot_info.is_bot = True
        bot_info.can_join_groups = True
        bot_info.can_read_all_group_messages = False
        bot_info.supports_inline_queries = False
        return bot_info

    @pytest.fixture
    def mock_telegram_message(self):
        """Mock Telegram message."""
        user = MagicMock(spec=User)
        user.id = 987654321
        user.username = 'test_user'
        user.first_name = 'Test'
        user.last_name = 'User'
        user.is_bot = False

        chat = MagicMock(spec=Chat)
        chat.id = 123456789
        chat.type = 'private'
        chat.title = None
        chat.username = 'test_user'

        message = MagicMock(spec=TelegramMessage)
        message.message_id = 1
        message.from_user = user
        message.chat = chat
        message.date = datetime.now(timezone.utc)
        message.text = 'Hello, world!'
        message.caption = None
        message.entities = []
        message.photo = None
        message.document = None
        message.audio = None
        message.video = None
        message.voice = None
        message.video_note = None
        message.sticker = None
        message.location = None
        message.contact = None
        message.reply_to_message = None
        message.forward_from = None
        message.forward_from_chat = None
        message.forward_date = None
        message.forward_from_message_id = None
        message.forward_signature = None
        message.edit_date = None
        message.via_bot = None
        message.message_thread_id = None
        message.to_dict.return_value = {
            'message_id': 1,
            'from': user,
            'chat': chat,
            'date': message.date.timestamp(),
            'text': 'Hello, world!'
        }
        return message

    @pytest.fixture
    def mock_telegram_update(self, mock_telegram_message):
        """Mock Telegram update."""
        update = MagicMock(spec=Update)
        update.update_id = 1
        update.message = mock_telegram_message
        update.edited_message = None
        update.channel_post = None
        update.edited_channel_post = None
        return update

    @pytest.mark.asyncio
    async def test_authentication_success(self, telegram_connector, mock_bot_info):
        """Test successful Telegram authentication."""
        with patch('integrations.telegram_connector.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot_class.return_value = mock_bot

            with patch('integrations.telegram_connector.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()

                assert telegram_connector.bot is not None
                assert telegram_connector.application is not None
                assert telegram_connector._bot_info['username'] == 'test_bot'
                mock_bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_invalid_token(self, telegram_connector):
        """Test authentication with invalid token."""
        with patch('integrations.telegram_connector.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.side_effect = TelegramError("Unauthorized")
            mock_bot_class.return_value = mock_bot

            with pytest.raises(AuthenticationError, match="Invalid Telegram bot token"):
                await telegram_connector.authenticate()

    @pytest.mark.asyncio
    async def test_authentication_missing_token(self):
        """Test authentication with missing token."""
        config = {'webhook_url': 'https://example.com'}
        connector = TelegramConnector(config=config)

        with pytest.raises(AuthenticationError, match="Telegram bot token is required"):
            await connector.authenticate()

    @pytest.mark.asyncio
    async def test_start_real_time_ingestion_webhook(self, telegram_connector, mock_bot_info):
        """Test starting real-time ingestion with webhook."""
        with patch('integrations.telegram_connector.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot.set_webhook.return_value = True
            mock_bot_class.return_value = mock_bot

            with patch('integrations.telegram_connector.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                await telegram_connector.start_real_time_ingestion()

                assert telegram_connector._processor_task is not None
                assert telegram_connector._webhook_configured is True
                mock_bot.set_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_real_time_ingestion_polling(self, telegram_config, mock_event_bus, mock_bot_info):
        """Test starting real-time ingestion with polling."""
        # Remove webhook URL to force polling
        config = telegram_config.copy()
        del config['webhook_url']

        connector = TelegramConnector(config=config, event_bus=mock_event_bus)

        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await connector.authenticate()
                await connector.start_real_time_ingestion()

                assert connector._processor_task is not None
                assert connector._polling_task is not None
                assert not connector._webhook_configured

    @pytest.mark.asyncio
    async def test_fetch_historical_messages(self, telegram_connector, mock_bot_info, mock_telegram_update):
        """Test fetching historical messages."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot.get_updates.return_value = [mock_telegram_update]
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                messages = await telegram_connector.fetch_historical_messages(limit=10)

                assert len(messages) == 1
                assert isinstance(messages[0], RawMessage)
                assert messages[0].platform == 'telegram'
                assert messages[0].platform_message_id == '1'
                mock_bot.get_updates.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_historical_messages_with_cursor(self, telegram_connector, mock_bot_info, mock_telegram_update):
        """Test fetching historical messages with cursor."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot.get_updates.return_value = [mock_telegram_update]
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                messages = await telegram_connector.fetch_historical_messages(cursor="100", limit=10)

                mock_bot.get_updates.assert_called_once_with(
                    offset=100,
                    limit=10,
                    timeout=10,
                    allowed_updates=['message', 'edited_message']
                )

    @pytest.mark.asyncio
    async def test_handle_webhook_valid_payload(self, telegram_connector, mock_telegram_update):
        """Test handling valid webhook payload."""
        payload = {
            'update_id': 1,
            'message': {
                'message_id': 1,
                'from': {'id': 987654321, 'username': 'test_user'},
                'chat': {'id': 123456789, 'type': 'private'},
                'date': int(datetime.now(timezone.utc).timestamp()),
                'text': 'Hello, world!'
            }
        }

        with patch('telegram.Update.de_json') as mock_de_json:
            mock_de_json.return_value = mock_telegram_update

            await telegram_connector.handle_webhook(payload)

            # Check that update was queued
            assert not telegram_connector._processing_queue.empty()
            mock_de_json.assert_called_once_with(
                payload, telegram_connector.bot)

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_payload(self, telegram_connector):
        """Test handling invalid webhook payload."""
        payload = {'invalid': 'data'}

        with patch('integrations.telegram_connector.Update.de_json') as mock_de_json:
            mock_de_json.return_value = None

            with pytest.raises(TelegramWebhookError, match="Failed to parse update"):
                await telegram_connector.handle_webhook(payload)

    @pytest.mark.asyncio
    async def test_process_update_to_raw_message(self, telegram_connector, mock_telegram_update, mock_telegram_message):
        """Test converting Telegram update to raw message."""
        raw_message = await telegram_connector._process_update_to_raw_message(mock_telegram_update)

        assert raw_message is not None
        assert isinstance(raw_message, RawMessage)
        assert raw_message.platform == 'telegram'
        assert raw_message.platform_message_id == '1'
        assert raw_message.thread_id == '123456789'
        assert raw_message.sender_id == '987654321'
        assert raw_message.content['text'] == 'Hello, world!'

    @pytest.mark.asyncio
    async def test_process_update_skip_bot_message(self, telegram_connector, mock_telegram_update, mock_telegram_message):
        """Test skipping messages from bots."""
        # Make the sender a bot
        mock_telegram_message.from_user.is_bot = True
        mock_telegram_message.chat.type = 'private'  # Not a channel

        raw_message = await telegram_connector._process_update_to_raw_message(mock_telegram_update)

        assert raw_message is None

    @pytest.mark.asyncio
    async def test_extract_message_content_text(self, telegram_connector, mock_telegram_message):
        """Test extracting content from text message."""
        content = await telegram_connector._extract_message_content(mock_telegram_message)

        assert content['text'] == 'Hello, world!'
        assert content['attachments'] == []
        assert content['entities'] == []

    @pytest.mark.asyncio
    async def test_extract_message_content_with_photo(self, telegram_connector, mock_telegram_message):
        """Test extracting content from message with photo."""
        # Mock photo
        photo = MagicMock()
        photo.file_id = 'photo_file_id'
        photo.file_unique_id = 'photo_unique_id'
        photo.width = 1920
        photo.height = 1080
        photo.file_size = 123456

        mock_telegram_message.photo = [photo]
        mock_telegram_message.caption = 'Photo caption'
        mock_telegram_message.text = None  # Override the default text

        content = await telegram_connector._extract_message_content(mock_telegram_message)

        assert content['text'] == 'Photo caption'
        assert len(content['attachments']) == 1
        assert content['attachments'][0]['type'] == 'photo'
        assert content['attachments'][0]['file_id'] == 'photo_file_id'

    @pytest.mark.asyncio
    async def test_extract_message_content_with_document(self, telegram_connector, mock_telegram_message):
        """Test extracting content from message with document."""
        # Mock document
        document = MagicMock()
        document.file_id = 'doc_file_id'
        document.file_unique_id = 'doc_unique_id'
        document.file_name = 'test.pdf'
        document.mime_type = 'application/pdf'
        document.file_size = 654321

        mock_telegram_message.document = document

        content = await telegram_connector._extract_message_content(mock_telegram_message)

        assert len(content['attachments']) == 1
        assert content['attachments'][0]['type'] == 'document'
        assert content['attachments'][0]['file_name'] == 'test.pdf'
        assert content['attachments'][0]['mime_type'] == 'application/pdf'

    @pytest.mark.asyncio
    async def test_send_message(self, telegram_connector, mock_bot_info):
        """Test sending a message."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info

            # Mock sent message
            sent_message = MagicMock()
            sent_message.message_id = 123
            mock_bot.send_message.return_value = sent_message
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                message_id = await telegram_connector.send_message(
                    chat_id=123456789,
                    text="Test message"
                )

                assert message_id == 123
                mock_bot.send_message.assert_called_once_with(
                    chat_id=123456789,
                    text="Test message",
                    parse_mode=None,
                    reply_to_message_id=None
                )

    @pytest.mark.asyncio
    async def test_get_chat_member_count(self, telegram_connector, mock_bot_info):
        """Test getting chat member count."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot.get_chat_member_count.return_value = 42
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                count = await telegram_connector.get_chat_member_count(123456789)

                assert count == 42
                mock_bot.get_chat_member_count.assert_called_once_with(
                    123456789)

    @pytest.mark.asyncio
    async def test_platform_health_check(self, telegram_connector, mock_bot_info):
        """Test platform-specific health check."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                await telegram_connector._platform_health_check()

                mock_bot.get_me.assert_called()

    @pytest.mark.asyncio
    async def test_platform_health_check_failure(self, telegram_connector, mock_bot_info):
        """Test platform health check failure."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.side_effect = TelegramError("Network error")
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                telegram_connector.bot = mock_bot

                with pytest.raises(TelegramConnectorError, match="Health check failed"):
                    await telegram_connector._platform_health_check()

    @pytest.mark.asyncio
    async def test_stop_real_time_ingestion(self, telegram_connector, mock_bot_info):
        """Test stopping real-time ingestion."""
        with patch('telegram.Bot') as mock_bot_class:
            mock_bot = AsyncMock()
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot.set_webhook.return_value = True
            mock_bot.delete_webhook.return_value = True
            mock_bot_class.return_value = mock_bot

            with patch('telegram.ext.Application.builder') as mock_app_builder:
                mock_builder = MagicMock()
                mock_app = AsyncMock()
                mock_builder.token.return_value = mock_builder
                mock_builder.build.return_value = mock_app
                mock_app_builder.return_value = mock_builder

                await telegram_connector.authenticate()
                await telegram_connector.start_real_time_ingestion()
                await telegram_connector.stop_real_time_ingestion()

                assert telegram_connector._processor_task is None
                assert not telegram_connector._webhook_configured
                mock_bot.delete_webhook.assert_called_once()

    def test_get_next_page_cursor(self, telegram_connector):
        """Test getting next page cursor."""
        cursor = telegram_connector.get_next_page_cursor(100)
        assert cursor == "101"

    def test_get_bot_info(self, telegram_connector):
        """Test getting bot info."""
        telegram_connector._bot_info = {'username': 'test_bot'}
        info = telegram_connector.get_bot_info()
        assert info['username'] == 'test_bot'

    def test_get_cached_chat(self, telegram_connector):
        """Test getting cached chat info."""
        chat_info = {'id': 123, 'type': 'private'}
        telegram_connector._chats_cache[123] = chat_info

        cached = telegram_connector.get_cached_chat(123)
        assert cached == chat_info

    def test_get_cached_user(self, telegram_connector):
        """Test getting cached user info."""
        user_info = {'id': 456, 'username': 'test_user'}
        telegram_connector._users_cache[456] = user_info

        cached = telegram_connector.get_cached_user(456)
        assert cached == user_info


class TestTelegramConnectorIntegration:
    """Integration tests for TelegramConnector."""

    @pytest.mark.asyncio
    async def test_full_message_processing_flow(self):
        """Test complete message processing flow."""
        config = {
            'bot_token': 'test_token',
            'webhook_url': 'https://example.com',
            'webhook_secret': 'secret'
        }

        event_bus = AsyncMock(spec=EventBus)
        connector = TelegramConnector(config=config, event_bus=event_bus)

        # Mock bot and application
        with patch('telegram.Bot') as mock_bot_class, \
                patch('telegram.ext.Application.builder') as mock_app_builder:

            mock_bot = AsyncMock()
            mock_bot_info = MagicMock()
            mock_bot_info.username = 'test_bot'
            mock_bot_info.id = 123
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot.set_webhook.return_value = True
            mock_bot_class.return_value = mock_bot

            mock_builder = MagicMock()
            mock_app = AsyncMock()
            mock_builder.token.return_value = mock_builder
            mock_builder.build.return_value = mock_app
            mock_app_builder.return_value = mock_builder

            # Authenticate and start
            await connector.authenticate()
            await connector.start_real_time_ingestion()

            # Create mock update
            update_data = {
                'update_id': 1,
                'message': {
                    'message_id': 1,
                    'from': {
                        'id': 987654321,
                        'username': 'test_user',
                        'first_name': 'Test',
                        'is_bot': False
                    },
                    'chat': {
                        'id': 123456789,
                        'type': 'private'
                    },
                    'date': int(datetime.now(timezone.utc).timestamp()),
                    'text': 'Hello, world!'
                }
            }

            # Mock Update.de_json
            with patch('telegram.Update.de_json') as mock_de_json:
                mock_update = MagicMock(spec=Update)
                mock_update.update_id = 1

                # Create mock message
                mock_message = MagicMock(spec=TelegramMessage)
                mock_message.message_id = 1
                mock_message.text = 'Hello, world!'
                mock_message.caption = None
                mock_message.date = datetime.now(timezone.utc)
                mock_message.entities = []
                mock_message.photo = None
                mock_message.document = None
                mock_message.audio = None
                mock_message.video = None
                mock_message.voice = None
                mock_message.video_note = None
                mock_message.sticker = None
                mock_message.location = None
                mock_message.contact = None
                mock_message.reply_to_message = None
                mock_message.forward_from = None
                mock_message.forward_from_chat = None
                mock_message.forward_date = None
                mock_message.forward_from_message_id = None
                mock_message.forward_signature = None
                mock_message.edit_date = None
                mock_message.via_bot = None
                mock_message.message_thread_id = None

                # Mock user and chat
                mock_user = MagicMock(spec=User)
                mock_user.id = 987654321
                mock_user.username = 'test_user'
                mock_user.first_name = 'Test'
                mock_user.last_name = None
                mock_user.is_bot = False
                mock_user.language_code = None
                mock_user.is_premium = None
                mock_user.added_to_attachment_menu = None

                mock_chat = MagicMock(spec=Chat)
                mock_chat.id = 123456789
                mock_chat.type = 'private'
                mock_chat.title = None
                mock_chat.username = None
                mock_chat.first_name = None
                mock_chat.last_name = None
                mock_chat.description = None
                mock_chat.invite_link = None
                mock_chat.pinned_message = None

                mock_message.from_user = mock_user
                mock_message.chat = mock_chat
                mock_message.to_dict.return_value = update_data['message']

                mock_update.message = mock_message
                mock_update.edited_message = None
                mock_update.channel_post = None
                mock_update.edited_channel_post = None

                mock_de_json.return_value = mock_update

                # Handle webhook
                await connector.handle_webhook(update_data)

                # Wait a bit for processing
                await asyncio.sleep(0.1)

                # Verify event was published
                event_bus.publish.assert_called()
                call_args = event_bus.publish.call_args
                assert call_args[0][0] == 'messages.raw'

                event = call_args[0][1]
                assert event.type == EventType.MESSAGE_RECEIVED
                assert event.data['platform'] == 'telegram'
                assert 'message' in event.data

            # Clean up
            await connector.stop_real_time_ingestion()

    @pytest.mark.asyncio
    async def test_error_handling_during_processing(self):
        """Test error handling during message processing."""
        config = {'bot_token': 'test_token'}
        event_bus = AsyncMock(spec=EventBus)
        connector = TelegramConnector(config=config, event_bus=event_bus)

        # Mock authentication
        with patch('telegram.Bot') as mock_bot_class, \
                patch('telegram.ext.Application.builder') as mock_app_builder:

            mock_bot = AsyncMock()
            mock_bot_info = MagicMock()
            mock_bot_info.username = 'test_bot'
            mock_bot.get_me.return_value = mock_bot_info
            mock_bot_class.return_value = mock_bot

            mock_builder = MagicMock()
            mock_app = AsyncMock()
            mock_builder.token.return_value = mock_builder
            mock_builder.build.return_value = mock_app
            mock_app_builder.return_value = mock_builder

            await connector.authenticate()

            # Test error during update processing
            with patch.object(connector, '_process_update_to_raw_message') as mock_process:
                mock_process.side_effect = Exception("Processing error")

                mock_update = MagicMock(spec=Update)
                mock_update.update_id = 1

                # This should not raise an exception
                await connector._process_telegram_update(mock_update)

                # Event should not be published due to error
                event_bus.publish.assert_not_called()
