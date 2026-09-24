"""
Embedding Model

Represents vector embeddings for semantic search.
"""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base import Base

# Note: For vector support, we'll use pgvector extension
# This requires: CREATE EXTENSION vector;
# And the pgvector Python package
try:
    from pgvector.sqlalchemy import Vector

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    # Fallback to ARRAY if pgvector not available
    from sqlalchemy import Float
    from sqlalchemy.dialects.postgresql import ARRAY


class Embedding(Base):
    """
    Embedding model for vector representations.

    Stores vector embeddings of messages for semantic search
    and similarity matching.

    Attributes:
        message_id: Foreign key to Message
        vector: Vector embedding (768 dimensions for nomic-embed-text)
        model: Model used to generate embedding
        message: Related message
    """

    __tablename__ = "embeddings"

    # Foreign key to message
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Vector embedding
    # Using pgvector if available, otherwise ARRAY as fallback
    if VECTOR_AVAILABLE:
        vector = Column(Vector(768), nullable=False)
    else:
        # Fallback to ARRAY for development without pgvector
        vector = Column(ARRAY(Float), nullable=False)

    # Model information
    model = Column(String(100), nullable=False)

    # Relationships
    message = relationship("Message", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, model={self.model})>"
