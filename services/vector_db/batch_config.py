"""
Configuration and result types for vector database batch processing.

This module provides configuration classes and result types for
batch processing operations in the vector database system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing operations."""
    batch_size: int = 100
    max_concurrent_batches: int = 3
    embedding_batch_size: int = 50
    retry_attempts: int = 3
    retry_delay: float = 1.0
    progress_callback: Optional[Callable[[int, int], None]] = None

    # Processing filters
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    platforms: List[str] = field(default_factory=list)
    content_types: List[str] = field(default_factory=list)


@dataclass
class BatchProcessingResult:
    """Result from batch processing operation."""
    operation_type: str
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    processing_time: float
    errors: List[str] = field(default_factory=list)
    batch_results: List[Any] = field(
        default_factory=list)  # VectorBatchResult list
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.processed_items == 0:
            return 0.0
        return self.successful_items / self.processed_items


@dataclass
class BatchOperationStats:
    """Statistics for batch processing operations."""
    total_batches_processed: int = 0
    total_documents_processed: int = 0
    total_processing_time: float = 0.0
    average_batch_time: float = 0.0
    last_processing_session: Optional[datetime] = None

    def update_stats(self, batch_count: int, document_count: int, processing_time: float) -> None:
        """Update processing statistics."""
        self.total_batches_processed += batch_count
        self.total_documents_processed += document_count
        self.total_processing_time += processing_time

        if self.total_batches_processed > 0:
            self.average_batch_time = (
                self.total_processing_time / self.total_batches_processed
            )

        self.last_processing_session = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'total_batches_processed': self.total_batches_processed,
            'total_documents_processed': self.total_documents_processed,
            'total_processing_time': self.total_processing_time,
            'average_batch_time': self.average_batch_time,
            'last_processing_session': self.last_processing_session
        }
