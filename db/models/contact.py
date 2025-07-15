import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from db.base import Base

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    first_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    telegram = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)
    twitter_handle = Column(String, nullable=True)
    slack_handle = Column(String, nullable=True)
    linkedin_profile = Column(String, nullable=True)

    extra_meta = Column(JSON, nullable=True)  # avatars, profile bios, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_contact_user_fullname", "user_id", "first_name", "last_name"),
    )
    