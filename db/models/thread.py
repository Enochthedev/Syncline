"""Thread model for conversation grouping."""

import uuid
from sqlalchemy import Column, String, DateTime, JSON, Integer, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from db.base import Base
from db.models.message import Platform


class Thread(Base):
    """Conversation thread model."""
    __tablename__ = "threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False,
                       index=True)  # Multi-tenant isolation
    # Use String instead of Enum for flexibility
    platform = Column(String(50), nullable=False)
    platform_thread_id = Column(String(255), nullable=False)

    # Thread metadata
    title = Column(String(500))
    participants = Column(ARRAY(UUID(as_uuid=True)),
                          nullable=False, default=list)
    last_message_at = Column(DateTime(timezone=True))
    message_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    thread_metadata = Column(JSON)  # Platform-specific thread metadata

    # Relationships
    messages = relationship(
        "Message", back_populates="thread", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'platform', 'platform_thread_id',
                         name='uq_tenant_platform_thread'),
        Index('ix_threads_tenant_id', 'tenant_id'),
        Index('ix_threads_tenant_platform', 'tenant_id', 'platform'),
        Index('ix_threads_tenant_last_message',
              'tenant_id', 'last_message_at'),
        Index('ix_threads_participants', 'participants', postgresql_using='gin'),
    )
