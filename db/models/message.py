import uuid
from sqlalchemy import Column, ForeignKey, String, Text, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from db.base import Base
import enum

class MessageSource(str, enum.Enum):
    gmail = "gmail"
    whatsapp = "whatsapp"
    telegram = "telegram"
    twitter_dm = "twitter_dm"

class MessageDirection(str, enum.Enum):
    incoming = "incoming"
    outgoing = "outgoing"

class Message(Base):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)

    source = Column(Enum(MessageSource), nullable=False)
    direction = Column(Enum(MessageDirection), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    thread_id = Column(String, nullable=True)  # Gmail thread, Telegram conversation ID, etc.
    transcript = Column(Text, nullable=True)  # For calls/voice notes
    metadata = Column(JSON, nullable=True)  # message_id, attachments, reactions

    created_at = Column(DateTime, default=datetime.utcnow)