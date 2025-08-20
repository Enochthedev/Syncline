"""
Type definitions for proactive memory AI services.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union


class CommitmentStatus(str, Enum):
    """Status of a commitment or action item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class CommitmentType(str, Enum):
    """Type of commitment."""
    TASK = "task"
    MEETING = "meeting"
    DEADLINE = "deadline"
    FOLLOW_UP = "follow_up"
    PROMISE = "promise"
    REMINDER = "reminder"


class NudgeType(str, Enum):
    """Type of proactive nudge."""
    FOLLOW_UP = "follow_up"
    DEADLINE_REMINDER = "deadline_reminder"
    RECONNECTION = "reconnection"
    FILE_REFERENCE = "file_reference"
    RELATIONSHIP_INSIGHT = "relationship_insight"
    COMMITMENT_CHECK = "commitment_check"


class NudgePriority(str, Enum):
    """Priority level for nudges."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Commitment:
    """Represents a commitment, promise, or action item."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: CommitmentType = CommitmentType.TASK
    status: CommitmentStatus = CommitmentStatus.PENDING

    # Core content
    description: str = ""
    context: str = ""

    # Participants
    committed_by: str = ""  # User who made the commitment
    committed_to: Optional[str] = None  # Who the commitment is to

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Source information
    source_message_id: Optional[str] = None
    source_thread_id: Optional[str] = None
    source_platform: Optional[str] = None

    # AI analysis
    confidence_score: float = 0.0
    extracted_entities: List[str] = field(default_factory=list)

    # Metadata
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileReference:
    """Represents a shared file or resource."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # File information
    filename: str = ""
    file_type: str = ""
    file_size: Optional[int] = None
    file_url: Optional[str] = None

    # Sharing context
    shared_by: str = ""
    shared_with: List[str] = field(default_factory=list)
    shared_at: datetime = field(default_factory=datetime.utcnow)

    # Source information
    source_message_id: Optional[str] = None
    source_thread_id: Optional[str] = None
    source_platform: Optional[str] = None

    # AI analysis
    content_summary: Optional[str] = None
    extracted_topics: List[str] = field(default_factory=list)

    # Metadata
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipInsight:
    """Insights about relationships and communication patterns."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Relationship details
    contact_id: str = ""
    contact_name: str = ""

    # Communication patterns
    total_messages: int = 0
    last_interaction: Optional[datetime] = None
    interaction_frequency: str = ""  # daily, weekly, monthly, etc.
    response_time_avg: Optional[timedelta] = None

    # Relationship insights
    relationship_strength: float = 0.0  # 0-1 score
    communication_style: str = ""
    common_topics: List[str] = field(default_factory=list)
    shared_files_count: int = 0

    # Proactive suggestions
    suggested_actions: List[str] = field(default_factory=list)
    reconnection_opportunity: bool = False

    # Analysis metadata
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.0

    # Metadata
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContactDossier:
    """Comprehensive contact profile with AI insights."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Basic contact info
    contact_id: str = ""
    name: str = ""
    email: Optional[str] = None
    platforms: Dict[str, str] = field(
        default_factory=dict)  # platform -> handle

    # Communication summary
    first_interaction: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    total_messages: int = 0
    total_threads: int = 0

    # Relationship insights
    relationship_insights: RelationshipInsight = field(
        default_factory=RelationshipInsight)

    # Content analysis
    key_topics: List[str] = field(default_factory=list)
    shared_files: List[FileReference] = field(default_factory=list)
    commitments: List[Commitment] = field(default_factory=list)

    # AI-generated summary
    summary: str = ""
    personality_insights: str = ""

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Nudge:
    """Proactive nudge or reminder."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Nudge details
    type: NudgeType = NudgeType.FOLLOW_UP
    priority: NudgePriority = NudgePriority.MEDIUM

    # Content
    title: str = ""
    message: str = ""
    action_text: Optional[str] = None

    # Context
    related_contact_id: Optional[str] = None
    related_commitment_id: Optional[str] = None
    related_file_id: Optional[str] = None
    related_thread_id: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    # Status
    is_delivered: bool = False
    is_dismissed: bool = False
    is_acted_upon: bool = False

    # AI analysis
    confidence_score: float = 0.0
    reasoning: str = ""

    # Metadata
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryContext:
    """Context for memory operations."""
    user_id: str = ""
    contact_id: Optional[str] = None
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    platform: Optional[str] = None

    # Time context
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None

    # Processing options
    include_commitments: bool = True
    include_files: bool = True
    include_insights: bool = True

    # Metadata
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryAnalysisResult:
    """Result of memory analysis operation."""
    context: MemoryContext

    # Extracted information
    commitments: List[Commitment] = field(default_factory=list)
    files: List[FileReference] = field(default_factory=list)
    insights: List[RelationshipInsight] = field(default_factory=list)
    nudges: List[Nudge] = field(default_factory=list)

    # Analysis metadata
    processing_time: float = 0.0
    confidence_score: float = 0.0
    model_used: str = ""

    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
