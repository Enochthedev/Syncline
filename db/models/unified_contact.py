"""Enhanced unified contact models for contact intelligence system."""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Index, Float, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base
import enum


class ContactIdentityType(str, enum.Enum):
    """Types of contact identities across platforms."""
    EMAIL = "email"
    PHONE = "phone"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    TWITTER = "twitter"
    SLACK = "slack"
    DISCORD = "discord"
    LINKEDIN = "linkedin"
    GMAIL = "gmail"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class RelationshipStrength(str, enum.Enum):
    """Relationship strength categories."""
    UNKNOWN = "unknown"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class CommunicationFrequency(str, enum.Enum):
    """Communication frequency categories."""
    NEVER = "never"
    RARE = "rare"
    OCCASIONAL = "occasional"
    REGULAR = "regular"
    FREQUENT = "frequent"
    DAILY = "daily"


class UnifiedContact(Base):
    """Enhanced unified contact model with platform identities and AI insights."""
    __tablename__ = "unified_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    # Primary identity
    primary_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    profile_photo_url = Column(String(1000), nullable=True)

    # Contact information
    primary_email = Column(String(255), nullable=True)
    primary_phone = Column(String(50), nullable=True)

    # Communication metadata
    last_interaction = Column(DateTime, nullable=True)
    first_interaction = Column(DateTime, nullable=True)
    total_messages = Column(Integer, default=0)
    total_threads = Column(Integer, default=0)
    platforms = Column(JSON, default=list)  # List of platform names
    preferred_platform = Column(String(50), nullable=True)

    # AI-generated insights
    relationship_strength = Column(Float, default=0.0)  # 0-1 scale
    communication_frequency = Column(
        String(20), default=CommunicationFrequency.NEVER)
    # Average response time in hours
    response_time_avg = Column(Float, nullable=True)
    sentiment_score = Column(Float, default=0.0)  # -1 to 1 scale

    # Topic and entity analysis
    # List of frequently discussed topics
    top_topics = Column(JSON, default=list)
    common_entities = Column(JSON, default=list)  # List of common entities
    shared_interests = Column(JSON, default=list)  # List of shared interests

    # Relationship analysis
    mutual_contacts = Column(JSON, default=list)  # List of mutual contact IDs
    interaction_patterns = Column(JSON, default=dict)  # Communication patterns

    # User preferences and notes
    custom_notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # User-defined tags
    is_favorite = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    notification_preferences = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)

    # Metadata
    extra_metadata = Column(JSON, default=dict)

    # Relationships
    identities = relationship(
        "ContactIdentity", back_populates="unified_contact", cascade="all, delete-orphan")
    insights = relationship(
        "ContactInsight", back_populates="unified_contact", cascade="all, delete-orphan")
    preferences = relationship(
        "ContactPreference", back_populates="unified_contact", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_unified_contacts_tenant_user", "tenant_id", "user_id"),
        Index("ix_unified_contacts_primary_name", "primary_name"),
        Index("ix_unified_contacts_primary_email", "primary_email"),
        Index("ix_unified_contacts_last_interaction", "last_interaction"),
        Index("ix_unified_contacts_relationship_strength",
              "relationship_strength"),
        Index("ix_unified_contacts_communication_frequency",
              "communication_frequency"),
        Index("ix_unified_contacts_is_favorite", "is_favorite"),
        Index("ix_unified_contacts_is_archived", "is_archived"),
    )


class ContactIdentity(Base):
    """Platform-specific contact identities."""
    __tablename__ = "contact_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unified_contact_id = Column(UUID(as_uuid=True), ForeignKey(
        "unified_contacts.id", ondelete="CASCADE"), nullable=False)

    # Platform information
    platform = Column(String(50), nullable=False)
    platform_user_id = Column(String(255), nullable=False)
    platform_handle = Column(String(255), nullable=True)

    # Identity details
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    profile_url = Column(String(1000), nullable=True)
    avatar_url = Column(String(1000), nullable=True)

    # Verification and status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)

    # Platform-specific metadata
    platform_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    unified_contact = relationship(
        "UnifiedContact", back_populates="identities")

    __table_args__ = (
        Index("ix_contact_identities_unified_contact", "unified_contact_id"),
        Index("ix_contact_identities_platform", "platform"),
        Index("ix_contact_identities_platform_user",
              "platform", "platform_user_id"),
        Index("ix_contact_identities_email", "email"),
        Index("ix_contact_identities_phone", "phone"),
    )


class ContactInsight(Base):
    """AI-generated insights about contacts."""
    __tablename__ = "contact_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unified_contact_id = Column(UUID(as_uuid=True), ForeignKey(
        "unified_contacts.id", ondelete="CASCADE"), nullable=False)

    # Insight type and content
    # e.g., 'communication_pattern', 'relationship_strength'
    insight_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Analysis data
    confidence_score = Column(Float, default=0.0)  # 0-1 scale
    supporting_data = Column(JSON, default=dict)  # Supporting evidence

    # Recommendations
    suggested_actions = Column(JSON, default=list)  # List of suggested actions

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    # 'helpful', 'not_helpful', 'incorrect'
    user_feedback = Column(String(20), nullable=True)

    # Relationships
    unified_contact = relationship("UnifiedContact", back_populates="insights")

    __table_args__ = (
        Index("ix_contact_insights_unified_contact", "unified_contact_id"),
        Index("ix_contact_insights_type", "insight_type"),
        Index("ix_contact_insights_generated_at", "generated_at"),
        Index("ix_contact_insights_confidence", "confidence_score"),
    )


class ContactPreference(Base):
    """User preferences for specific contacts."""
    __tablename__ = "contact_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unified_contact_id = Column(UUID(as_uuid=True), ForeignKey(
        "unified_contacts.id", ondelete="CASCADE"), nullable=False)

    # Preference settings
    notification_enabled = Column(Boolean, default=True)
    preferred_communication_platform = Column(String(50), nullable=True)
    # 'never', 'low', 'normal', 'high'
    reminder_frequency = Column(String(20), default="normal")

    # Custom settings
    custom_ringtone = Column(String(255), nullable=True)
    custom_notification_sound = Column(String(255), nullable=True)

    # Privacy settings
    share_presence = Column(Boolean, default=True)
    share_read_receipts = Column(Boolean, default=True)

    # Interaction preferences
    auto_reply_enabled = Column(Boolean, default=False)
    auto_reply_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    unified_contact = relationship(
        "UnifiedContact", back_populates="preferences")

    __table_args__ = (
        Index("ix_contact_preferences_unified_contact", "unified_contact_id"),
    )


class ContactRelationship(Base):
    """Relationships between contacts (mutual connections, etc.)."""
    __tablename__ = "contact_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationship participants
    contact_a_id = Column(UUID(as_uuid=True), ForeignKey(
        "unified_contacts.id", ondelete="CASCADE"), nullable=False)
    contact_b_id = Column(UUID(as_uuid=True), ForeignKey(
        "unified_contacts.id", ondelete="CASCADE"), nullable=False)

    # Relationship details
    # 'mutual_contact', 'colleague', 'family', etc.
    relationship_type = Column(String(50), nullable=False)
    strength = Column(Float, default=0.0)  # 0-1 scale

    # Evidence
    common_threads = Column(Integer, default=0)
    common_groups = Column(JSON, default=list)
    shared_interactions = Column(Integer, default=0)

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, nullable=True)

    # Status
    is_confirmed = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)

    __table_args__ = (
        Index("ix_contact_relationships_contact_a", "contact_a_id"),
        Index("ix_contact_relationships_contact_b", "contact_b_id"),
        Index("ix_contact_relationships_type", "relationship_type"),
        Index("ix_contact_relationships_strength", "strength"),
    )
