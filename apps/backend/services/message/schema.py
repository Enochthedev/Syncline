"""
Unified message schema using Pydantic models.

This module defines the core data structures for representing normalized
messages across all platforms with validation and serialization support.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Platform(str, Enum):
    """Supported messaging platforms."""

    GMAIL = "gmail"
    SLACK = "slack"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    TWITTER = "twitter"
    TELEGRAM = "telegram"


class ContentFormat(str, Enum):
    """Message content format types."""

    PLAIN = "plain"
    HTML = "html"
    MARKDOWN = "markdown"


class MessageContent(BaseModel):
    """
    Normalized message content with multiple format representations.

    Attributes:
        text: Plain text content
        html: HTML formatted content (optional)
        format: Primary content format
    """

    text: Optional[str] = Field(None, description="Plain text content")
    html: Optional[str] = Field(None, description="HTML formatted content")
    format: ContentFormat = Field(
        default=ContentFormat.PLAIN, description="Primary content format"
    )

    @field_validator("text", "html")
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean content strings."""
        if v is not None:
            # Strip leading/trailing whitespace
            v = v.strip()
            # Return None if empty after stripping
            return v if v else None
        return v

    @model_validator(mode="after")
    def validate_has_content(self) -> "MessageContent":
        """Ensure at least one content field is present."""
        if not self.text and not self.html:
            raise ValueError("At least one of text or html must be provided")
        return self

    def get_primary_content(self) -> str:
        """Get content in the primary format."""
        if self.format == ContentFormat.HTML and self.html:
            return self.html
        return self.text or ""

    def has_content(self) -> bool:
        """Check if any content is available."""
        return bool(self.text or self.html)


class MessageSender(BaseModel):
    """
    Message sender information.

    Attributes:
        platform_user_id: Platform-specific user identifier
        name: Display name
        email: Email address (optional)
        phone: Phone number (optional)
    """

    platform_user_id: str = Field(..., description="Platform-specific user ID")
    name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v

    def get_identifier(self) -> str:
        """Get the best available identifier."""
        return self.email or self.name or self.platform_user_id


class MessageRecipient(BaseModel):
    """
    Message recipient information.

    Attributes:
        platform_user_id: Platform-specific user identifier
        name: Display name
        email: Email address (optional)
        phone: Phone number (optional)
    """

    platform_user_id: str = Field(..., description="Platform-specific user ID")
    name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class MessageAttachment(BaseModel):
    """
    Message attachment information.

    Attributes:
        id: Unique attachment identifier
        filename: Original filename
        mime_type: MIME type
        size_bytes: File size in bytes
        storage_path: Path where attachment is stored
    """

    id: UUID = Field(default_factory=uuid4, description="Unique attachment ID")
    filename: str = Field(..., description="Original filename")
    mime_type: Optional[str] = Field(None, description="MIME type")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    storage_path: Optional[str] = Field(None, description="Storage path")

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename is not empty."""
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        return v.strip()


class UnifiedMessage(BaseModel):
    """
    Unified message representation across all platforms.

    This is the core schema for normalized messages after platform-specific
    parsing and cleaning.

    Attributes:
        id: Unique message identifier (generated)
        platform: Source platform
        platform_message_id: Platform's unique message identifier
        thread_id: Platform's thread/conversation identifier
        sender: Message sender information
        recipients: List of message recipients
        content: Message content
        attachments: List of attachments
        metadata: Additional platform-specific metadata
        timestamp: Message timestamp from platform
        collected_at: When message was collected
    """

    id: UUID = Field(default_factory=uuid4, description="Unique message ID")
    platform: Platform = Field(..., description="Source platform")
    platform_message_id: str = Field(..., description="Platform message ID")
    thread_id: Optional[str] = Field(None, description="Thread/conversation ID")
    sender: MessageSender = Field(..., description="Message sender")
    recipients: List[MessageRecipient] = Field(
        default_factory=list, description="Message recipients"
    )
    content: MessageContent = Field(..., description="Message content")
    attachments: List[MessageAttachment] = Field(
        default_factory=list, description="Message attachments"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific metadata"
    )
    timestamp: datetime = Field(..., description="Message timestamp")
    collected_at: datetime = Field(..., description="Collection timestamp")

    @field_validator("platform_message_id")
    @classmethod
    def validate_platform_message_id(cls, v: str) -> str:
        """Validate platform message ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Platform message ID cannot be empty")
        return v.strip()

    def has_attachments(self) -> bool:
        """Check if message has attachments."""
        return len(self.attachments) > 0

    def get_attachment_count(self) -> int:
        """Get number of attachments."""
        return len(self.attachments)

    def get_content_preview(self, max_length: int = 200) -> str:
        """Get a preview of the message content."""
        content_text = self.content.text or ""

        if not content_text:
            if self.has_attachments():
                return f"[{self.get_attachment_count()} attachment(s)]"
            return "[No content]"

        if len(content_text) <= max_length:
            return content_text

        return content_text[: max_length - 3] + "..."

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
        use_enum_values = True
