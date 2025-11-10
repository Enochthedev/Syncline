"""
Message Model

Normalized messages in unified schema across all platforms.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from db.base import Base


class Message(Base):
    """
    Normalized message model with unified schema.
    
    Represents messages from all platforms in a consistent format
    after cleaning and normalization.
    
    Attributes:
        connection_id: Foreign key to PlatformConnection
        raw_message_id: Foreign key to RawMessage
        platform: Platform name (denormalized)
        platform_message_id: Platform's unique message identifier
        thread_id: Platform's thread/conversation identifier
        sender_id: Foreign key to Participant (sender)
        content: Message content (text, html, format)
        message_metadata: Additional message metadata
        timestamp: Message timestamp from platform
        collected_at: When message was collected
        cleaned_at: When message was normalized
        connection: Related platform connection
        raw_message: Related raw message
        sender: Related sender participant
        attachments: Related attachments
        entities: Related extracted entities
        embeddings: Related embeddings
    """
    
    __tablename__ = "messages"
    
    # Foreign keys
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    raw_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Platform information (denormalized)
    platform = Column(String(50), nullable=False, index=True)
    platform_message_id = Column(String(255), nullable=False, index=True)
    
    # Thread/conversation identifier
    thread_id = Column(String(255), nullable=True, index=True)
    
    # Sender (will be linked to Participant model in task 2.3)
    sender_id = Column(
        UUID(as_uuid=True),
        nullable=True,  # Nullable until Participant model is created
        index=True
    )
    
    # Message content
    # Structure: {
    #   "text": "plain text content",
    #   "html": "html content (optional)",
    #   "format": "plain|html|markdown"
    # }
    content = Column(JSONB, nullable=False)
    
    # Additional metadata
    # Structure: {
    #   "platform_specific": {...},
    #   "reactions": [...],
    #   "edited": true/false,
    #   "forwarded": true/false,
    #   "recipients": [...]
    # }
    message_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False)
    cleaned_at = Column(DateTime, nullable=False)
    
    # Relationships
    connection = relationship("PlatformConnection")
    raw_message = relationship("RawMessage", back_populates="message")
    sender = relationship("Participant", foreign_keys=[sender_id])
    attachments = relationship(
        "Attachment",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    entities = relationship(
        "Entity",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "Embedding",
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=False
    )
    
    # Unique constraint: one normalized message per raw message
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "platform_message_id",
            name="uq_connection_normalized_message"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, platform={self.platform}, timestamp={self.timestamp})>"
