"""
Message normalization service for converting platform-specific messages to unified schema.

This service handles the conversion of raw messages from different platforms
into the standardized NormalizedMessage format used throughout the MESH system.
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import logging

from services.message_schema import (
    RawMessage, NormalizedMessage, MessageContent, Attachment, Participant, Thread,
    Platform, ContentType, AttachmentType
)
from services.blob_storage import BlobStorageManager, get_default_storage_manager
from utils.mime_utils import clean_mime_type, resolve_mime_type, is_safe_mime_type

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Handles content cleaning and format conversion."""

    @staticmethod
    def clean_html(html_content: str) -> str:
        """Clean HTML content by removing dangerous tags and normalizing."""
        if not html_content:
            return ""

        # Remove script and style tags completely
        html_content = re.sub(
            r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(
            r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

        # Remove dangerous attributes
        html_content = re.sub(
            r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'\s*javascript\s*:', '',
                              html_content, flags=re.IGNORECASE)

        # Normalize whitespace
        html_content = re.sub(r'\s+', ' ', html_content).strip()

        return html_content

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """Convert HTML to plain text."""
        if not html_content:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)

        # Decode HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
        }

        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def html_to_markdown(html_content: str) -> str:
        """Convert HTML to Markdown (basic conversion)."""
        if not html_content:
            return ""

        markdown = html_content

        # Convert common HTML tags to Markdown
        conversions = [
            (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
            (r'<b[^>]*>(.*?)</b>', r'**\1**'),
            (r'<em[^>]*>(.*?)</em>', r'*\1*'),
            (r'<i[^>]*>(.*?)</i>', r'*\1*'),
            (r'<code[^>]*>(.*?)</code>', r'`\1`'),
            (r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)'),
            (r'<br[^>]*/?>', '\n'),
            (r'<p[^>]*>(.*?)</p>', r'\1\n\n'),
            (r'<h1[^>]*>(.*?)</h1>', r'# \1\n'),
            (r'<h2[^>]*>(.*?)</h2>', r'## \1\n'),
            (r'<h3[^>]*>(.*?)</h3>', r'### \1\n'),
            (r'<li[^>]*>(.*?)</li>', r'- \1\n'),
        ]

        for pattern, replacement in conversions:
            markdown = re.sub(pattern, replacement, markdown,
                              flags=re.DOTALL | re.IGNORECASE)

        # Remove remaining HTML tags
        markdown = re.sub(r'<[^>]+>', '', markdown)

        # Clean up whitespace
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        markdown = markdown.strip()

        return markdown

    @staticmethod
    def standardize_content(content: str, content_type: ContentType) -> MessageContent:
        """Standardize content and generate multiple formats."""
        if not content:
            return MessageContent()

        # Normalize whitespace and remove null characters
        content = re.sub(r'\x00', '', content)  # Remove null bytes
        content = re.sub(r'\r\n', '\n', content)  # Normalize CRLF to LF
        content = re.sub(r'\r', '\n', content)    # Normalize CR to LF
        content = content.strip()

        if not content:
            return MessageContent()

        message_content = MessageContent(primary_format=content_type)

        if content_type == ContentType.HTML:
            message_content.html = ContentProcessor.clean_html(content)
            message_content.text = ContentProcessor.html_to_text(
                message_content.html)
            message_content.markdown = ContentProcessor.html_to_markdown(
                message_content.html)
        elif content_type == ContentType.MARKDOWN:
            message_content.markdown = content.strip()
            # Better markdown to text conversion
            text_content = content
            # Remove markdown formatting but preserve structure
            text_content = re.sub(r'\*\*(.*?)\*\*', r'\1',
                                  text_content)  # Bold
            text_content = re.sub(r'\*(.*?)\*', r'\1',
                                  text_content)      # Italic
            text_content = re.sub(
                r'`(.*?)`', r'\1', text_content)        # Code
            text_content = re.sub(
                r'#{1,6}\s+', '', text_content)         # Headers
            text_content = re.sub(r'\[([^\]]+)\]\([^\)]+\)',
                                  r'\1', text_content)  # Links
            message_content.text = text_content.strip()
            message_content.html = None
        elif content_type == ContentType.RICH_TEXT:
            # Handle rich text format (platform-specific)
            message_content.text = content.strip()
            message_content.html = None
            message_content.markdown = None
        else:  # TEXT or default
            message_content.text = content.strip()
            message_content.html = None
            message_content.markdown = None

        # Ensure we have at least text content
        if not message_content.text and message_content.html:
            message_content.text = ContentProcessor.html_to_text(
                message_content.html)
        elif not message_content.text and message_content.markdown:
            message_content.text = re.sub(
                r'[*_`#\[\]()]', '', message_content.markdown).strip()

        return message_content


class AttachmentProcessor:
    """Handles attachment processing and blob storage integration."""

    def __init__(self, blob_storage_manager: Optional[BlobStorageManager] = None):
        """Initialize with optional blob storage manager."""
        self.blob_storage_manager = blob_storage_manager or get_default_storage_manager()

    def process_attachment(self, attachment_data: Dict[str, Any], message_id: str) -> Attachment:
        """Process raw attachment data into normalized Attachment."""
        attachment = Attachment()

        # Extract basic file information
        attachment.filename = attachment_data.get(
            'filename') or attachment_data.get('name')
        attachment.original_filename = attachment.filename
        raw_mime_type = attachment_data.get(
            'mimeType') or attachment_data.get('content_type')
        attachment.file_size = attachment_data.get(
            'size') or attachment_data.get('file_size')

        # Use improved MIME type processing
        attachment.mime_type = raw_mime_type
        attachment.cleaned_mime_type = resolve_mime_type(
            raw_mime_type, attachment.filename)
        attachment.attachment_type = attachment._determine_attachment_type(
            attachment.cleaned_mime_type)

        # Validate MIME type safety
        if not is_safe_mime_type(attachment.cleaned_mime_type):
            logger.warning(
                f"Potentially unsafe attachment type: {attachment.cleaned_mime_type} "
                f"for file {attachment.filename}"
            )
            attachment.metadata = attachment.metadata or {}
            attachment.metadata['safety_warning'] = 'potentially_unsafe_mime_type'

        # Handle content hash for deduplication
        if 'content' in attachment_data:
            content = attachment_data['content']
            if isinstance(content, bytes):
                attachment.content_hash = hashlib.sha256(content).hexdigest()
            elif isinstance(content, str):
                attachment.content_hash = hashlib.sha256(
                    content.encode('utf-8')).hexdigest()

        # Store platform-specific metadata
        attachment.metadata = attachment.metadata or {}
        attachment.metadata.update({
            'platform_data': attachment_data,
            'processed_at': datetime.utcnow().isoformat(),
            'message_id': message_id
        })

        return attachment

    async def store_attachment(self, attachment: Attachment, content: bytes, message_id: str) -> Attachment:
        """Store attachment in blob storage and update paths."""
        if not self.blob_storage_manager:
            logger.warning(
                "No blob storage manager configured, skipping attachment storage")
            return attachment

        try:
            # Store using blob storage manager
            storage_info = await self.blob_storage_manager.store_attachment(
                content=content,
                filename=attachment.filename or f"attachment_{attachment.id}",
                message_id=message_id,
                content_type=attachment.cleaned_mime_type,
                metadata={
                    'attachment_id': attachment.id,
                    'original_filename': attachment.original_filename,
                    'attachment_type': attachment.attachment_type.value,
                    'processed_at': datetime.utcnow().isoformat()
                }
            )

            # Update attachment with storage information
            attachment.storage_path = storage_info['storage_path']
            attachment.storage_url = storage_info['storage_url']
            attachment.content_hash = storage_info['content_hash']

            # Generate thumbnail for images
            if attachment.attachment_type == AttachmentType.IMAGE:
                thumbnail_path = await self._generate_thumbnail(content, attachment.storage_path)
                attachment.thumbnail_path = thumbnail_path

            logger.info(
                f"Stored attachment {attachment.id} at {attachment.storage_path}")

        except Exception as e:
            logger.error(f"Failed to store attachment {attachment.id}: {e}")
            # Continue without storage - attachment metadata is still preserved
            attachment.metadata = attachment.metadata or {}
            attachment.metadata['storage_error'] = str(e)

        return attachment

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        return ''

    async def _generate_thumbnail(self, content: bytes, storage_path: str) -> Optional[str]:
        """Generate thumbnail for image attachments."""
        # This would integrate with an image processing service
        # For now, return None as placeholder
        return None


class PlatformNormalizers:
    """Platform-specific normalization logic."""

    @staticmethod
    def normalize_gmail_message(raw_message: RawMessage) -> Tuple[NormalizedMessage, Thread, List[Participant]]:
        """Normalize Gmail message data."""
        gmail_data = raw_message.raw_data

        # Extract message metadata
        message_id = gmail_data.get('id', '')
        thread_id = gmail_data.get('threadId', message_id)

        # Parse headers
        headers = {h['name'].lower(): h['value']
                   for h in gmail_data.get('payload', {}).get('headers', [])}

        # Create sender
        sender = Participant(
            platform=Platform.GMAIL,
            platform_user_id=headers.get(
                'from', '').split('<')[-1].rstrip('>'),
            display_name=headers.get('from', '').split('<')[
                0].strip().strip('"'),
            email=headers.get('from', '').split(
                '<')[-1].rstrip('>') if '<' in headers.get('from', '') else headers.get('from', ''),
        )

        # Create recipients
        recipients = []
        for to_header in ['to', 'cc', 'bcc']:
            if to_header in headers:
                for recipient_str in headers[to_header].split(','):
                    recipient_str = recipient_str.strip()
                    if recipient_str:
                        email = recipient_str.split(
                            '<')[-1].rstrip('>') if '<' in recipient_str else recipient_str
                        display_name = recipient_str.split('<')[0].strip().strip(
                            '"') if '<' in recipient_str else None

                        recipient = Participant(
                            platform=Platform.GMAIL,
                            platform_user_id=email,
                            display_name=display_name,
                            email=email,
                        )
                        recipients.append(recipient)

        # Extract content
        content = PlatformNormalizers._extract_gmail_content(
            gmail_data.get('payload', {}))

        # Extract attachments
        attachments = PlatformNormalizers._extract_gmail_attachments(
            gmail_data.get('payload', {}))

        # Create normalized message
        normalized_message = NormalizedMessage(
            platform=Platform.GMAIL,
            platform_message_id=message_id,
            thread_id=thread_id,
            sender=sender,
            recipients=recipients,
            content=content,
            attachments=attachments,
            timestamp=datetime.fromtimestamp(
                int(gmail_data.get('internalDate', 0)) / 1000),
            metadata={
                'labels': gmail_data.get('labelIds', []),
                'snippet': gmail_data.get('snippet', ''),
                'headers': headers
            },
            raw_data=gmail_data
        )

        # Create thread
        thread = Thread(
            platform=Platform.GMAIL,
            platform_thread_id=thread_id,
            title=headers.get('subject', 'No Subject'),
            participants=[sender.id] + [r.id for r in recipients],
            last_message_at=normalized_message.timestamp,
            message_count=1,
            metadata={'subject': headers.get('subject', '')}
        )

        return normalized_message, thread, [sender] + recipients

    @staticmethod
    def _extract_gmail_content(payload: Dict[str, Any]) -> MessageContent:
        """Extract content from Gmail payload."""
        content_text = ""
        content_html = ""

        def extract_parts(part: Dict[str, Any]):
            nonlocal content_text, content_html

            mime_type = part.get('mimeType', '')

            if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                import base64
                decoded = base64.urlsafe_b64decode(
                    part['body']['data']).decode('utf-8')
                content_text += decoded
            elif mime_type == 'text/html' and 'data' in part.get('body', {}):
                import base64
                decoded = base64.urlsafe_b64decode(
                    part['body']['data']).decode('utf-8')
                content_html += decoded

            # Recursively process multipart
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_parts(subpart)

        extract_parts(payload)

        # Determine primary format and standardize
        if content_html:
            return ContentProcessor.standardize_content(content_html, ContentType.HTML)
        elif content_text:
            return ContentProcessor.standardize_content(content_text, ContentType.TEXT)
        else:
            return MessageContent()

    @staticmethod
    def _extract_gmail_attachments(payload: Dict[str, Any]) -> List[Attachment]:
        """Extract attachments from Gmail payload."""
        attachments = []

        def extract_attachment_parts(part: Dict[str, Any]):
            if part.get('filename') and part.get('body', {}).get('attachmentId'):
                raw_mime_type = part.get('mimeType')
                filename = part['filename']

                attachment = Attachment(
                    filename=filename,
                    original_filename=filename,
                    mime_type=raw_mime_type,
                    file_size=part.get('body', {}).get('size'),
                    metadata={
                        'attachment_id': part['body']['attachmentId'],
                        'gmail_part_id': part.get('partId')
                    }
                )

                # Use enhanced MIME type resolution
                attachment.cleaned_mime_type = resolve_mime_type(
                    raw_mime_type, filename)
                attachment.attachment_type = attachment._determine_attachment_type(
                    attachment.cleaned_mime_type)

                attachments.append(attachment)

            # Process multipart
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_attachment_parts(subpart)

        extract_attachment_parts(payload)
        return attachments

    @staticmethod
    def normalize_discord_message(raw_message: RawMessage) -> Tuple[NormalizedMessage, Thread, List[Participant]]:
        """Normalize Discord message data."""
        discord_data = raw_message.raw_data

        # Extract basic info
        message_id = discord_data.get('id', '')
        channel_id = discord_data.get('channel_id', '')
        guild_id = discord_data.get('guild_id', '')

        # Create sender
        author = discord_data.get('author', {})
        sender = Participant(
            platform=Platform.DISCORD,
            platform_user_id=author.get('id', ''),
            display_name=author.get('username', ''),
            avatar_url=f"https://cdn.discordapp.com/avatars/{author.get('id')}/{author.get('avatar')}.png" if author.get(
                'avatar') else None,
            metadata={
                'discriminator': author.get('discriminator'),
                'bot': author.get('bot', False),
                'global_name': author.get('global_name')
            }
        )

        # Extract content
        content = ContentProcessor.standardize_content(
            discord_data.get('content', ''),
            ContentType.MARKDOWN  # Discord uses markdown formatting
        )

        # Extract attachments
        attachments = []
        for attachment_data in discord_data.get('attachments', []):
            attachment = Attachment(
                filename=attachment_data.get('filename'),
                original_filename=attachment_data.get('filename'),
                mime_type=attachment_data.get('content_type'),
                file_size=attachment_data.get('size'),
                storage_url=attachment_data.get('url'),
                metadata={
                    'discord_attachment_id': attachment_data.get('id'),
                    'proxy_url': attachment_data.get('proxy_url'),
                    'width': attachment_data.get('width'),
                    'height': attachment_data.get('height')
                }
            )
            attachments.append(attachment)

        # Handle embeds as additional content
        embeds = discord_data.get('embeds', [])
        if embeds:
            embed_content = []
            for embed in embeds:
                if embed.get('title'):
                    embed_content.append(f"**{embed['title']}**")
                if embed.get('description'):
                    embed_content.append(embed['description'])
                if embed.get('url'):
                    embed_content.append(f"Link: {embed['url']}")

            if embed_content:
                if content.text:
                    content.text += "\n\n" + "\n".join(embed_content)
                else:
                    content.text = "\n".join(embed_content)

        # Create normalized message
        normalized_message = NormalizedMessage(
            platform=Platform.DISCORD,
            platform_message_id=message_id,
            thread_id=f"{guild_id}_{channel_id}" if guild_id else channel_id,
            sender=sender,
            recipients=[],  # Discord messages are channel-based
            content=content,
            attachments=attachments,
            timestamp=datetime.fromisoformat(discord_data.get(
                'timestamp', '').replace('Z', '+00:00')),
            metadata={
                'channel_id': channel_id,
                'guild_id': guild_id,
                'message_type': discord_data.get('type', 0),
                'referenced_message': discord_data.get('referenced_message'),
                'embeds': embeds,
                'reactions': discord_data.get('reactions', [])
            },
            raw_data=discord_data
        )

        # Create thread
        thread = Thread(
            platform=Platform.DISCORD,
            platform_thread_id=f"{guild_id}_{channel_id}" if guild_id else channel_id,
            title=f"Discord Channel {channel_id}",
            participants=[sender.id],
            last_message_at=normalized_message.timestamp,
            message_count=1,
            metadata={
                'channel_id': channel_id,
                'guild_id': guild_id
            }
        )

        return normalized_message, thread, [sender]

    @staticmethod
    def normalize_whatsapp_message(raw_message: RawMessage) -> Tuple[NormalizedMessage, Thread, List[Participant]]:
        """Normalize WhatsApp message data (via Matrix bridge)."""
        whatsapp_data = raw_message.raw_data

        # Extract basic info - WhatsApp via Matrix has specific format
        message_id = whatsapp_data.get('event_id', '')
        room_id = whatsapp_data.get('room_id', '')

        # Extract sender info
        sender_id = whatsapp_data.get('sender', '')
        content_data = whatsapp_data.get('content', {})

        # Create sender
        sender = Participant(
            platform=Platform.WHATSAPP,
            platform_user_id=sender_id,
            display_name=content_data.get('displayname') or sender_id.split(':')[
                0].replace('@', ''),
            metadata={
                'matrix_user_id': sender_id,
                'room_id': room_id
            }
        )

        # Extract content based on message type
        msgtype = content_data.get('msgtype', 'm.text')
        content_text = ""
        attachments = []

        if msgtype == 'm.text':
            content_text = content_data.get('body', '')
        elif msgtype == 'm.image':
            content_text = '[Image]'
            # Handle image attachment
            if content_data.get('url'):
                attachment = Attachment(
                    filename=content_data.get('body', 'image'),
                    mime_type=content_data.get('info', {}).get(
                        'mimetype', 'image/jpeg'),
                    file_size=content_data.get('info', {}).get('size'),
                    storage_url=content_data.get('url'),
                    attachment_type=AttachmentType.IMAGE,
                    metadata={
                        'matrix_url': content_data.get('url'),
                        'width': content_data.get('info', {}).get('w'),
                        'height': content_data.get('info', {}).get('h')
                    }
                )
                attachments.append(attachment)
        elif msgtype in ['m.file', 'm.audio', 'm.video']:
            content_text = content_data.get(
                'body', f'[{msgtype.replace("m.", "").title()}]')
            if content_data.get('url'):
                attachment_type = AttachmentType.OTHER
                if msgtype == 'm.audio':
                    attachment_type = AttachmentType.AUDIO
                elif msgtype == 'm.video':
                    attachment_type = AttachmentType.VIDEO
                elif msgtype == 'm.file':
                    attachment_type = AttachmentType.DOCUMENT

                attachment = Attachment(
                    filename=content_data.get('body', 'file'),
                    mime_type=content_data.get('info', {}).get('mimetype'),
                    file_size=content_data.get('info', {}).get('size'),
                    storage_url=content_data.get('url'),
                    attachment_type=attachment_type,
                    metadata={
                        'matrix_url': content_data.get('url'),
                        'matrix_msgtype': msgtype
                    }
                )
                attachments.append(attachment)

        # Standardize content
        content = ContentProcessor.standardize_content(
            content_text, ContentType.TEXT)

        # Create normalized message
        normalized_message = NormalizedMessage(
            platform=Platform.WHATSAPP,
            platform_message_id=message_id,
            thread_id=room_id,
            sender=sender,
            recipients=[],  # WhatsApp group messages don't have explicit recipients
            content=content,
            attachments=attachments,
            timestamp=datetime.fromtimestamp(
                whatsapp_data.get('origin_server_ts', 0) / 1000),
            metadata={
                'room_id': room_id,
                'msgtype': msgtype,
                'matrix_event_id': message_id,
                'relates_to': content_data.get('m.relates_to')
            },
            raw_data=whatsapp_data
        )

        # Create thread
        thread = Thread(
            platform=Platform.WHATSAPP,
            platform_thread_id=room_id,
            title="WhatsApp Chat",
            participants=[sender.id],
            last_message_at=normalized_message.timestamp,
            message_count=1,
            metadata={'room_id': room_id}
        )

        return normalized_message, thread, [sender]

    @staticmethod
    def normalize_slack_message(raw_message: RawMessage) -> Tuple[NormalizedMessage, Thread, List[Participant]]:
        """Normalize Slack message data."""
        slack_data = raw_message.raw_data

        # Extract basic info
        message_id = slack_data.get('ts', '')
        # Use thread_ts if available
        thread_id = slack_data.get('thread_ts', message_id)
        channel_id = slack_data.get('channel', '')

        # Create sender
        sender = Participant(
            platform=Platform.SLACK,
            platform_user_id=slack_data.get('user', ''),
            display_name=slack_data.get('username') or slack_data.get(
                'user_profile', {}).get('display_name'),
            email=slack_data.get('user_profile', {}).get('email'),
            avatar_url=slack_data.get('user_profile', {}).get('image_72'),
        )

        # Extract content
        content = ContentProcessor.standardize_content(
            slack_data.get('text', ''),
            ContentType.MARKDOWN  # Slack uses markdown-like formatting
        )

        # Extract attachments
        attachments = []
        for file_data in slack_data.get('files', []):
            attachment = Attachment(
                filename=file_data.get('name'),
                original_filename=file_data.get('name'),
                mime_type=file_data.get('mimetype'),
                file_size=file_data.get('size'),
                storage_url=file_data.get('url_private'),
                metadata={'slack_file_id': file_data.get('id')}
            )
            attachments.append(attachment)

        # Create normalized message
        normalized_message = NormalizedMessage(
            platform=Platform.SLACK,
            platform_message_id=message_id,
            # Combine channel and thread
            thread_id=f"{channel_id}_{thread_id}",
            sender=sender,
            recipients=[],  # Slack messages are typically channel-based
            content=content,
            attachments=attachments,
            timestamp=datetime.fromtimestamp(float(slack_data.get('ts', 0))),
            metadata={
                'channel': channel_id,
                'message_type': slack_data.get('type', 'message'),
                'subtype': slack_data.get('subtype'),
            },
            raw_data=slack_data
        )

        # Create thread
        thread = Thread(
            platform=Platform.SLACK,
            platform_thread_id=f"{channel_id}_{thread_id}",
            title=f"Slack Channel {channel_id}",
            participants=[sender.id],
            last_message_at=normalized_message.timestamp,
            message_count=1,
            metadata={'channel_id': channel_id}
        )

        return normalized_message, thread, [sender]


class MessageNormalizer:
    """
    Main message normalization service.

    Converts platform-specific raw messages into the unified NormalizedMessage format
    used throughout the MESH system.
    """

    def __init__(self, attachment_processor: Optional[AttachmentProcessor] = None):
        """Initialize the message normalizer."""
        self.attachment_processor = attachment_processor or AttachmentProcessor()
        self.content_processor = ContentProcessor()

        # Platform-specific normalizers
        self.platform_normalizers = {
            Platform.GMAIL: PlatformNormalizers.normalize_gmail_message,
            Platform.SLACK: PlatformNormalizers.normalize_slack_message,
            Platform.DISCORD: PlatformNormalizers.normalize_discord_message,
            Platform.WHATSAPP: PlatformNormalizers.normalize_whatsapp_message,
            # Add more platforms as needed
        }

    async def normalize_message(self, raw_message: RawMessage) -> Tuple[NormalizedMessage, Thread, List[Participant]]:
        """
        Normalize a raw message from any supported platform.

        Args:
            raw_message: Raw message data from platform API

        Returns:
            Tuple of (normalized_message, thread, participants)

        Raises:
            ValueError: If platform is not supported
        """
        if raw_message.platform not in self.platform_normalizers:
            raise ValueError(f"Unsupported platform: {raw_message.platform}")

        try:
            # Use platform-specific normalizer
            normalizer = self.platform_normalizers[raw_message.platform]
            normalized_message, thread, participants = normalizer(raw_message)

            # Process attachments if any
            if normalized_message.attachments:
                processed_attachments = []
                for attachment in normalized_message.attachments:
                    # Additional processing could be done here
                    processed_attachments.append(attachment)
                normalized_message.attachments = processed_attachments

            logger.info(
                f"Normalized {raw_message.platform} message {normalized_message.platform_message_id} "
                f"with {len(normalized_message.attachments)} attachments"
            )

            return normalized_message, thread, participants

        except Exception as e:
            logger.error(
                f"Failed to normalize {raw_message.platform} message "
                f"{raw_message.platform_message_id}: {e}"
            )
            raise

    def get_supported_platforms(self) -> List[Platform]:
        """Get list of supported platforms."""
        return list(self.platform_normalizers.keys())

    def add_platform_normalizer(self, platform: Platform, normalizer_func):
        """Add a custom platform normalizer."""
        self.platform_normalizers[platform] = normalizer_func
        logger.info(f"Added normalizer for platform: {platform}")
