"""Participant model for message senders and recipients."""

import uuid
from sqlalchemy import Column, String, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base

class Participant(Base):
    """Participant model for message senders and recipients."""
    __tablename__ = "participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(50), nullable=False)
    platform_user_id = Column(String(255), nullable=False)
    
    # Identity fields
    display_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    avatar_url = Column(String(1000))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    participant_metadata = Column(JSON)  # Platform-specific participant data
    
    # Relationships
    sent_messages = relationship("Message", back_populates="sender")
    
    __table_args__ = (
        UniqueConstraint('platform', 'platform_user_id', name='uq_platform_participant'),
        Index('ix_participants_platform', 'platform'),
        Index('ix_participants_email', 'email'),
        Index('ix_participants_display_name', 'display_name'),
    )