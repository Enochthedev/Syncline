"""
Platform Connection Model

Represents authenticated connections to communication platforms.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from db.base import Base


class PlatformType(str, enum.Enum):
    """Supported communication platforms."""
    GMAIL = "gmail"
    SLACK = "slack"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    TWITTER = "twitter"
    TELEGRAM = "telegram"


class ConnectionStatus(str, enum.Enum):
    """Connection status states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    FAILED = "failed"
    REVOKED = "revoked"


class PlatformConnection(Base):
    """
    Platform connection model for OAuth and authentication.
    
    Attributes:
        user_id: Foreign key to User
        platform: Platform type (gmail, slack, etc.)
        credentials: Encrypted OAuth credentials (JSONB)
        status: Connection status
        last_sync_at: Last successful sync timestamp
        platform_metadata: Additional platform-specific metadata
        user: Related user
        raw_messages: Related raw messages
    """
    
    __tablename__ = "platform_connections"
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Platform information
    platform = Column(
        SQLEnum(PlatformType, name="platform_type"),
        nullable=False,
        index=True
    )
    
    # Encrypted credentials (OAuth tokens, API keys, etc.)
    # Structure: {
    #   "access_token": "...",
    #   "refresh_token": "...",
    #   "expires_at": "...",
    #   "token_type": "Bearer",
    #   ...
    # }
    credentials = Column(JSONB, nullable=False)
    
    # Connection status
    status = Column(
        SQLEnum(ConnectionStatus, name="connection_status"),
        default=ConnectionStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    # Sync tracking
    last_sync_at = Column(DateTime, nullable=True)
    
    # Platform-specific metadata
    # Structure: {
    #   "platform_user_id": "...",
    #   "platform_username": "...",
    #   "scopes": [...],
    #   ...
    # }
    platform_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="platform_connections")
    raw_messages = relationship(
        "RawMessage",
        back_populates="connection",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<PlatformConnection(id={self.id}, platform={self.platform}, status={self.status})>"
