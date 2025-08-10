"""Summary models for AI-generated content summaries."""

import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base
import enum

class SummaryType(str, enum.Enum):
    """Types of summaries that can be generated."""
    micro = "micro"        # Real-time single message context
    thread = "thread"      # Conversation-level insights
    daily = "daily"        # Daily rollup summaries
    weekly = "weekly"      # Weekly trend analysis

class SummaryScope(str, enum.Enum):
    """Scope of what the summary covers."""
    message = "message"    # Single message
    thread = "thread"      # Conversation thread
    contact = "contact"    # Per-contact summary
    global_scope = "global"  # Global/user-wide summary

class Summary(Base):
    """AI-generated summary model."""
    __tablename__ = "summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)  # SummaryType enum value
    scope_type = Column(String(50), nullable=False)  # SummaryScope enum value
    scope_id = Column(UUID(as_uuid=True))  # ID of the scoped entity (thread_id, participant_id, etc.)
    
    # Summary content
    content = Column(Text, nullable=False)
    key_points = Column(ARRAY(Text))  # Array of key points
    action_items = Column(ARRAY(Text))  # Array of action items
    entities = Column(ARRAY(UUID(as_uuid=True)))  # Referenced entity IDs
    
    # Time range
    timeframe_start = Column(DateTime(timezone=True))
    timeframe_end = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Metadata
    summary_metadata = Column(JSON)  # AI model info, confidence scores, etc.
    
    # Relationships can be added later when needed
    
    __table_args__ = (
        Index('ix_summaries_type_scope', 'type', 'scope_type'),
        Index('ix_summaries_scope_id', 'scope_id'),
        Index('ix_summaries_timeframe', 'timeframe_start', 'timeframe_end'),
        Index('ix_summaries_created', 'created_at'),
    )