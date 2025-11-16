"""
Collection Job Model

Tracks message collection jobs for platform connections.
"""

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from db.base import Base


class JobType(str, enum.Enum):
    """Collection job types."""
    HISTORICAL = "historical"
    REALTIME = "realtime"
    INCREMENTAL = "incremental"


class JobStatus(str, enum.Enum):
    """Collection job status states."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CollectionJob(Base):
    """
    Collection job model for tracking message collection tasks.
    
    Attributes:
        connection_id: Foreign key to PlatformConnection
        job_type: Type of collection job (historical, realtime, incremental)
        status: Current job status
        progress: Job progress information (JSONB)
        error_message: Error message if job failed
        connection: Related platform connection
    """
    
    __tablename__ = "collection_jobs"
    
    # Foreign key to platform connection
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Job type
    job_type = Column(
        SQLEnum(JobType, name="job_type"),
        nullable=False,
        index=True
    )
    
    # Job status
    status = Column(
        SQLEnum(JobStatus, name="job_status"),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Progress tracking
    # Structure: {
    #   "total_messages": 1000,
    #   "collected_messages": 250,
    #   "last_message_id": "...",
    #   "page_token": "...",
    #   "started_at": "2024-01-01T00:00:00Z",
    #   "estimated_completion": "2024-01-01T01:00:00Z",
    #   "messages_per_second": 4.2,
    #   ...
    # }
    progress = Column(JSONB, nullable=True)
    
    # Error information
    error_message = Column(String(1000), nullable=True)
    
    # Relationships
    connection = relationship("PlatformConnection", backref="collection_jobs")
    
    def __repr__(self) -> str:
        return f"<CollectionJob(id={self.id}, type={self.job_type}, status={self.status})>"
