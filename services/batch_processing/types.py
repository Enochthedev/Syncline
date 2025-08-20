"""
Type definitions for batch processing system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class BatchJobType(str, Enum):
    """Types of batch jobs that can be scheduled."""
    DAILY_DIGEST = "daily_digest"
    WEEKLY_DIGEST = "weekly_digest"
    ENTITY_GRAPH_BUILD = "entity_graph_build"
    MEMORY_OPTIMIZATION = "memory_optimization"
    DATA_RETENTION = "data_retention"
    SUMMARY_CLEANUP = "summary_cleanup"
    VECTOR_REINDEX = "vector_reindex"


class BatchJobStatus(str, Enum):
    """Status of batch jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class DigestType(str, Enum):
    """Types of digest summaries."""
    DAILY_PERSONAL = "daily_personal"
    DAILY_CONTACT = "daily_contact"
    DAILY_THREAD = "daily_thread"
    WEEKLY_OVERVIEW = "weekly_overview"
    WEEKLY_TRENDS = "weekly_trends"
    WEEKLY_RELATIONSHIPS = "weekly_relationships"


class EntityGraphScope(str, Enum):
    """Scope for entity graph building."""
    USER = "user"
    TENANT = "tenant"
    CONTACT = "contact"
    THREAD = "thread"
    TIMEFRAME = "timeframe"


class MemoryOptimizationType(str, Enum):
    """Types of memory optimization operations."""
    CONSOLIDATE_SUMMARIES = "consolidate_summaries"
    COMPRESS_EMBEDDINGS = "compress_embeddings"
    ARCHIVE_OLD_DATA = "archive_old_data"
    REBUILD_INDEXES = "rebuild_indexes"
    CLEANUP_DUPLICATES = "cleanup_duplicates"


class RetentionPolicy(str, Enum):
    """Data retention policies."""
    MESSAGES_30_DAYS = "messages_30_days"
    MESSAGES_90_DAYS = "messages_90_days"
    MESSAGES_1_YEAR = "messages_1_year"
    SUMMARIES_6_MONTHS = "summaries_6_months"
    SUMMARIES_2_YEARS = "summaries_2_years"
    EMBEDDINGS_1_YEAR = "embeddings_1_year"
    AUDIT_LOGS_7_YEARS = "audit_logs_7_years"


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: BatchJobType = BatchJobType.DAILY_DIGEST
    status: BatchJobStatus = BatchJobStatus.PENDING

    # Scheduling
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Configuration
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Execution details
    progress: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Results
    result_data: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DigestRequest:
    """Request for digest generation."""
    digest_type: DigestType
    tenant_id: str
    user_id: Optional[str] = None
    contact_id: Optional[str] = None
    thread_id: Optional[str] = None

    # Time range
    start_date: datetime = field(
        default_factory=lambda: datetime.utcnow() - timedelta(days=1))
    end_date: datetime = field(default_factory=datetime.utcnow)

    # Options
    include_attachments: bool = True
    include_entities: bool = True
    include_sentiment: bool = False
    max_messages: Optional[int] = None

    # Output preferences
    format: str = "markdown"
    language: str = "en"
    detail_level: str = "medium"  # low, medium, high


@dataclass
class EntityGraphRequest:
    """Request for entity graph building."""
    scope: EntityGraphScope
    tenant_id: str
    scope_id: Optional[str] = None  # user_id, contact_id, thread_id, etc.

    # Time range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Graph options
    include_relationships: bool = True
    include_weights: bool = True
    min_confidence: float = 0.5
    max_entities: Optional[int] = None

    # Analysis options
    detect_communities: bool = True
    calculate_centrality: bool = True
    find_key_entities: bool = True


@dataclass
class MemoryOptimizationRequest:
    """Request for memory optimization."""
    optimization_type: MemoryOptimizationType
    tenant_id: str

    # Scope
    user_id: Optional[str] = None
    contact_id: Optional[str] = None

    # Options
    dry_run: bool = False
    backup_before: bool = True
    compression_ratio: float = 0.8

    # Thresholds
    min_age_days: int = 30
    min_size_mb: float = 1.0
    max_items_per_batch: int = 1000


@dataclass
class RetentionRequest:
    """Request for data retention processing."""
    policy: RetentionPolicy
    tenant_id: str

    # Options
    dry_run: bool = False
    backup_before: bool = True
    force_delete: bool = False

    # Filters
    platform_filter: Optional[List[str]] = None
    user_filter: Optional[List[str]] = None

    # Safety limits
    max_deletions_per_batch: int = 1000
    confirmation_required: bool = True


@dataclass
class BatchJobResult:
    """Result of a batch job execution."""
    job_id: str
    success: bool

    # Execution metrics
    duration_seconds: float
    items_processed: int
    items_failed: int

    # Resource usage
    memory_peak_mb: float
    cpu_time_seconds: float

    # Output data
    output_files: List[str] = field(default_factory=list)
    summary: Optional[str] = None

    # Error details
    error_type: Optional[str] = None
    error_details: Optional[str] = None

    # Metadata
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScheduleConfig:
    """Configuration for scheduled batch jobs."""
    job_type: BatchJobType
    cron_expression: str  # Standard cron format
    timezone: str = "UTC"

    # Job parameters
    default_parameters: Dict[str, Any] = field(default_factory=dict)

    # Execution options
    max_concurrent: int = 1
    timeout_minutes: int = 60
    retry_on_failure: bool = True

    # Conditions
    enabled: bool = True
    tenant_filter: Optional[List[str]] = None
    user_filter: Optional[List[str]] = None

    # Metadata
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EntityRelationship:
    """Represents a relationship between entities."""
    source_entity_id: str
    target_entity_id: str
    relationship_type: str

    # Strength and confidence
    weight: float = 1.0
    confidence: float = 0.5

    # Context
    context_messages: List[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    frequency: int = 1

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityGraph:
    """Represents an entity graph with nodes and relationships."""
    scope: EntityGraphScope
    scope_id: str

    # Graph data
    entities: List[str] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)

    # Analysis results
    communities: Dict[str, List[str]] = field(default_factory=dict)
    centrality_scores: Dict[str, float] = field(default_factory=dict)
    key_entities: List[str] = field(default_factory=list)

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    total_entities: int = 0
    total_relationships: int = 0

    # Statistics
    avg_degree: float = 0.0
    density: float = 0.0
    clustering_coefficient: float = 0.0


@dataclass
class DigestSummary:
    """Summary generated by digest processing."""
    digest_type: DigestType
    tenant_id: str
    scope_id: Optional[str] = None

    # Content
    title: str = ""
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)

    # Statistics
    message_count: int = 0
    thread_count: int = 0
    participant_count: int = 0
    attachment_count: int = 0

    # Time range
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: datetime = field(default_factory=datetime.utcnow)

    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    language: str = "en"
    word_count: int = 0

    # Related data
    entity_ids: List[str] = field(default_factory=list)
    thread_ids: List[str] = field(default_factory=list)
    contact_ids: List[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Result of memory optimization operation."""
    optimization_type: MemoryOptimizationType
    tenant_id: str

    # Before/after metrics
    items_before: int = 0
    items_after: int = 0
    size_before_mb: float = 0.0
    size_after_mb: float = 0.0

    # Operations performed
    items_consolidated: int = 0
    items_compressed: int = 0
    items_archived: int = 0
    items_deleted: int = 0

    # Performance
    duration_seconds: float = 0.0
    space_saved_mb: float = 0.0
    compression_ratio: float = 0.0

    # Metadata
    completed_at: datetime = field(default_factory=datetime.utcnow)
    backup_location: Optional[str] = None


@dataclass
class RetentionResult:
    """Result of data retention operation."""
    policy: RetentionPolicy
    tenant_id: str

    # Items processed
    items_evaluated: int = 0
    items_retained: int = 0
    items_archived: int = 0
    items_deleted: int = 0

    # Data volumes
    data_retained_mb: float = 0.0
    data_archived_mb: float = 0.0
    data_deleted_mb: float = 0.0

    # Performance
    duration_seconds: float = 0.0

    # Safety checks
    dry_run: bool = False
    backup_created: bool = False
    backup_location: Optional[str] = None

    # Metadata
    completed_at: datetime = field(default_factory=datetime.utcnow)
    policy_details: Dict[str, Any] = field(default_factory=dict)
