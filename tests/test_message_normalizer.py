"""
Tests for message normalization service.

Tests the main MessageNormalizer service, platform-specific normalizers,
and attachment processing.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
import base64

from services.message_normalizer import (
    MessageNormalizer, AttachmentProcessor, PlatformNormalizers
)
from services.message_schema import (
    Platform, ContentType, AttachmentType, RawMessage, NormalizedMessage,
    Attachment, Participant, Thread
)


class TestAttachmentProcessor:
    """Test attachment processing functionality."""

    def test_attachment_processing(self):
        """Test basic attachment processing."""
        processor = AttachmentProcessor()

        attachment_data = {
            'filename': 'document.pdf',
            'mimeType': 'application/pdf',
            'size': 1024,
            'content': b'PDF content here'
        }

        attachment = processor.process_attachment(attachment_data, "msg123")

        assert attachment.filename == 'document.pdf'
        assert attachment.cleaned_mime_type == 'application/pdf'
        assert attachment.attachment_type == AttachmentType.DOCUMENT
        assert attachment.file_size == 1024
        assert attachment.content_hash is not None
        assert 'platform_data' in attachment.metadata

    def test_attachment_processing_variations(self):
        """Test attachment processing with different data formats."""
        processor = AttachmentProcessor()

        # Test with alternative field names
        attachment_data = {
            'name': 'image.jpg',  # 'name' instead of 'filename'
            'content_type': 'image/jpeg',  # 'content_type' instead of 'mimeType'
            'file_size': 2048,  # 'file_size' instead of 'size'
        }

        attachment = processor.process_attachment(attachment_data, "msg456")

        assert attachment.filename == 'image.jpg'
        assert attachment.cleaned_mime_type == 'image/jpeg'
        assert attachment.attachment_type == AttachmentType.IMAGE
        assert attachment.file_size == 2048

    def test_content_hashing(self):
        """Test content hashing for attachments."""
        processor = AttachmentProcessor()

        # Test with bytes content
        attachment_data = {
            'filename': 'test.txt',
            'content': b'Test content for hashing'
        }

        attachment = processor.process_attachment(attachment_data, "msg789")
        assert attachment.content_hash is not None
        assert len(attachment.content_hash) == 64  # SHA-256 hex length

        # Test with string content
        attachment_data_str = {
            'filename': 'test2.txt',
            'content': 'String content for hashing'
        }

        attachment_str = processor.process_attachment(
            attachment_data_str, "msg790")
        assert attachment_str.content_hash is not None
        assert len(attachment_str.content_hash) == 64

        # Same content should produce same hash
        attachment_data_same = {
            'filename': 'test3.txt',
            'content': b'Test content for hashing'
        }

        attachment_same = processor.process_attachment(
            attachment_data_same, "msg791")
        assert attachment.content_hash == attachment_same.content_hash

    @pytest.mark.asyncio
    async def test_attachment_storage_integration(self):
        """Test attachment storage integration."""
        # Mock blob storage manager
        mock_manager = AsyncMock()
        mock_manager.store_attachment.return_value = {
            'storage_path': 'attachments/msg123/test.pdf',
            'storage_url': 'https://storage.example.com/file.pdf',
            'content_hash': 'abc123',
            'size': 11
        }

        processor = AttachmentProcessor(mock_manager)

        attachment = Attachment(
            filename="test.pdf",
            cleaned_mime_type="application/pdf"
        )

        content = b"PDF content"
        result = await processor.store_attachment(attachment, content, "msg123")

        assert result.storage_url == "https://storage.example.com/file.pdf"
        assert result.storage_path == 'attachments/msg123/test.pdf'
        assert result.content_hash == 'abc123'
        mock_manager.store_attachment.assert_called_once()

    @pytest.mark.asyncio
    async def test_attachment_storage_without_manager(self):
        """Test attachment storage without blob storage manager."""
        processor = AttachmentProcessor(blob_storage_manager=None)

        attachment = Attachment(filename="test.pdf")
        content = b"PDF content"

        # Should not raise error, just log warning
        result = await processor.store_attachment(attachment, content, "msg123")
        assert result == attachment  # Should return unchanged attachment

    @pytest.mark.asyncio
    async def test_enhanced_attachment_processing(self):
        """Test enhanced attachment processing with MIME type resolution."""
        processor = AttachmentProcessor()

        # Test with generic MIME type but specific filename
        attachment_data = {
            'filename': 'document.pdf',
            'mimeType': 'application/octet-stream',  # Generic
            'size': 2048
        }

        attachment = processor.process_attachment(attachment_data, "msg456")

        # Should resolve to PDF based on filename
        assert attachment.cleaned_mime_type == 'application/pdf'
        assert attachment.attachment_type == AttachmentType.DOCUMENT
        assert 'message_id' in attachment.metadata

    def test_unsafe_mime_type_handling(self):
        """Test handling of potentially unsafe MIME types."""
        processor = AttachmentProcessor()

        attachment_data = {
            'filename': 'script.exe',
            'mimeType': 'application/x-executable',
            'size': 1024
        }

        attachment = processor.process_attachment(attachment_data, "msg789")

        # Should process but mark as potentially unsafe
        assert 'safety_warning' in attachment.metadata
        assert attachment.metadata['safety_warning'] == 'potentially_unsafe_mime_type'


class TestPlatformNormalizers:
    """Test platform-specific normalization logic."""

    def test_gmail_message_normalization(self):
        """Test Gmail message normalization."""
        gmail_data = {
            'id': 'gmail_msg_123',
            'threadId': 'gmail_thread_456',
            'internalDate': '1705312200000',  # 2024-01-15 10:30:00
            'snippet': 'Hello world...',
            'labelIds': ['INBOX', 'UNREAD'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'John Doe <john@example.com>'},
                    {'name': 'To', 'value': 'jane@example.com'},
                    {'name': 'Subject', 'value': 'Test Email'},
                    {'name': 'Date', 'value': 'Mon, 15 Jan 2024 10:30:00 +0000'}
                ],
                'mimeType': 'text/plain',
                'body': {
                    'data': base64.urlsafe_b64encode(b'Hello world').decode('ascii')
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='gmail_msg_123',
            raw_data=gmail_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_gmail_message(
            raw_message)

        # Check normalized message
        assert normalized.platform == Platform.GMAIL
        assert normalized.platform_message_id == 'gmail_msg_123'
        assert normalized.thread_id == 'gmail_thread_456'
        assert normalized.content.text == 'Hello world'
        assert 'INBOX' in normalized.metadata['labels']

        # Check sender
        assert normalized.sender.email == 'john@example.com'
        assert normalized.sender.display_name == 'John Doe'

        # Check recipients
        assert len(normalized.recipients) == 1
        assert normalized.recipients[0].email == 'jane@example.com'

        # Check thread
        assert thread.platform == Platform.GMAIL
        assert thread.title == 'Test Email'
        assert len(thread.participants) == 2  # sender + recipient

        # Check participants list
        assert len(participants) == 2

    def test_gmail_multipart_message(self):
        """Test Gmail multipart message normalization."""
        gmail_data = {
            'id': 'gmail_multipart_123',
            'threadId': 'gmail_thread_789',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Multipart Test'}
                ],
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'<p>HTML content</p>').decode('ascii')
                        }
                    },
                    {
                        'filename': 'attachment.pdf',
                        'mimeType': 'application/pdf',
                        'body': {
                            'attachmentId': 'att_123',
                            'size': 1024
                        },
                        'partId': '1'
                    }
                ]
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='gmail_multipart_123',
            raw_data=gmail_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_gmail_message(
            raw_message)

        # Check content extraction
        assert normalized.content.html is not None
        assert 'HTML content' in normalized.content.text

        # Check attachment extraction
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'attachment.pdf'
        assert attachment.mime_type == 'application/pdf'
        assert attachment.file_size == 1024
        assert 'attachment_id' in attachment.metadata

    def test_slack_message_normalization(self):
        """Test Slack message normalization."""
        slack_data = {
            'type': 'message',
            'ts': '1705312200.123456',
            'user': 'U123456',
            'text': 'Hello *world* from Slack!',
            'channel': 'C789012',
            'username': 'john.doe',
            'user_profile': {
                'display_name': 'John Doe',
                'email': 'john@company.com',
                'image_72': 'https://avatars.slack.com/user.jpg'
            },
            'files': [
                {
                    'id': 'F123456',
                    'name': 'document.pdf',
                    'mimetype': 'application/pdf',
                    'size': 1024,
                    'url_private': 'https://files.slack.com/document.pdf'
                }
            ]
        }

        raw_message = RawMessage(
            platform=Platform.SLACK,
            platform_message_id='1705312200.123456',
            raw_data=slack_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_slack_message(
            raw_message)

        # Check normalized message
        assert normalized.platform == Platform.SLACK
        assert normalized.platform_message_id == '1705312200.123456'
        assert normalized.thread_id == 'C789012_1705312200.123456'
        assert 'Hello' in normalized.content.text

        # Check sender
        assert normalized.sender.platform_user_id == 'U123456'
        # Display name might use username if display_name not available
        assert normalized.sender.display_name in ['John Doe', 'john.doe']
        assert normalized.sender.email == 'john@company.com'

        # Check attachments
        assert len(normalized.attachments) == 1
        assert normalized.attachments[0].filename == 'document.pdf'
        assert normalized.attachments[0].mime_type == 'application/pdf'

        # Check thread
        assert thread.platform == Platform.SLACK
        assert 'C789012' in thread.platform_thread_id
        assert thread.metadata['channel_id'] == 'C789012'

    def test_slack_threaded_message(self):
        """Test Slack threaded message normalization."""
        slack_data = {
            'type': 'message',
            'ts': '1705312300.123456',
            'thread_ts': '1705312200.123456',  # This is a reply
            'user': 'U789012',
            'text': 'This is a reply in a thread',
            'channel': 'C789012'
        }

        raw_message = RawMessage(
            platform=Platform.SLACK,
            platform_message_id='1705312300.123456',
            raw_data=slack_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_slack_message(
            raw_message)

        # Thread ID should use thread_ts instead of ts
        assert normalized.thread_id == 'C789012_1705312200.123456'
        assert thread.platform_thread_id == 'C789012_1705312200.123456'

    def test_discord_message_normalization(self):
        """Test Discord message normalization."""
        discord_data = {
            'id': '123456789012345678',
            'channel_id': '987654321098765432',
            'guild_id': '111222333444555666',
            'author': {
                'id': '555666777888999000',
                'username': 'testuser',
                'discriminator': '1234',
                'avatar': 'abcdef123456',
                'bot': False
            },
            'content': 'Hello **Discord** world!',
            'timestamp': '2024-01-15T10:30:00.000Z',
            'attachments': [
                {
                    'id': '999888777666555444',
                    'filename': 'image.png',
                    'content_type': 'image/png',
                    'size': 1024,
                    'url': 'https://cdn.discordapp.com/attachments/123/image.png'
                }
            ]
        }

        raw_message = RawMessage(
            platform=Platform.DISCORD,
            platform_message_id='123456789012345678',
            raw_data=discord_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_discord_message(
            raw_message)

        # Check normalized message
        assert normalized.platform == Platform.DISCORD
        assert normalized.platform_message_id == '123456789012345678'
        assert 'Hello' in normalized.content.text
        assert normalized.sender.platform_user_id == '555666777888999000'
        assert normalized.sender.display_name == 'testuser'

        # Check attachments
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'image.png'
        assert attachment.mime_type == 'image/png'

        # Check thread
        assert thread.platform == Platform.DISCORD
        assert '111222333444555666_987654321098765432' in thread.platform_thread_id

    def test_whatsapp_message_normalization(self):
        """Test WhatsApp message normalization."""
        whatsapp_data = {
            'event_id': '$whatsapp_event_123',
            'room_id': '!whatsapp_room_456:matrix.org',
            'sender': '@whatsapp_user_789:matrix.org',
            'origin_server_ts': 1705312200000,
            'content': {
                'msgtype': 'm.text',
                'body': 'Hello from WhatsApp!'
            }
        }

        raw_message = RawMessage(
            platform=Platform.WHATSAPP,
            platform_message_id='$whatsapp_event_123',
            raw_data=whatsapp_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_whatsapp_message(
            raw_message)

        # Check normalized message
        assert normalized.platform == Platform.WHATSAPP
        assert normalized.content.text == 'Hello from WhatsApp!'
        assert normalized.sender.platform_user_id == '@whatsapp_user_789:matrix.org'

        # Check thread
        assert thread.platform == Platform.WHATSAPP
        assert thread.platform_thread_id == '!whatsapp_room_456:matrix.org'

    def test_whatsapp_image_message_normalization(self):
        """Test WhatsApp image message normalization."""
        whatsapp_data = {
            'event_id': '$whatsapp_image_123',
            'room_id': '!whatsapp_room_456:matrix.org',
            'sender': '@whatsapp_user_789:matrix.org',
            'origin_server_ts': 1705312200000,
            'content': {
                'msgtype': 'm.image',
                'body': 'vacation_photo.jpg',
                'url': 'mxc://matrix.org/abcdef123456',
                'info': {
                    'mimetype': 'image/jpeg',
                    'size': 2048,
                    'w': 1920,
                    'h': 1080
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.WHATSAPP,
            platform_message_id='$whatsapp_image_123',
            raw_data=whatsapp_data
        )

        normalized, thread, participants = PlatformNormalizers.normalize_whatsapp_message(
            raw_message)

        # Check content and attachments
        assert '[Image]' in normalized.content.text
        assert len(normalized.attachments) == 1

        attachment = normalized.attachments[0]
        assert attachment.filename == 'vacation_photo.jpg'
        assert attachment.mime_type == 'image/jpeg'
        assert attachment.attachment_type == AttachmentType.IMAGE
        assert attachment.metadata['width'] == 1920
        assert attachment.metadata['height'] == 1080


class TestMessageNormalizer:
    """Test the main message normalizer service."""

    @pytest.fixture
    def normalizer(self):
        """Create a message normalizer instance."""
        return MessageNormalizer()

    @pytest.mark.asyncio
    async def test_gmail_message_normalization_integration(self, normalizer):
        """Test complete Gmail message normalization."""
        gmail_data = {
            'id': 'msg123',
            'threadId': 'thread456',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Test Subject'}
                ],
                'mimeType': 'text/plain',
                'body': {'data': base64.urlsafe_b64encode(b'Test message').decode('ascii')}
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='msg123',
            raw_data=gmail_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        assert normalized.platform == Platform.GMAIL
        assert normalized.content.text == 'Test message'
        assert thread.title == 'Test Subject'
        assert len(participants) == 2

    @pytest.mark.asyncio
    async def test_slack_message_normalization_integration(self, normalizer):
        """Test complete Slack message normalization."""
        slack_data = {
            'type': 'message',
            'ts': '1705312200.123456',
            'user': 'U123456',
            'text': 'Test Slack message',
            'channel': 'C789012'
        }

        raw_message = RawMessage(
            platform=Platform.SLACK,
            platform_message_id='1705312200.123456',
            raw_data=slack_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        assert normalized.platform == Platform.SLACK
        assert normalized.content.text == 'Test Slack message'
        assert 'C789012' in thread.platform_thread_id
        assert len(participants) == 1

    @pytest.mark.asyncio
    async def test_unsupported_platform_error(self, normalizer):
        """Test error handling for unsupported platforms."""
        raw_message = RawMessage(
            platform=Platform.INSTAGRAM,  # Not implemented yet
            platform_message_id='msg123',
            raw_data={}
        )

        with pytest.raises(ValueError, match="Unsupported platform"):
            await normalizer.normalize_message(raw_message)

    def test_supported_platforms(self, normalizer):
        """Test getting supported platforms."""
        platforms = normalizer.get_supported_platforms()

        assert Platform.GMAIL in platforms
        assert Platform.SLACK in platforms
        assert len(platforms) >= 2

    def test_custom_platform_normalizer(self, normalizer):
        """Test adding custom platform normalizer."""
        def custom_normalizer(raw_message):
            return (
                NormalizedMessage(platform=Platform.TELEGRAM),
                Thread(platform=Platform.TELEGRAM),
                []
            )

        normalizer.add_platform_normalizer(
            Platform.TELEGRAM, custom_normalizer)

        platforms = normalizer.get_supported_platforms()
        assert Platform.TELEGRAM in platforms

    @pytest.mark.asyncio
    async def test_attachment_processing_integration(self, normalizer):
        """Test attachment processing in normalization pipeline."""
        gmail_data = {
            'id': 'msg_with_attachment',
            'threadId': 'thread_with_attachment',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Message with Attachment'}
                ],
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'Message with attachment').decode('ascii')
                        }
                    },
                    {
                        'filename': 'test_document.pdf',
                        'mimeType': 'application/pdf',
                        'body': {
                            'attachmentId': 'att_123',
                            'size': 2048
                        },
                        'partId': '1'
                    }
                ]
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='msg_with_attachment',
            raw_data=gmail_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Verify attachment processing
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'test_document.pdf'
        assert attachment.cleaned_mime_type == 'application/pdf'
        assert attachment.file_size == 2048
        assert attachment.attachment_type == AttachmentType.DOCUMENT

    @pytest.mark.asyncio
    async def test_error_handling_in_normalization(self, normalizer):
        """Test error handling during normalization process."""
        # Test with malformed Gmail data
        malformed_gmail_data = {
            'id': 'malformed_msg',
            # Missing required fields like threadId, payload, etc.
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='malformed_msg',
            raw_data=malformed_gmail_data
        )

        # Should handle gracefully and not crash
        try:
            normalized, thread, participants = await normalizer.normalize_message(raw_message)
            # If it succeeds, verify basic structure
            assert normalized.platform == Platform.GMAIL
            assert normalized.platform_message_id == 'malformed_msg'
        except Exception as e:
            # If it fails, should be a controlled failure
            assert isinstance(e, (ValueError, KeyError, AttributeError))

    @pytest.mark.asyncio
    async def test_discord_message_normalization_integration(self, normalizer):
        """Test complete Discord message normalization."""
        discord_data = {
            'id': '123456789012345678',
            'channel_id': '987654321098765432',
            'guild_id': '111222333444555666',
            'author': {
                'id': '555666777888999000',
                'username': 'testuser',
                'discriminator': '1234',
                'avatar': 'abcdef123456',
                'bot': False
            },
            'content': 'Hello **Discord** world!',
            'timestamp': '2024-01-15T10:30:00.000Z',
            'attachments': [
                {
                    'id': '999888777666555444',
                    'filename': 'image.png',
                    'content_type': 'image/png',
                    'size': 1024,
                    'url': 'https://cdn.discordapp.com/attachments/123/image.png',
                    'proxy_url': 'https://media.discordapp.net/attachments/123/image.png',
                    'width': 800,
                    'height': 600
                }
            ],
            'embeds': [
                {
                    'title': 'Embed Title',
                    'description': 'Embed description',
                    'url': 'https://example.com'
                }
            ]
        }

        raw_message = RawMessage(
            platform=Platform.DISCORD,
            platform_message_id='123456789012345678',
            raw_data=discord_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        assert normalized.platform == Platform.DISCORD
        assert 'Hello' in normalized.content.text
        assert 'Embed Title' in normalized.content.text  # Embeds should be included
        assert len(normalized.attachments) == 1
        assert normalized.attachments[0].attachment_type == AttachmentType.IMAGE
        assert 'guild_id' in normalized.metadata

    @pytest.mark.asyncio
    async def test_whatsapp_message_normalization_integration(self, normalizer):
        """Test complete WhatsApp message normalization."""
        whatsapp_data = {
            'event_id': '$whatsapp_event_123',
            'room_id': '!whatsapp_room_456:matrix.org',
            'sender': '@whatsapp_user_789:matrix.org',
            'origin_server_ts': 1705312200000,
            'content': {
                'msgtype': 'm.text',
                'body': 'Hello from WhatsApp!'
            }
        }

        raw_message = RawMessage(
            platform=Platform.WHATSAPP,
            platform_message_id='$whatsapp_event_123',
            raw_data=whatsapp_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        assert normalized.platform == Platform.WHATSAPP
        assert normalized.content.text == 'Hello from WhatsApp!'
        assert 'room_id' in normalized.metadata
        assert normalized.sender.platform_user_id == '@whatsapp_user_789:matrix.org'

    @pytest.mark.asyncio
    async def test_whatsapp_image_message_normalization(self, normalizer):
        """Test WhatsApp image message normalization."""
        whatsapp_data = {
            'event_id': '$whatsapp_image_123',
            'room_id': '!whatsapp_room_456:matrix.org',
            'sender': '@whatsapp_user_789:matrix.org',
            'origin_server_ts': 1705312200000,
            'content': {
                'msgtype': 'm.image',
                'body': 'vacation_photo.jpg',
                'url': 'mxc://matrix.org/abcdef123456',
                'info': {
                    'mimetype': 'image/jpeg',
                    'size': 2048,
                    'w': 1920,
                    'h': 1080
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.WHATSAPP,
            platform_message_id='$whatsapp_image_123',
            raw_data=whatsapp_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        assert normalized.platform == Platform.WHATSAPP
        assert '[Image]' in normalized.content.text
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'vacation_photo.jpg'
        assert attachment.attachment_type == AttachmentType.IMAGE
        assert attachment.metadata['width'] == 1920

    @pytest.mark.asyncio
    async def test_content_format_handling(self, normalizer):
        """Test handling of different content formats."""
        # Test HTML content
        html_gmail_data = {
            'id': 'html_msg',
            'threadId': 'html_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'HTML Message'}
                ],
                'mimeType': 'text/html',
                'body': {
                    'data': base64.urlsafe_b64encode(b'<p>HTML <strong>content</strong></p>').decode('ascii')
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='html_msg',
            raw_data=html_gmail_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Should have both HTML and text versions
        assert normalized.content.html is not None
        assert normalized.content.text is not None
        assert 'HTML content' in normalized.content.text
        assert '<strong>' in normalized.content.html

    @pytest.mark.asyncio
    async def test_enhanced_attachment_processing(self, normalizer):
        """Test enhanced attachment processing with MIME type resolution."""
        gmail_data = {
            'id': 'msg_enhanced_attachment',
            'threadId': 'thread_enhanced_attachment',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Enhanced Attachment Test'}
                ],
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'Message with enhanced attachment').decode('ascii')
                        }
                    },
                    {
                        'filename': 'document.pdf',
                        'mimeType': 'application/octet-stream',  # Generic MIME type
                        'body': {
                            'attachmentId': 'att_enhanced_123',
                            'size': 4096
                        },
                        'partId': '1'
                    }
                ]
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='msg_enhanced_attachment',
            raw_data=gmail_data
        )

        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Verify enhanced attachment processing
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'document.pdf'
        # Should resolve to PDF MIME type based on filename
        assert attachment.cleaned_mime_type == 'application/pdf'
        assert attachment.attachment_type == AttachmentType.DOCUMENT
        assert 'attachment_id' in attachment.metadata

    @pytest.mark.asyncio
    async def test_content_standardization_edge_cases(self, normalizer):
        """Test content standardization with edge cases."""
        # Test content with null bytes and mixed line endings
        problematic_content = "Hello\x00World\r\nWith\rMixed\nEndings"

        from services.message_normalizer import ContentProcessor
        from services.message_schema import ContentType

        # Test text standardization
        result = ContentProcessor.standardize_content(
            problematic_content, ContentType.TEXT)
        assert '\x00' not in result.text
        assert '\r' not in result.text
        assert 'HelloWorld' in result.text

        # Test markdown standardization
        markdown_content = "**Bold** *italic* `code` # Header [link](url)"
        result = ContentProcessor.standardize_content(
            markdown_content, ContentType.MARKDOWN)
        assert result.markdown == markdown_content
        assert 'Bold italic code Header link' in result.text  # Formatting removed
