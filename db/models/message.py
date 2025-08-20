import uuid
from sqlalchemy import Column, ForeignKey, String, Text, Enum, DateTime, JSON, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base
import enum


class Platform(str, enum.Enum):
    """Supported messaging platforms."""
    gmail = "gmail"
    slack = "slack"
    discord = "discord"
    whatsapp = "whatsapp"
    twitter = "twitter"
    telegram = "telegram"
    google_chat = "google_chat"
    linkedin = "linkedin"
    instagram = "instagram"


class Message(Base):
    """Core message model with unified schema across platforms."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False,
                       index=True)  # Multi-tenant isolation
    platform = Column(String(50), nullable=False)
    platform_message_id = Column(String(255), nullable=False)
    thread_id = Column(UUID(as_uuid=True), ForeignKey(
        "threads.id"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey(
        "participants.id"), nullable=False)

    # Content fields
    content_text = Column(Text)
    content_html = Column(Text)
    content_markdown = Column(Text)

    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata and raw data
    message_metadata = Column(JSON)  # Platform-specific metadata
    raw_data = Column(JSON)  # Original platform data

    # Relationships
    thread = relationship("Thread", back_populates="messages")
    sender = relationship("Participant", back_populates="sent_messages")
    attachments = relationship(
        "Attachment", back_populates="message", cascade="all, delete-orphan")
    entities = relationship(
        "MessageEntity", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'platform', 'platform_message_id',
                         name='uq_tenant_platform_message'),
        Index('ix_messages_tenant_id', 'tenant_id'),
        Index('ix_messages_tenant_thread_timestamp',
              'tenant_id', 'thread_id', 'timestamp'),
        Index('ix_messages_tenant_sender_timestamp',
              'tenant_id', 'sender_id', 'timestamp'),
        Index('ix_messages_tenant_platform_timestamp',
              'tenant_id', 'platform', 'timestamp'),
    )
