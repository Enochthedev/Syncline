"""
Unified message schema data classes for platform-agnostic message representation.

This module defines the core data structures used throughout the MESH system
for representing normalized messages, threads, and participants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import uuid


class Platform(str, Enum):
    """Supported messaging platforms."""
    GMAIL = "gmail"
    SLACK = "slack"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    TWITTER = "twitter"
    TELEGRAM = "telegram"
    GOOGLE_CHAT = "google_chat"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"


class ContentType(str, Enum):
    """Message content types."""
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
    RICH_TEXT = "rich_text"


class AttachmentType(str, Enum):
    """Attachment types based on MIME categories."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    OTHER = "other"


@dataclass
class MessageContent:
    """Normalized message content with multiple format representations."""
    text: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    primary_format: ContentType = ContentType.TEXT

    def get_primary_content(self) -> Optional[str]:
        """Get content in the primary format."""
        if self.primary_format == ContentType.TEXT:
            return self.text
        elif self.primary_format == ContentType.HTML:
            return self.html
        elif self.primary_format == ContentType.MARKDOWN:
            return self.markdown
        return self.text  # Fallback to text

    def has_content(self) -> bool:
        """Check if any content is available."""
        return bool(self.text or self.html or self.markdown)


@dataclass
class Attachment:
    """Normalized attachment representation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    cleaned_mime_type: Optional[str] = None
    file_size: Optional[int] = None
    storage_path: Optional[str] = None
    storage_url: Optional[str] = None
    content_hash: Optional[str] = None
    thumbnail_path: Optional[str] = None
    attachment_type: AttachmentType = AttachmentType.OTHER
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization processing."""
        if self.mime_type and not self.cleaned_mime_type:
            self.cleaned_mime_type = self._clean_mime_type(self.mime_type)
            self.attachment_type = self._determine_attachment_type(
                self.cleaned_mime_type)

    def _clean_mime_type(self, mime_type: str) -> str:
        """Clean and normalize MIME type."""
        # Remove parameters and normalize
        cleaned = mime_type.split(';')[0].strip().lower()

        # Common MIME type corrections
        mime_corrections = {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel': 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint': 'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        }

        return mime_corrections.get(cleaned, cleaned)

    def _determine_attachment_type(self, mime_type: str) -> AttachmentType:
        """Determine attachment type from MIME type."""
        if mime_type.startswith('image/'):
            return AttachmentType.IMAGE
        elif mime_type.startswith('video/'):
            return AttachmentType.VIDEO
        elif mime_type.startswith('audio/'):
            return AttachmentType.AUDIO
        elif mime_type in [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'text/csv',
            'application/rtf'
        ]:
            return AttachmentType.DOCUMENT
        elif mime_type in [
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed',
            'application/gzip',
            'application/x-tar'
        ]:
            return AttachmentType.ARCHIVE
        else:
            return AttachmentType.OTHER


@dataclass
class Participant:
    """Normalized participant representation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: Platform = Platform.GMAIL
    platform_user_id: str = ""
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_identifier(self) -> str:
        """Get the best available identifier for the participant."""
        return (
            self.email or
            self.display_name or
            self.platform_user_id or
            f"unknown_{self.id[:8]}"
        )

    def get_display_name(self) -> str:
        """Get the best available display name."""
        return (
            self.display_name or
            self.email or
            self.platform_user_id or
            f"User {self.id[:8]}"
        )


@dataclass
class Thread:
    """Normalized thread representation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: Platform = Platform.GMAIL
    platform_thread_id: str = ""
    title: Optional[str] = None
    participants: List[str] = field(default_factory=list)  # Participant IDs
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_participant(self, participant_id: str) -> None:
        """Add a participant to the thread if not already present."""
        if participant_id not in self.participants:
            self.participants.append(participant_id)

    def get_title(self) -> str:
        """Get thread title or generate one."""
        if self.title:
            return self.title

        if len(self.participants) <= 2:
            return "Direct Message"
        else:
            return f"Group Chat ({len(self.participants)} participants)"


@dataclass
class NormalizedMessage:
    """
    Unified message representation across all platforms.

    This is the core data structure that represents a message after
    platform-specific normalization has been applied.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: Platform = Platform.GMAIL
    platform_message_id: str = ""
    thread_id: str = ""
    sender: Participant = field(default_factory=Participant)
    recipients: List[Participant] = field(default_factory=list)
    content: MessageContent = field(default_factory=MessageContent)
    attachments: List[Attachment] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def has_attachments(self) -> bool:
        """Check if message has attachments."""
        return len(self.attachments) > 0

    def get_attachment_count(self) -> int:
        """Get number of attachments."""
        return len(self.attachments)

    def get_attachments_by_type(self, attachment_type: AttachmentType) -> List[Attachment]:
        """Get attachments of a specific type."""
        return [att for att in self.attachments if att.attachment_type == attachment_type]

    def get_content_preview(self, max_length: int = 200) -> str:
        """Get a preview of the message content."""
        content = self.content.get_primary_content()
        if not content:
            if self.has_attachments():
                return f"[{self.get_attachment_count()} attachment(s)]"
            return "[No content]"

        if len(content) <= max_length:
            return content

        return content[:max_length - 3] + "..."

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'platform': self.platform.value,
            'platform_message_id': self.platform_message_id,
            'thread_id': self.thread_id,
            'sender': {
                'id': self.sender.id,
                'platform': self.sender.platform.value,
                'platform_user_id': self.sender.platform_user_id,
                'display_name': self.sender.display_name,
                'email': self.sender.email,
                'phone': self.sender.phone,
                'avatar_url': self.sender.avatar_url,
                'metadata': self.sender.metadata
            },
            'recipients': [
                {
                    'id': recipient.id,
                    'platform': recipient.platform.value,
                    'platform_user_id': recipient.platform_user_id,
                    'display_name': recipient.display_name,
                    'email': recipient.email,
                    'phone': recipient.phone,
                    'avatar_url': recipient.avatar_url,
                    'metadata': recipient.metadata
                }
                for recipient in self.recipients
            ],
            'content': {
                'text': self.content.text,
                'html': self.content.html,
                'markdown': self.content.markdown,
                'primary_format': self.content.primary_format.value
            },
            'attachments': [
                {
                    'id': att.id,
                    'filename': att.filename,
                    'original_filename': att.original_filename,
                    'mime_type': att.mime_type,
                    'cleaned_mime_type': att.cleaned_mime_type,
                    'file_size': att.file_size,
                    'storage_path': att.storage_path,
                    'storage_url': att.storage_url,
                    'content_hash': att.content_hash,
                    'thumbnail_path': att.thumbnail_path,
                    'attachment_type': att.attachment_type.value,
                    'metadata': att.metadata
                }
                for att in self.attachments
            ],
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'raw_data': self.raw_data
        }


@dataclass
class RawMessage:
    """
    Raw message data from external platforms before normalization.

    This represents the original message data as received from
    platform APIs before any processing or normalization.
    """
    platform: Platform
    platform_message_id: str
    raw_data: Dict[str, Any]
    received_at: datetime = field(default_factory=datetime.utcnow)

    def get_platform_data(self, key: str, default: Any = None) -> Any:
        """Safely get data from raw platform data."""
        return self.raw_data.get(key, default)
