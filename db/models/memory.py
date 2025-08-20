import uuid
from sqlalchemy import JSON, Column, ForeignKey, String, Text, Enum, DateTime, Float, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from db.base import Base
import enum


class MemoryType(str, enum.Enum):
    daily = "daily"
    thread = "thread"
    lifetime = "lifetime"
    interaction = "interaction"


class CommitmentStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"
    cancelled = "cancelled"


class CommitmentType(str, enum.Enum):
    task = "task"
    meeting = "meeting"
    deadline = "deadline"
    follow_up = "follow_up"
    promise = "promise"
    reminder = "reminder"


class NudgeType(str, enum.Enum):
    follow_up = "follow_up"
    deadline_reminder = "deadline_reminder"
    reconnection = "reconnection"
    file_reference = "file_reference"
    relationship_insight = "relationship_insight"
    commitment_check = "commitment_check"


class NudgePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ContactMemory(Base):
    __tablename__ = "contact_memory"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey(
        "contacts.id", ondelete="CASCADE"), nullable=False)

    summary_text = Column(Text, nullable=False)
    vector = Column(JSON, nullable=True)  # stored as list of floats
    last_updated = Column(DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow)


class Commitment(Base):
    __tablename__ = "commitments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core content
    type = Column(Enum(CommitmentType), nullable=False,
                  default=CommitmentType.task)
    status = Column(Enum(CommitmentStatus), nullable=False,
                    default=CommitmentStatus.pending)
    description = Column(Text, nullable=False)
    context = Column(Text, nullable=True)

    # Participants
    committed_by = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    committed_to = Column(UUID(as_uuid=True), ForeignKey(
        "contacts.id", ondelete="SET NULL"), nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Source information
    source_message_id = Column(UUID(as_uuid=True), ForeignKey(
        "messages.id", ondelete="SET NULL"), nullable=True)
    source_thread_id = Column(UUID(as_uuid=True), ForeignKey(
        "threads.id", ondelete="SET NULL"), nullable=True)
    source_platform = Column(String(50), nullable=True)

    # AI analysis
    confidence_score = Column(Float, default=0.0)
    extracted_entities = Column(JSON, nullable=True)  # List of entity IDs

    # Metadata
    extra_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_commitment_user_status", "committed_by", "status"),
        Index("ix_commitment_due_date", "due_date"),
        Index("ix_commitment_contact", "committed_to"),
    )


class FileReference(Base):
    __tablename__ = "file_references"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # File information
    filename = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_url = Column(Text, nullable=True)

    # Sharing context
    shared_by = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    shared_with = Column(JSON, nullable=True)  # List of contact/user IDs
    shared_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Source information
    source_message_id = Column(UUID(as_uuid=True), ForeignKey(
        "messages.id", ondelete="SET NULL"), nullable=True)
    source_thread_id = Column(UUID(as_uuid=True), ForeignKey(
        "threads.id", ondelete="SET NULL"), nullable=True)
    source_platform = Column(String(50), nullable=True)

    # AI analysis
    content_summary = Column(Text, nullable=True)
    extracted_topics = Column(JSON, nullable=True)  # List of topics

    # Metadata
    extra_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_file_reference_user", "shared_by"),
        Index("ix_file_reference_filename", "filename"),
        Index("ix_file_reference_shared_at", "shared_at"),
    )


class Nudge(Base):
    __tablename__ = "nudges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Nudge details
    type = Column(Enum(NudgeType), nullable=False)
    priority = Column(Enum(NudgePriority), nullable=False,
                      default=NudgePriority.medium)

    # Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    action_text = Column(String(100), nullable=True)

    # Target user
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    # Context
    related_contact_id = Column(UUID(as_uuid=True), ForeignKey(
        "contacts.id", ondelete="SET NULL"), nullable=True)
    related_commitment_id = Column(UUID(as_uuid=True), ForeignKey(
        "commitments.id", ondelete="SET NULL"), nullable=True)
    related_file_id = Column(UUID(as_uuid=True), ForeignKey(
        "file_references.id", ondelete="SET NULL"), nullable=True)
    related_thread_id = Column(UUID(as_uuid=True), ForeignKey(
        "threads.id", ondelete="SET NULL"), nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_for = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Status
    is_delivered = Column(Boolean, default=False, nullable=False)
    is_dismissed = Column(Boolean, default=False, nullable=False)
    is_acted_upon = Column(Boolean, default=False, nullable=False)

    # AI analysis
    confidence_score = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)

    # Metadata
    extra_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_nudge_user_delivered", "user_id", "is_delivered"),
        Index("ix_nudge_priority_scheduled", "priority", "scheduled_for"),
        Index("ix_nudge_type_user", "type", "user_id"),
    )


class ContactDossier(Base):
    __tablename__ = "contact_dossiers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic contact info
    contact_id = Column(UUID(as_uuid=True), ForeignKey(
        "contacts.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)

    # Communication summary
    first_interaction = Column(DateTime, nullable=True)
    last_interaction = Column(DateTime, nullable=True)
    total_messages = Column(Integer, default=0)
    total_threads = Column(Integer, default=0)

    # Relationship insights
    relationship_strength = Column(Float, default=0.0)
    communication_style = Column(String(100), nullable=True)
    interaction_frequency = Column(String(50), nullable=True)

    # Content analysis
    key_topics = Column(JSON, nullable=True)  # List of topics
    common_entities = Column(JSON, nullable=True)  # List of entity IDs

    # AI-generated content
    summary = Column(Text, nullable=True)
    personality_insights = Column(Text, nullable=True)
    # List of action suggestions
    suggested_actions = Column(JSON, nullable=True)

    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False)
    extra_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_contact_dossier_user", "user_id"),
        Index("ix_contact_dossier_updated", "last_updated"),
    )
