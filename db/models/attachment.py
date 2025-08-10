"""Attachment model for message files and media."""

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base

class Attachment(Base):
    """Attachment model for message files and media."""
    __tablename__ = "attachments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    
    # File information
    filename = Column(String(500))
    original_filename = Column(String(500))
    mime_type = Column(String(100))
    file_size = Column(Integer)  # Size in bytes
    
    # Storage information
    storage_path = Column(String(1000))  # Path in blob storage
    storage_url = Column(String(1000))   # Public URL if available
    
    # Content information
    content_hash = Column(String(64))    # SHA-256 hash for deduplication
    thumbnail_path = Column(String(1000))  # Thumbnail for images/videos
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Metadata
    attachment_metadata = Column(JSON)  # Platform-specific attachment data, dimensions, etc.
    
    # Relationships
    message = relationship("Message", back_populates="attachments")
    
    __table_args__ = (
        Index('ix_attachments_message', 'message_id'),
        Index('ix_attachments_mime_type', 'mime_type'),
        Index('ix_attachments_hash', 'content_hash'),
        Index('ix_attachments_filename', 'filename'),
    )