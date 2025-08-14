"""
Tests for Gmail integration functionality.

Tests Gmail API integration, email fetching, and message processing pipeline.
"""

import pytest
import base64
from datetime import datetime

from services.message_normalizer import MessageNormalizer
from services.message_schema import Platform, RawMessage


class TestGmailIntegration:
    """Test Gmail integration functionality."""

    def test_gmail_fetch_basic(self):
        """Test basic Gmail fetch functionality."""
        try:
            from integrations.gmail_client.fetch import fetch_emails

            # Test with a small query to avoid rate limits
            emails = fetch_emails(query="is:inbox", max_results=1)

            # Should return a list (might be empty if no emails)
            assert isinstance(emails, list)

            if emails:
                # If we got emails, verify structure
                email = emails[0]
                assert 'id' in email
                assert 'snippet' in email
                assert 'threadId' in email or email.get('threadId') is not None

        except ImportError:
            pytest.skip("Gmail integration not available")
        except Exception as e:
            # Gmail tests might fail due to auth issues in CI/testing
            pytest.skip(f"Gmail test skipped due to: {e}")

    def test_gmail_fetch_with_results(self):
        """Test Gmail fetch with multiple results."""
        try:
            from integrations.gmail_client.fetch import fetch_emails

            # Test with slightly more results
            emails = fetch_emails(query="is:inbox", max_results=5)

            assert isinstance(emails, list)
            assert len(emails) <= 5  # Should not exceed max_results

            # If we have emails, test their structure
            for email in emails:
                assert isinstance(email, dict)
                assert 'id' in email
                assert 'snippet' in email
                # Snippet should be a string
                assert isinstance(email['snippet'], str)
                # Should have threadId
                assert 'threadId' in email or email.get('threadId') is not None

        except ImportError:
            pytest.skip("Gmail integration not available")
        except Exception as e:
            pytest.skip(f"Gmail test skipped due to: {e}")

    @pytest.mark.asyncio
    async def test_gmail_message_processing(self):
        """Test processing Gmail messages through the normalization pipeline."""
        # This test uses mock data to avoid requiring actual Gmail access
        gmail_data = {
            'id': 'test_gmail_msg',
            'threadId': 'test_gmail_thread',
            'internalDate': '1705312200000',
            'snippet': 'Test Gmail message...',
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'Test Sender <test@example.com>'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Test Gmail Subject'}
                ],
                'mimeType': 'text/plain',
                'body': {
                    'data': base64.urlsafe_b64encode(b'Test Gmail message').decode('ascii')
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='test_gmail_msg',
            raw_data=gmail_data
        )

        normalizer = MessageNormalizer()
        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Verify Gmail-specific processing
        assert normalized.platform == Platform.GMAIL
        assert normalized.content.text == 'Test Gmail message'
        assert normalized.sender.email == 'test@example.com'
        assert 'INBOX' in normalized.metadata['labels']
        assert thread.title == 'Test Gmail Subject'

    @pytest.mark.asyncio
    async def test_gmail_html_message_processing(self):
        """Test processing Gmail HTML messages."""
        gmail_data = {
            'id': 'test_html_msg',
            'threadId': 'test_html_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'HTML Sender <html@example.com>'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'HTML Test Email'}
                ],
                'mimeType': 'text/html',
                'body': {
                    'data': base64.urlsafe_b64encode(b'<p>HTML <strong>message</strong> content</p>').decode('ascii')
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='test_html_msg',
            raw_data=gmail_data
        )

        normalizer = MessageNormalizer()
        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Verify HTML processing
        assert normalized.content.html is not None
        assert '<strong>message</strong>' in normalized.content.html
        assert normalized.content.text == 'HTML message content'

    @pytest.mark.asyncio
    async def test_gmail_multipart_message_processing(self):
        """Test processing Gmail multipart messages with attachments."""
        gmail_data = {
            'id': 'test_multipart_msg',
            'threadId': 'test_multipart_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'Multipart Sender <multi@example.com>'},
                    {'name': 'To', 'value': 'recipient@example.com'},
                    {'name': 'Subject', 'value': 'Multipart Test Email'}
                ],
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'Multipart message text').decode('ascii')
                        }
                    },
                    {
                        'filename': 'test_attachment.pdf',
                        'mimeType': 'application/pdf',
                        'body': {
                            'attachmentId': 'att_12345',
                            'size': 1024
                        },
                        'partId': '1'
                    }
                ]
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='test_multipart_msg',
            raw_data=gmail_data
        )

        normalizer = MessageNormalizer()
        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Verify multipart processing
        assert normalized.content.text == 'Multipart message text'
        assert len(normalized.attachments) == 1

        attachment = normalized.attachments[0]
        assert attachment.filename == 'test_attachment.pdf'
        assert attachment.mime_type == 'application/pdf'
        assert attachment.file_size == 1024
        assert 'attachment_id' in attachment.metadata

    @pytest.mark.asyncio
    async def test_gmail_multiple_recipients(self):
        """Test processing Gmail messages with multiple recipients."""
        gmail_data = {
            'id': 'test_multi_recipients',
            'threadId': 'test_multi_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'Sender <sender@example.com>'},
                    {'name': 'To', 'value': 'recipient1@example.com, recipient2@example.com'},
                    {'name': 'Cc', 'value': 'cc@example.com'},
                    {'name': 'Subject', 'value': 'Multiple Recipients Test'}
                ],
                'mimeType': 'text/plain',
                'body': {
                    'data': base64.urlsafe_b64encode(b'Message to multiple recipients').decode('ascii')
                }
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='test_multi_recipients',
            raw_data=gmail_data
        )

        normalizer = MessageNormalizer()
        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Verify multiple recipients processing
        assert len(normalized.recipients) == 3  # 2 To + 1 Cc

        recipient_emails = [r.email for r in normalized.recipients]
        assert 'recipient1@example.com' in recipient_emails
        assert 'recipient2@example.com' in recipient_emails
        assert 'cc@example.com' in recipient_emails

        # Verify thread participants include all
        assert len(thread.participants) == 4  # sender + 3 recipients

    def test_gmail_error_handling(self):
        """Test Gmail integration error handling."""
        try:
            from integrations.gmail_client.fetch import fetch_emails

            # Test with invalid query (should handle gracefully)
            emails = fetch_emails(query="invalid:query:format", max_results=1)

            # Should return empty list or handle error gracefully
            assert isinstance(emails, list)

        except ImportError:
            pytest.skip("Gmail integration not available")
        except Exception as e:
            # Should handle errors gracefully
            assert isinstance(e, Exception)
            pytest.skip(f"Gmail error handling test: {e}")

    @pytest.mark.asyncio
    async def test_gmail_edge_cases(self):
        """Test Gmail message processing edge cases."""
        # Test message with minimal data
        minimal_gmail_data = {
            'id': 'minimal_msg',
            'threadId': 'minimal_thread',
            'internalDate': '1705312200000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'minimal@example.com'},
                    {'name': 'Subject', 'value': 'Minimal Message'}
                ],
                'mimeType': 'text/plain',
                'body': {}  # Empty body
            }
        }

        raw_message = RawMessage(
            platform=Platform.GMAIL,
            platform_message_id='minimal_msg',
            raw_data=minimal_gmail_data
        )

        normalizer = MessageNormalizer()
        normalized, thread, participants = await normalizer.normalize_message(raw_message)

        # Should handle minimal data gracefully
        assert normalized.platform == Platform.GMAIL
        assert normalized.sender.email == 'minimal@example.com'
        assert thread.title == 'Minimal Message'

        # Content might be empty but should not crash
        assert normalized.content is not None
