"""
Entity Model

Represents extracted named entities from messages.
"""

from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from db.base import Base


class Entity(Base):
    """
    Entity model for extracted named entities.

    Stores entities extracted from messages using NLP/AI,
    such as people, organizations, locations, dates, etc.

    Attributes:
        message_id: Foreign key to Message
        entity_type: Type of entity (PERSON, ORG, DATE, LOCATION, etc.)
        entity_text: The actual text of the entity
        confidence: Confidence score (0.0 to 1.0)
        entity_metadata: Additional entity information
        message: Related message
    """

    __tablename__ = "entities"

    # Foreign key to message
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entity information
    entity_type = Column(String(50), nullable=False, index=True)
    entity_text = Column(String(500), nullable=False, index=True)

    # Confidence score from extraction
    confidence = Column(Float, nullable=True)

    # Additional metadata
    # Structure: {
    #   "start_pos": 0,
    #   "end_pos": 10,
    #   "normalized_value": "...",
    #   "context": "...",
    #   "extractor": "spacy|custom",
    #   ...
    # }
    entity_metadata = Column(JSONB, nullable=True)

    # Relationships
    message = relationship("Message", back_populates="entities")

    def __repr__(self) -> str:
        return (
            f"<Entity(id={self.id}, type={self.entity_type}, text={self.entity_text})>"
        )
