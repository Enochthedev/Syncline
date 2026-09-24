"""
Attachment Model

Represents file attachments associated with messages.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base import Base


class Attachment(Base):
    """
    Attachment model for message files.

    Represents files attached to messages, with metadata
    and storage location.

    Attributes:
        message_id: Foreign key to Message
        filename: Original filename
        mime_type: MIME type of the file
        size_bytes: File size in bytes
        storage_path: Path to stored file
        platform_url: Original URL from platform (if available)
        message: Related message
    """

    __tablename__ = "attachments"

    # Foreign key to message
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File information
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)

    # Storage location
    storage_path = Column(String(500), nullable=False)

    # Original platform URL (if available)
    platform_url = Column(String(1000), nullable=True)

    # Relationships
    message = relationship("Message", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, filename={self.filename}, size={self.size_bytes})>"
