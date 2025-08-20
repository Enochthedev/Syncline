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
    tenant_id = Column(UUID(as_uuid=True), nullable=False,
                       index=True)  # Multi-tenant isolation
    platform = Column(String(50), nullable=False)
    platform_user_id = Column(String(255), nullable=False)

    # Identity fields
    display_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    avatar_url = Column(String(1000))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    participant_metadata = Column(JSON)  # Platform-specific participant data

    # Relationships
    sent_messages = relationship("Message", back_populates="sender")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'platform', 'platform_user_id',
                         name='uq_tenant_platform_participant'),
        Index('ix_participants_tenant_id', 'tenant_id'),
        Index('ix_participants_tenant_platform', 'tenant_id', 'platform'),
        Index('ix_participants_tenant_email', 'tenant_id', 'email'),
        Index('ix_participants_tenant_display_name',
              'tenant_id', 'display_name'),
    )
