"""
Participant Model

Represents platform-specific user identities.
"""

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from db.base import Base


class Participant(Base):
    """
    Participant model for platform-specific identities.
    
    Represents a user's identity on a specific platform,
    which can be linked to a unified Contact.
    
    Attributes:
        contact_id: Foreign key to Contact (nullable until matched)
        platform: Platform name
        platform_user_id: Platform's unique user identifier
        name: Display name on platform
        email: Email address (if available)
        phone: Phone number (if available)
        participant_metadata: Additional platform-specific data
        contact: Related unified contact
        sent_messages: Messages sent by this participant
    """
    
    __tablename__ = "participants"
    
    # Foreign key to contact (nullable until matched)
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Platform information
    platform = Column(String(50), nullable=False, index=True)
    platform_user_id = Column(String(255), nullable=False, index=True)
    
    # User information
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    
    # Platform-specific metadata
    # Structure: {
    #   "avatar_url": "...",
    #   "username": "...",
    #   "display_name": "...",
    #   "profile_url": "...",
    #   "is_bot": true/false,
    #   ...
    # }
    participant_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    contact = relationship("Contact", back_populates="participants")
    
    # Messages sent by this participant
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender"
    )
    
    # Unique constraint: one participant per platform user
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_user_id",
            name="uq_platform_user"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Participant(id={self.id}, platform={self.platform}, name={self.name})>"
