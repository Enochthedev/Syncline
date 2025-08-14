"""
Integration tests for the complete message normalization pipeline.

Tests the full flow from raw messages through normalization, attachment processing,
and blob storage integration across multiple platforms.
"""

import pytest
import asyncio
import base64
from datetime import datetime
from unittest.mock import AsyncMock

from services.message_normalizer import MessageNormalizer, AttachmentProcessor
from services.message_schema import (
    Platform, ContentType, AttachmentType, RawMessage, NormalizedMessage,
    Attachment, Participant, Thread
)
from services.blob_storage import BlobStorageManager, LocalFileSystemStorage


class TestMessageNormalizationIntegration:
    """Test complete message normalization integration."""

    @pytest.fixture
    async def storage_manager(self, tmp_path):
        """Create a blob storage manager with temporary storage."""
        storage_client = LocalFileSystemStorage(str(tmp_path / "test_storage"))
        return BlobStorageManager(storage_client)

    @pytest.fixture
    def normalizer_with_storage(self, storage_manager):
        """Create a message normalizer with blob storage integration."""
        attachment_processor = AttachmentProcessor(storage_manager)
        normalizer = MessageNormalizer(attachment_processor)
        return normalizer

    @pytest.mark.asyncio
    async def test_gmail_message_with_attachment_full_pipeline(self, normalizer_with_storage):
        """Test complete Gmail message processing with attachment storage."""
        # Create a Gmail message with attachment
        attachment_content = b"This is a test PDF document content"
        gmail_data = {
            'id': 'gmail_integration_test',
            'threadId': 'gmail_thread_integration',
            'internalDate': '1705312200000',
            'snippet': 'Email with attachment...',
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'John Doe <john@example.com>'},
                    {'name': 'To', 'value': 'jane@example.com, bob@example.com'},
                    {'name': 'Subject', 'value': 'Integration Test Email'},
                    {'name': 'Date', 'value': 'Mon, 15 Jan 2024 10:30:00 +0000'}
                ],
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': base64.urlsafe_b64encode(
                                b'<p>Hello <strong>world</strong>!</p><p>Please find the document attached.</p>'
                            ).decode('ascii')
                        }
                    },
                    {
                        'filename': 'important_document.pdf',
                        'mimeType': 'application/pdf',
                        'body': {
                            'attachmentId': 'att_integration_123',
                            'size': len(attachment_content)
                        },
                        'partId': '1'
                    }
                ]
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='gmail_integration_test',
            raw_data=gmail_data
        )

        # Normalize the message
        normalized, thread, participants = await normalizer_with_storage.normalize_message(raw_message)

        # Verify message normalization
        assert normalized.platform == Platform.GMAIL
        assert normalized.platform_message_id == 'gmail_integration_test'
        assert normalized.thread_id == 'gmail_thread_integration'

        # Verify content processing
        assert normalized.content.html is not None
        assert normalized.content.text is not None
        assert 'Hello world!' in normalized.content.text
        assert '<strong>world</strong>' in normalized.content.html
        assert normalized.content.primary_format == ContentType.HTML

        # Verify sender processing
        assert normalized.sender.email == 'john@example.com'
        assert normalized.sender.display_name == 'John Doe'
        assert normalized.sender.platform == Platform.GMAIL

        # Verify recipients processing
        assert len(normalized.recipients) == 2
        recipient_emails = [r.email for r in normalized.recipients]
        assert 'jane@example.com' in recipient_emails
        assert 'bob@example.com' in recipient_emails

        # Verify attachment processing
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'important_document.pdf'
        assert attachment.cleaned_mime_type == 'application/pdf'
        assert attachment.attachment_type == AttachmentType.DOCUMENT
        assert attachment.file_size == len(attachment_content)

        # Verify thread creation
        assert thread.platform == Platform.GMAIL
        assert thread.title == 'Integration Test Email'
        assert len(thread.participants) == 3  # sender + 2 recipients

        # Verify participants list
        assert len(participants) == 3
        participant_emails = [p.email for p in participants if p.email]
        assert 'john@example.com' in participant_emails
        assert 'jane@example.com' in participant_emails
        assert 'bob@example.com' in participant_emails

    @pytest.mark.asyncio
    async def test_multi_platform_normalization(self, normalizer_with_storage):
        """Test normalization across multiple platforms."""

        # Test Gmail message
        gmail_data = {
            'id': 'gmail_multi_test',
            'threadId': 'gmail_thread_multi',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'gmail_user@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Gmail Test'}
                ],
                'mimeType': 'text/plain',
                'body': {'data': base64.urlsafe_b64encode(b'Gmail message content').decode('ascii')}
            }
        }

        gmail_raw = RawMessage(Platform.GMAIL, 'gmail_multi_test', gmail_data)
        gmail_normalized, gmail_thread, gmail_participants = await normalizer_with_storage.normalize_message(gmail_raw)

        # Test Slack message
        slack_data = {
            'type': 'message',
            'ts': '1705312300.123456',
            'user': 'U123456',
            'text': 'Slack message with *formatting*',
            'channel': 'C789012',
            'username': 'slack_user'
        }

        slack_raw = RawMessage(Platform.SLACK, '1705312300.123456', slack_data)
        slack_normalized, slack_thread, slack_participants = await normalizer_with_storage.normalize_message(slack_raw)

        # Test Discord message
        discord_data = {
            'id': '123456789012345678',
            'channel_id': '987654321098765432',
            'guild_id': '111222333444555666',
            'author': {
                'id': '555666777888999000',
                'username': 'discord_user',
                'discriminator': '1234'
            },
            'content': 'Discord message with **bold** text',
            'timestamp': '2024-01-15T10:35:00.000Z'
        }

        discord_raw = RawMessage(
            Platform.DISCORD, '123456789012345678', discord_data)
        discord_normalized, discord_thread, discord_participants = await normalizer_with_storage.normalize_message(discord_raw)

        # Test WhatsApp message
        whatsapp_data = {
            'event_id': '$whatsapp_multi_test',
            'room_id': '!whatsapp_room_multi:matrix.org',
            'sender': '@whatsapp_user:matrix.org',
            'origin_server_ts': 1705312400000,
            'content': {
                'msgtype': 'm.text',
                'body': 'WhatsApp message content'
            }
        }

        whatsapp_raw = RawMessage(
            Platform.WHATSAPP, '$whatsapp_multi_test', whatsapp_data)
        whatsapp_normalized, whatsapp_thread, whatsapp_participants = await normalizer_with_storage.normalize_message(whatsapp_raw)

        # Verify all platforms were processed correctly
        platforms_processed = [
            gmail_normalized.platform,
            slack_normalized.platform,
            discord_normalized.platform,
            whatsapp_normalized.platform
        ]

        assert Platform.GMAIL in platforms_processed
        assert Platform.SLACK in platforms_processed
        assert Platform.DISCORD in platforms_processed
        assert Platform.WHATSAPP in platforms_processed

        # Verify content was processed for each platform
        assert 'Gmail message content' in gmail_normalized.content.text
        assert 'Slack message' in slack_normalized.content.text
        assert 'Discord message' in discord_normalized.content.text
        assert 'WhatsApp message content' in whatsapp_normalized.content.text

        # Verify platform-specific features
        # No labels in test data
        assert gmail_normalized.metadata['labels'] == []
        assert 'C789012' in slack_normalized.thread_id
        assert discord_normalized.metadata['guild_id'] == '111222333444555666'
        assert whatsapp_normalized.metadata['msgtype'] == 'm.text'

    @pytest.mark.asyncio
    async def test_attachment_processing_with_storage(self, normalizer_with_storage, tmp_path):
        """Test attachment processing with actual blob storage."""
        # Create test attachment content
        test_image_content = b"fake_image_data_for_testing"

        slack_data = {
            'type': 'message',
            'ts': '1705312500.123456',
            'user': 'U123456',
            'text': 'Message with file attachment',
            'channel': 'C789012',
            'files': [
                {
                    'id': 'F123456',
                    'name': 'test_image.png',
                    'mimetype': 'image/png',
                    'size': len(test_image_content),
                    'url_private': 'https://files.slack.com/test_image.png'
                }
            ]
        }

        raw_message = RawMessage(
            Platform.SLACK, '1705312500.123456', slack_data)
        normalized, thread, participants = await normalizer_with_storage.normalize_message(raw_message)

        # Verify attachment was processed
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'test_image.png'
        assert attachment.cleaned_mime_type == 'image/png'
        assert attachment.attachment_type == AttachmentType.IMAGE
        assert attachment.file_size == len(test_image_content)

        # Note: In this test, we don't actually store the attachment content
        # because the Slack normalizer doesn't download the file content
        # This would be handled by the actual Slack connector

    @pytest.mark.asyncio
    async def test_content_standardization_across_platforms(self, normalizer_with_storage):
        """Test content standardization works consistently across platforms."""

        # Test HTML content (Gmail)
        html_content = '<p>Hello <strong>world</strong>!</p><p>Second paragraph.</p>'
        gmail_data = {
            'id': 'content_test_gmail',
            'threadId': 'content_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Content Test'}
                ],
                'mimeType': 'text/html',
                'body': {'data': base64.urlsafe_b64encode(html_content.encode()).decode('ascii')}
            }
        }

        gmail_raw = RawMessage(
            Platform.GMAIL, 'content_test_gmail', gmail_data)
        gmail_normalized, _, _ = await normalizer_with_storage.normalize_message(gmail_raw)

        # Test Markdown content (Slack/Discord)
        markdown_content = 'Hello **world**! Second paragraph.'
        slack_data = {
            'type': 'message',
            'ts': '1705312600.123456',
            'user': 'U123456',
            'text': markdown_content,
            'channel': 'C789012'
        }

        slack_raw = RawMessage(Platform.SLACK, '1705312600.123456', slack_data)
        slack_normalized, _, _ = await normalizer_with_storage.normalize_message(slack_raw)

        # Verify both produce similar text output
        gmail_text = gmail_normalized.content.text.replace('\n', ' ').strip()
        slack_text = slack_normalized.content.text.replace('\n', ' ').strip()

        assert 'Hello world!' in gmail_text
        assert 'Hello world!' in slack_text
        assert 'Second paragraph' in gmail_text
        assert 'Second paragraph' in slack_text

        # Verify format-specific content is preserved
        assert gmail_normalized.content.html is not None
        assert '<strong>world</strong>' in gmail_normalized.content.html
        assert slack_normalized.content.markdown is not None
        assert '**world**' in slack_normalized.content.markdown

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, normalizer_with_storage):
        """Test error handling and recovery in the normalization pipeline."""

        # Test with malformed Gmail data
        malformed_gmail_data = {
            'id': 'malformed_test',
            # Missing threadId and payload
        }

        malformed_raw = RawMessage(
            Platform.GMAIL, 'malformed_test', malformed_gmail_data)

        # Should handle gracefully
        try:
            normalized, thread, participants = await normalizer_with_storage.normalize_message(malformed_raw)
            # If it succeeds, verify basic structure
            assert normalized.platform == Platform.GMAIL
            assert normalized.platform_message_id == 'malformed_test'
        except Exception as e:
            # If it fails, should be a controlled failure
            assert isinstance(e, (ValueError, KeyError, AttributeError))

        # Test with unsupported platform
        with pytest.raises(ValueError, match="Unsupported platform"):
            unsupported_raw = RawMessage(Platform.INSTAGRAM, 'test', {})
            await normalizer_with_storage.normalize_message(unsupported_raw)

    @pytest.mark.asyncio
    async def test_mime_type_resolution_integration(self, normalizer_with_storage):
        """Test MIME type resolution works in the full pipeline."""

        # Test with generic MIME type but specific filename
        gmail_data = {
            'id': 'mime_resolution_test',
            'threadId': 'mime_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'test@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'MIME Resolution Test'}
                ],
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {'data': base64.urlsafe_b64encode(b'Test message').decode('ascii')}
                    },
                    {
                        'filename': 'spreadsheet.xlsx',
                        'mimeType': 'application/octet-stream',  # Generic MIME type
                        'body': {
                            'attachmentId': 'att_mime_test',
                            'size': 1024
                        },
                        'partId': '1'
                    }
                ]
            }
        }

        raw_message = RawMessage(
            Platform.GMAIL, 'mime_resolution_test', gmail_data)
        normalized, thread, participants = await normalizer_with_storage.normalize_message(raw_message)

        # Verify MIME type was resolved correctly
        assert len(normalized.attachments) == 1
        attachment = normalized.attachments[0]
        assert attachment.filename == 'spreadsheet.xlsx'
        # Should resolve to Excel MIME type based on filename
        assert attachment.cleaned_mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert attachment.attachment_type == AttachmentType.DOCUMENT

    @pytest.mark.asyncio
    async def test_performance_with_large_message_batch(self, normalizer_with_storage):
        """Test performance with a batch of messages."""

        # Create a batch of test messages
        messages = []
        for i in range(10):
            gmail_data = {
                'id': f'batch_test_{i}',
                'threadId': f'batch_thread_{i}',
                'internalDate': str(1705312200000 + i * 1000),
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': f'sender_{i}@example.com'},
                        {'name': 'To', 'value': 'recipient@example.com'},
                        {'name': 'Subject', 'value': f'Batch Test Message {i}'}
                    ],
                    'mimeType': 'text/plain',
                    'body': {'data': base64.urlsafe_b64encode(f'Batch message {i} content'.encode()).decode('ascii')}
                }
            }

            raw_message = RawMessage(
                Platform.GMAIL, f'batch_test_{i}', gmail_data)
            messages.append(raw_message)

        # Process all messages
        start_time = datetime.utcnow()
        results = []

        for raw_message in messages:
            normalized, thread, participants = await normalizer_with_storage.normalize_message(raw_message)
            results.append((normalized, thread, participants))

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # Verify all messages were processed
        assert len(results) == 10

        # Verify processing was reasonably fast (should be well under 1 second for 10 simple messages)
        assert processing_time < 1.0

        # Verify each message was processed correctly
        for i, (normalized, thread, participants) in enumerate(results):
            assert normalized.platform_message_id == f'batch_test_{i}'
            assert f'Batch message {i} content' in normalized.content.text
            assert thread.title == f'Batch Test Message {i}'
            assert len(participants) == 2  # sender + recipient
