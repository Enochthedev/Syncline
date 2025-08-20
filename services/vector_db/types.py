"""
Type definitions for vector database operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class VectorCollectionType(str, Enum):
    """Types of vector collections."""
    MESSAGES = "messages"
    SUMMARIES = "summaries"
    ENTITIES = "entities"
    DOCUMENTS = "documents"


@dataclass
class VectorMetadata:
    """Metadata for vector documents."""
    # Core message metadata
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    platform: Optional[str] = None
    sender: Optional[str] = None
    timestamp: Optional[datetime] = None

    # Content metadata
    content_type: Optional[str] = None  # text, summary, entity
    content_length: Optional[int] = None
    language: Optional[str] = None

    # Entity metadata (for entity embeddings)
    # person, organization, date, task, file, topic
    entity_type: Optional[str] = None
    entity_value: Optional[str] = None
    confidence: Optional[float] = None

    # Summary metadata (for summary embeddings)
    summary_type: Optional[str] = None  # micro, thread, daily, weekly
    summary_scope: Optional[str] = None  # message, thread, contact, global
    timeframe_start: Optional[datetime] = None
    timeframe_end: Optional[datetime] = None

    # Additional metadata
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Chroma storage."""
        result = {}

        # Convert datetime objects to ISO strings
        for key, value in self.__dict__.items():
            if value is None:
                continue
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, list) and value:
                result[key] = value
            elif isinstance(value, dict) and value:
                result[key] = value
            elif value:
                result[key] = str(value)

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorMetadata':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        converted_data = {}

        for key, value in data.items():
            if key in ['timestamp', 'timeframe_start', 'timeframe_end'] and isinstance(value, str):
                try:
                    converted_data[key] = datetime.fromisoformat(value)
                except ValueError:
                    converted_data[key] = value
            else:
                converted_data[key] = value

        return cls(**converted_data)


@dataclass
class VectorDocument:
    """Document for vector storage."""
    id: str
    text: str
    embedding: List[float]
    metadata: VectorMetadata
    collection: VectorCollectionType
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_chroma_format(self) -> Dict[str, Any]:
        """Convert to Chroma storage format."""
        return {
            'ids': [self.id],
            'documents': [self.text],
            'embeddings': [self.embedding],
            'metadatas': [self.metadata.to_dict()]
        }


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    id: str
    text: str
    metadata: VectorMetadata
    distance: float
    similarity_score: float  # 1 - distance for cosine similarity

    @classmethod
    def from_chroma_result(
        cls,
        doc_id: str,
        document: str,
        metadata: Dict[str, Any],
        distance: float
    ) -> 'VectorSearchResult':
        """Create from Chroma search result."""
        return cls(
            id=doc_id,
            text=document,
            metadata=VectorMetadata.from_dict(metadata),
            distance=distance,
            similarity_score=1.0 - distance  # Convert distance to similarity
        )


@dataclass
class VectorSearchQuery:
    """Query for vector similarity search."""
    text: Optional[str] = None
    embedding: Optional[List[float]] = None
    collection: VectorCollectionType = VectorCollectionType.MESSAGES
    limit: int = 10

    # Metadata filters
    platform_filter: Optional[str] = None
    sender_filter: Optional[str] = None
    thread_filter: Optional[str] = None
    content_type_filter: Optional[str] = None
    entity_type_filter: Optional[str] = None
    summary_type_filter: Optional[str] = None

    # Time range filters
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Tag filters
    include_tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)

    # Custom metadata filters
    custom_filters: Dict[str, Any] = field(default_factory=dict)

    def build_where_clause(self) -> Optional[Dict[str, Any]]:
        """Build Chroma where clause from filters."""
        where_conditions = {}

        # Platform filter
        if self.platform_filter:
            where_conditions['platform'] = self.platform_filter

        # Sender filter
        if self.sender_filter:
            where_conditions['sender'] = self.sender_filter

        # Thread filter
        if self.thread_filter:
            where_conditions['thread_id'] = self.thread_filter

        # Content type filter
        if self.content_type_filter:
            where_conditions['content_type'] = self.content_type_filter

        # Entity type filter
        if self.entity_type_filter:
            where_conditions['entity_type'] = self.entity_type_filter

        # Summary type filter
        if self.summary_type_filter:
            where_conditions['summary_type'] = self.summary_type_filter

        # Add custom filters
        where_conditions.update(self.custom_filters)

        return where_conditions if where_conditions else None


@dataclass
class VectorBatchOperation:
    """Batch operation for vector database."""
    operation_type: str  # 'add', 'update', 'delete'
    documents: List[VectorDocument] = field(default_factory=list)
    document_ids: List[str] = field(
        default_factory=list)  # For delete operations
    collection: VectorCollectionType = VectorCollectionType.MESSAGES

    def validate(self) -> bool:
        """Validate the batch operation."""
        if self.operation_type == 'delete':
            return len(self.document_ids) > 0
        else:
            return len(self.documents) > 0


@dataclass
class VectorBatchResult:
    """Result from batch vector operation."""
    operation_type: str
    collection: VectorCollectionType
    processed_count: int
    success_count: int
    error_count: int
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.processed_count == 0:
            return 0.0
        return self.success_count / self.processed_count
