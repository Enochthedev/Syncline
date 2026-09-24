"""
Contact Model

Represents unified contacts across multiple platforms.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from db.base import Base


class Contact(Base):
    """
    Contact model for unified identity across platforms.

    Represents a person or entity that the user communicates with,
    potentially across multiple platforms.

    Attributes:
        user_id: Owner of this contact
        canonical_name: Primary name for the contact
        emails: List of email addresses
        phones: List of phone numbers
        linkedin_url: LinkedIn profile URL
        linkedin_id: LinkedIn member ID
        company: Current company/organization
        job_title: Current job title
        message_count: Cached count of messages for filtering
        platform_identities: Platform-specific user IDs
        contact_metadata: Additional contact information
        participants: Related platform-specific participants
        threads: Related conversation threads
    """

    __tablename__ = "contacts"

    # Owner of this contact
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # Nullable until we have proper user context
        index=True,
    )

    # Primary identity
    canonical_name = Column(String(255), nullable=False, index=True)

    # Contact information
    emails = Column(ARRAY(Text), nullable=True)
    phones = Column(ARRAY(Text), nullable=True)

    # LinkedIn-specific fields
    linkedin_url = Column(String(512), nullable=True, unique=True, index=True)
    linkedin_id = Column(String(255), nullable=True, unique=True, index=True)

    # Professional context fields
    company = Column(String(255), nullable=True, index=True)
    job_title = Column(String(255), nullable=True)

    # Message count for filtering (only show contacts with messages)
    # Updated when messages are synced
    message_count = Column(Integer, nullable=False, default=0, index=True)

    # Platform-specific identities
    # Structure: {
    #   "gmail": "user@example.com",
    #   "slack": "U12345678",
    #   "discord": "123456789012345678",
    #   "whatsapp": "+1234567890",
    #   "linkedin": "john-smith-123abc",
    #   ...
    # }
    platform_identities = Column(JSONB, nullable=True)

    # Additional metadata
    # Structure: {
    #   "avatar_url": "...",
    #   "industry": "...",
    #   "location": "...",
    #   "notes": "...",
    #   "tags": [...],
    #   "skills": [...],
    #   "connection_degree": 1,
    #   "custom_fields": {...}
    # }
    contact_metadata = Column(JSONB, nullable=True)

    # Relationships
    participants = relationship(
        "Participant", back_populates="contact", cascade="all, delete-orphan"
    )

    threads = relationship(
        "Thread", back_populates="contact", cascade="all, delete-orphan"
    )

    memories = relationship(
        "Memory", back_populates="contact", cascade="all, delete-orphan"
    )

    @property
    def has_messages(self) -> bool:
        """Check if this contact has any messages."""
        return self.message_count > 0

    @property
    def display_name(self) -> str:
        """Get display name with optional company context."""
        if self.company:
            return f"{self.canonical_name} ({self.company})"
        return self.canonical_name

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name={self.canonical_name}, messages={self.message_count})>"
