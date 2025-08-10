import uuid
from sqlalchemy import JSON, Column, ForeignKey, String, Text, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from db.base import Base
import enum

class MemoryType(str, enum.Enum):
    daily = "daily"
    thread = "thread"
    lifetime = "lifetime"
    interaction = "interaction"

class ContactMemory(Base):
    __tablename__ = "contact_memory"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)

    summary_text = Column(Text, nullable=False)
    vector = Column(JSON, nullable=True)  # stored as list of floats
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)