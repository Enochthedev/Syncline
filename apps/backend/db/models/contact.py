"""
Contact Model

Represents unified contacts across multiple platforms.
"""

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from db.base import Base


class Contact(Base):
    """
    Contact model for unified identity across platforms.
    
    Represents a person or entity that the user communicates with,
    potentially across multiple platforms.
    
    Attributes:
        canonical_name: Primary name for the contact
        emails: List of email addresses
        phones: List of phone numbers
        platform_identities: Platform-specific user IDs
        contact_metadata: Additional contact information
        participants: Related platform-specific participants
        threads: Related conversation threads
    """
    
    __tablename__ = "contacts"
    
    # Primary identity
    canonical_name = Column(String(255), nullable=False, index=True)
    
    # Contact information
    emails = Column(ARRAY(Text), nullable=True)
    phones = Column(ARRAY(Text), nullable=True)
    
    # Platform-specific identities
    # Structure: {
    #   "gmail": "user@example.com",
    #   "slack": "U12345678",
    #   "discord": "123456789012345678",
    #   "whatsapp": "+1234567890",
    #   ...
    # }
    platform_identities = Column(JSONB, nullable=True)
    
    # Additional metadata
    # Structure: {
    #   "avatar_url": "...",
    #   "company": "...",
    #   "title": "...",
    #   "notes": "...",
    #   "tags": [...],
    #   "custom_fields": {...}
    # }
    contact_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    participants = relationship(
        "Participant",
        back_populates="contact",
        cascade="all, delete-orphan"
    )
    
    threads = relationship(
        "Thread",
        back_populates="contact",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name={self.canonical_name})>"
