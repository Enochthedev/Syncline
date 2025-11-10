"""
Raw Message Model

Stores unprocessed messages from platforms in their original format.
"""

from sqlalchemy import Column, String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from db.base import Base


class RawMessage(Base):
    """
    Raw message model for collection stage.
    
    Stores messages in their original platform-specific format
    before normalization.
    
    Attributes:
        connection_id: Foreign key to PlatformConnection
        platform: Platform name (denormalized for queries)
        platform_message_id: Platform's unique message identifier
        raw_data: Complete message data from platform (JSONB)
        processed: Whether message has been normalized
        connection: Related platform connection
        message: Related normalized message (after processing)
    """
    
    __tablename__ = "raw_messages"
    
    # Foreign key to platform connection
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Platform information (denormalized for performance)
    platform = Column(String(50), nullable=False, index=True)
    
    # Platform's unique message ID
    platform_message_id = Column(String(255), nullable=False, index=True)
    
    # Complete raw message data from platform
    # Structure varies by platform, examples:
    # Gmail: {"id": "...", "threadId": "...", "payload": {...}, ...}
    # Slack: {"type": "message", "channel": "...", "user": "...", "text": "...", ...}
    # Discord: {"id": "...", "channel_id": "...", "author": {...}, "content": "...", ...}
    raw_data = Column(JSONB, nullable=False)
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    connection = relationship("PlatformConnection", back_populates="raw_messages")
    message = relationship(
        "Message",
        back_populates="raw_message",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Unique constraint: one message per platform per connection
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "platform_message_id",
            name="uq_connection_platform_message"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<RawMessage(id={self.id}, platform={self.platform}, processed={self.processed})>"
