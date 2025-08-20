"""Entity models for extracted information from messages."""

import uuid
from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base
import enum


class EntityType(str, enum.Enum):
    """Types of entities that can be extracted."""
    person = "person"
    organization = "organization"
    date = "date"
    task = "task"
    file = "file"
    topic = "topic"
    location = "location"
    money = "money"
    phone = "phone"
    email = "email"
    # LinkedIn-specific entity types
    job_title = "job_title"
    industry = "industry"
    skill = "skill"
    business_opportunity = "business_opportunity"


class Entity(Base):
    """Entity model for extracted information."""
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)  # EntityType enum value
    value = Column(Text, nullable=False)
    normalized_value = Column(Text)  # Cleaned/standardized version
    confidence = Column(Float)  # Confidence score from extraction

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Metadata
    entity_metadata = Column(JSON)  # Additional entity information

    # Relationships
    message_entities = relationship("MessageEntity", back_populates="entity")

    __table_args__ = (
        Index('ix_entities_type_value', 'type', 'value'),
        Index('ix_entities_normalized', 'normalized_value'),
        Index('ix_entities_confidence', 'confidence'),
    )


class MessageEntity(Base):
    """Association table between messages and entities."""
    __tablename__ = "message_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey(
        "messages.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey(
        "entities.id", ondelete="CASCADE"), nullable=False)

    # Context information
    start_position = Column(Integer)  # Character position in message
    end_position = Column(Integer)
    context = Column(Text)  # Surrounding text context

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    message = relationship("Message", back_populates="entities")
    entity = relationship("Entity", back_populates="message_entities")

    __table_args__ = (
        Index('ix_message_entities_message', 'message_id'),
        Index('ix_message_entities_entity', 'entity_id'),
    )
