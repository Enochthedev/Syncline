"""
Platform-specific message parsers.

This module contains parsers for each supported platform that convert
platform-specific message formats to the unified message schema.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .content_processor import ContentProcessor
from .schema import (
    ContentFormat,
    MessageAttachment,
    MessageContent,
    MessageRecipient,
    MessageSender,
    Platform,
    UnifiedMessage,
)

logger = logging.getLogger(__name__)


class BasePlatformParser(ABC):
    """
    Abstract base class for platform-specific message parsers.

    Each platform parser implements the parse method to convert
    platform-specific message data to the unified format.
    """

    def __init__(self, content_processor: ContentProcessor):
        """
        Initialize the parser.

        Args:
            content_processor: Content processor for cleaning and conversion
        """
        self.content_processor = content_processor

    @abstractmethod
    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """
        Parse platform-specific message data to unified format.

        Args:
            raw_data: Raw message data from platform
            platform_message_id: Platform's message identifier
            collected_at: When the message was collected

        Returns:
            Unified message
        """
        pass

    def _safe_get(self, data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """
        Safely get nested dictionary values.

        Args:
            data: Dictionary to search
            *keys: Sequence of keys to traverse
            default: Default value if key not found

        Returns:
            Value at the key path or default
        """
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current if current is not None else default


class GmailParser(BasePlatformParser):
    """Parser for Gmail messages."""

    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """Parse Gmail message to unified format."""
        try:
            # Extract payload
            payload = raw_data.get("payload", {})
            headers = {
                h["name"].lower(): h["value"] for h in payload.get("headers", [])
            }

            # Extract sender
            from_header = headers.get("from", "")
            sender = self._parse_email_address(from_header)

            # Extract recipients
            to_header = headers.get("to", "")
            cc_header = headers.get("cc", "")
            recipients = []
            for addr in self._parse_email_list(to_header):
                recipients.append(addr)
            for addr in self._parse_email_list(cc_header):
                recipients.append(addr)

            # Extract content
            content = self._extract_gmail_content(payload)

            # Extract attachments
            attachments = self._extract_gmail_attachments(payload)

            # Parse timestamp
            timestamp = datetime.fromtimestamp(
                int(raw_data.get("internalDate", 0)) / 1000
            )

            # Build metadata
            metadata = {
                "thread_id": raw_data.get("threadId"),
                "labels": raw_data.get("labelIds", []),
                "subject": headers.get("subject"),
                "snippet": raw_data.get("snippet"),
            }

            return UnifiedMessage(
                platform=Platform.GMAIL,
                platform_message_id=platform_message_id,
                thread_id=raw_data.get("threadId"),
                sender=sender,
                recipients=recipients,
                content=content,
                attachments=attachments,
                metadata=metadata,
                timestamp=timestamp,
                collected_at=collected_at,
            )

        except Exception as e:
            logger.error(f"Gmail parsing failed: {e}")
            raise

    def _parse_email_address(self, email_str: str) -> MessageSender:
        """Parse email address string to MessageSender."""
        import re

        # Try to extract name and email from "Name <email@example.com>" format
        match = re.match(r"([^<]+)<([^>]+)>", email_str)
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
        else:
            name = None
            email = email_str.strip()

        return MessageSender(platform_user_id=email, name=name, email=email)

    def _parse_email_list(self, email_str: str) -> List[MessageRecipient]:
        """Parse comma-separated email list."""
        if not email_str:
            return []

        import re

        recipients = []

        # Split by comma, handling "Name <email>" format
        for part in email_str.split(","):
            part = part.strip()
            if not part:
                continue

            match = re.match(r"([^<]+)<([^>]+)>", part)
            if match:
                name = match.group(1).strip().strip('"')
                email = match.group(2).strip()
            else:
                name = None
                email = part

            recipients.append(
                MessageRecipient(platform_user_id=email, name=name, email=email)
            )

        return recipients

    def _extract_gmail_content(self, payload: Dict) -> MessageContent:
        """Extract content from Gmail payload."""
        text_content = ""
        html_content = ""

        # Check for multipart message
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                body = part.get("body", {})
                data = body.get("data", "")

                if mime_type == "text/plain" and data:
                    import base64

                    text_content = base64.urlsafe_b64decode(data).decode("utf-8")
                elif mime_type == "text/html" and data:
                    import base64

                    html_content = base64.urlsafe_b64decode(data).decode("utf-8")
        else:
            # Single part message
            body = payload.get("body", {})
            data = body.get("data", "")
            if data:
                import base64

                decoded = base64.urlsafe_b64decode(data).decode("utf-8")
                mime_type = payload.get("mimeType", "")
                if "html" in mime_type:
                    html_content = decoded
                else:
                    text_content = decoded

        # Clean content
        if html_content:
            html_content = self.content_processor.clean_html(html_content)
            if not text_content:
                text_content = self.content_processor.html_to_text(html_content)

        if text_content:
            text_content = self.content_processor.clean_text(text_content)

        return MessageContent(
            text=text_content or None,
            html=html_content or None,
            format=ContentFormat.HTML if html_content else ContentFormat.PLAIN,
        )

    def _extract_gmail_attachments(self, payload: Dict) -> List[MessageAttachment]:
        """Extract attachments from Gmail payload."""
        attachments = []

        if "parts" in payload:
            for part in payload.get("parts", []):
                filename = part.get("filename")
                if filename:
                    attachments.append(
                        MessageAttachment(
                            filename=filename,
                            mime_type=part.get("mimeType"),
                            size_bytes=part.get("body", {}).get("size"),
                        )
                    )

        return attachments


class SlackParser(BasePlatformParser):
    """Parser for Slack messages."""

    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """Parse Slack message to unified format."""
        try:
            # Extract sender
            user_id = raw_data.get("user", "")
            username = raw_data.get("username", user_id)

            sender = MessageSender(platform_user_id=user_id, name=username)

            # Extract content
            text = raw_data.get("text", "")
            text = self.content_processor.clean_text(text)

            content = MessageContent(text=text, format=ContentFormat.MARKDOWN)

            # Extract attachments
            attachments = []
            for file_data in raw_data.get("files", []):
                attachments.append(
                    MessageAttachment(
                        filename=file_data.get("name", "unknown"),
                        mime_type=file_data.get("mimetype"),
                        size_bytes=file_data.get("size"),
                    )
                )

            # Parse timestamp
            ts = float(raw_data.get("ts", 0))
            timestamp = datetime.fromtimestamp(ts) if ts else collected_at

            # Build metadata
            metadata = {
                "channel": raw_data.get("channel"),
                "thread_ts": raw_data.get("thread_ts"),
                "reactions": raw_data.get("reactions", []),
            }

            return UnifiedMessage(
                platform=Platform.SLACK,
                platform_message_id=platform_message_id,
                thread_id=raw_data.get("thread_ts") or raw_data.get("ts"),
                sender=sender,
                content=content,
                attachments=attachments,
                metadata=metadata,
                timestamp=timestamp,
                collected_at=collected_at,
            )

        except Exception as e:
            logger.error(f"Slack parsing failed: {e}")
            raise


class DiscordParser(BasePlatformParser):
    """Parser for Discord messages."""

    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """Parse Discord message to unified format."""
        try:
            # Extract sender
            author = raw_data.get("author", {})
            sender = MessageSender(
                platform_user_id=author.get("id", ""),
                name=author.get("username"),
                email=author.get("email"),
            )

            # Extract content
            text = raw_data.get("content", "")
            text = self.content_processor.clean_text(text)

            content = MessageContent(text=text, format=ContentFormat.MARKDOWN)

            # Extract attachments
            attachments = []
            for att_data in raw_data.get("attachments", []):
                attachments.append(
                    MessageAttachment(
                        filename=att_data.get("filename", "unknown"),
                        mime_type=att_data.get("content_type"),
                        size_bytes=att_data.get("size"),
                    )
                )

            # Parse timestamp
            timestamp_str = raw_data.get("timestamp")
            timestamp = (
                datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timestamp_str
                else collected_at
            )

            # Build metadata
            metadata = {
                "channel_id": raw_data.get("channel_id"),
                "guild_id": raw_data.get("guild_id"),
                "mentions": raw_data.get("mentions", []),
                "reactions": raw_data.get("reactions", []),
            }

            return UnifiedMessage(
                platform=Platform.DISCORD,
                platform_message_id=platform_message_id,
                thread_id=raw_data.get("channel_id"),
                sender=sender,
                content=content,
                attachments=attachments,
                metadata=metadata,
                timestamp=timestamp,
                collected_at=collected_at,
            )

        except Exception as e:
            logger.error(f"Discord parsing failed: {e}")
            raise


class WhatsAppParser(BasePlatformParser):
    """Parser for WhatsApp messages."""

    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """Parse WhatsApp message to unified format."""
        try:
            # Extract sender
            sender_data = raw_data.get("sender", {})
            sender = MessageSender(
                platform_user_id=sender_data.get("id", ""),
                name=sender_data.get("name"),
                phone=sender_data.get("phone"),
            )

            # Extract content
            text = raw_data.get("body", "")
            text = self.content_processor.clean_text(text)

            content = MessageContent(text=text, format=ContentFormat.PLAIN)

            # Extract attachments
            attachments = []
            if raw_data.get("hasMedia"):
                media = raw_data.get("media", {})
                attachments.append(
                    MessageAttachment(
                        filename=media.get("filename", "media"),
                        mime_type=media.get("mimetype"),
                        size_bytes=media.get("filesize"),
                    )
                )

            # Parse timestamp
            timestamp = datetime.fromtimestamp(raw_data.get("timestamp", 0))

            # Build metadata
            metadata = {
                "chat_id": raw_data.get("chatId"),
                "from_me": raw_data.get("fromMe", False),
            }

            return UnifiedMessage(
                platform=Platform.WHATSAPP,
                platform_message_id=platform_message_id,
                thread_id=raw_data.get("chatId"),
                sender=sender,
                content=content,
                attachments=attachments,
                metadata=metadata,
                timestamp=timestamp,
                collected_at=collected_at,
            )

        except Exception as e:
            logger.error(f"WhatsApp parsing failed: {e}")
            raise


class TwitterParser(BasePlatformParser):
    """Parser for Twitter messages."""

    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """Parse Twitter message to unified format."""
        try:
            # Extract sender
            user = raw_data.get("user", {})
            sender = MessageSender(
                platform_user_id=user.get("id_str", ""),
                name=user.get("name"),
            )

            # Extract content
            text = raw_data.get("text", "")
            text = self.content_processor.clean_text(text)

            content = MessageContent(text=text, format=ContentFormat.PLAIN)

            # Extract attachments (media)
            attachments = []
            for media in raw_data.get("entities", {}).get("media", []):
                attachments.append(
                    MessageAttachment(
                        filename=media.get("media_url", "").split("/")[-1],
                        mime_type=f"image/{media.get('type', 'jpeg')}",
                    )
                )

            # Parse timestamp
            created_at = raw_data.get("created_at")
            timestamp = (
                datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                if created_at
                else collected_at
            )

            # Build metadata
            metadata = {
                "in_reply_to": raw_data.get("in_reply_to_status_id_str"),
                "retweet_count": raw_data.get("retweet_count"),
                "favorite_count": raw_data.get("favorite_count"),
            }

            return UnifiedMessage(
                platform=Platform.TWITTER,
                platform_message_id=platform_message_id,
                thread_id=raw_data.get("in_reply_to_status_id_str"),
                sender=sender,
                content=content,
                attachments=attachments,
                metadata=metadata,
                timestamp=timestamp,
                collected_at=collected_at,
            )

        except Exception as e:
            logger.error(f"Twitter parsing failed: {e}")
            raise


class TelegramParser(BasePlatformParser):
    """Parser for Telegram messages."""

    def parse(
        self, raw_data: Dict[str, Any], platform_message_id: str, collected_at: datetime
    ) -> UnifiedMessage:
        """Parse Telegram message to unified format."""
        try:
            # Extract sender
            from_user = raw_data.get("from", {})
            sender = MessageSender(
                platform_user_id=str(from_user.get("id", "")),
                name=from_user.get("first_name"),
            )

            # Extract content
            text = raw_data.get("text", "")
            text = self.content_processor.clean_text(text)

            content = MessageContent(text=text, format=ContentFormat.PLAIN)

            # Extract attachments
            attachments = []
            if "document" in raw_data:
                doc = raw_data["document"]
                attachments.append(
                    MessageAttachment(
                        filename=doc.get("file_name", "document"),
                        mime_type=doc.get("mime_type"),
                        size_bytes=doc.get("file_size"),
                    )
                )

            # Parse timestamp
            timestamp = datetime.fromtimestamp(raw_data.get("date", 0))

            # Build metadata
            metadata = {
                "chat_id": raw_data.get("chat", {}).get("id"),
                "message_thread_id": raw_data.get("message_thread_id"),
            }

            return UnifiedMessage(
                platform=Platform.TELEGRAM,
                platform_message_id=platform_message_id,
                thread_id=str(raw_data.get("message_thread_id", "")),
                sender=sender,
                content=content,
                attachments=attachments,
                metadata=metadata,
                timestamp=timestamp,
                collected_at=collected_at,
            )

        except Exception as e:
            logger.error(f"Telegram parsing failed: {e}")
            raise
