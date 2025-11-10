"""
Thread Model

Represents conversation threads across platforms.
"""

from sqlalchemy import Column, String, ForeignKey, Integer, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from db.base import Base


class Thread(Base):
    """
    Thread model for conversation grouping.
    
    Represents a conversation or message thread, potentially
    involving multiple participants.
    
    Attributes:
        platform: Platform name
        platform_thread_id: Platform's thread identifier
        contact_id: Primary contact for this thread
        title: Thread title or subject
        participant_ids: List of participant UUIDs
        message_count: Number of messages in thread
        first_message_at: Timestamp of first message
        last_message_at: Timestamp of last message
        contact: Related primary contact
        messages: Related messages (via thread_id)
    """
    
    __tablename__ = "threads"
    
    # Platform information
    platform = Column(String(50), nullable=False, index=True)
    platform_thread_id = Column(String(255), nullable=False, index=True)
    
    # Primary contact
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Thread metadata
    title = Column(String(500), nullable=True)
    
    # Participants (array of UUIDs)
    participant_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # Statistics
    message_count = Column(Integer, default=0, nullable=False)
    first_message_at = Column(DateTime, nullable=True, index=True)
    last_message_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    contact = relationship("Contact", back_populates="threads")
    
    # Messages will be queried via thread_id field in Message model
    # messages = relationship("Message", foreign_keys="Message.thread_id")
    
    # Unique constraint: one thread per platform
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_thread_id",
            name="uq_platform_thread"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Thread(id={self.id}, platform={self.platform}, messages={self.message_count})>"
