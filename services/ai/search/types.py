"""
Type definitions for the hybrid search system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID


class SearchResultType(str, Enum):
    """Types of search results."""
    MESSAGE = "message"
    THREAD = "thread"
    PARTICIPANT = "participant"
    ENTITY = "entity"
    SUMMARY = "summary"
    ATTACHMENT = "attachment"


class QueryIntent(str, Enum):
    """Detected intent from natural language queries."""
    GENERAL_SEARCH = "general_search"
    COMMITMENT_SEARCH = "commitment_search"
    PERSON_SEARCH = "person_search"
    TOPIC_SEARCH = "topic_search"
    TIME_BASED_SEARCH = "time_based_search"
    FILE_SEARCH = "file_search"
    CONVERSATION_SEARCH = "conversation_search"


@dataclass
class SearchFilters:
    """Filters for search queries."""
    platforms: Optional[List[str]] = None
    participants: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    thread_ids: Optional[List[UUID]] = None
    entity_types: Optional[List[str]] = None
    has_attachments: Optional[bool] = None
    content_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None


@dataclass
class SearchRanking:
    """Ranking information for search results."""
    lexical_score: float = 0.0
    vector_score: float = 0.0
    combined_score: float = 0.0
    boost_factors: Dict[str, float] = field(default_factory=dict)
    explanation: Optional[str] = None


@dataclass
class SearchResult:
    """Individual search result."""
    id: str
    type: SearchResultType
    title: str
    content: str
    snippet: str
    metadata: Dict[str, Any]
    ranking: SearchRanking
    timestamp: datetime
    platform: Optional[str] = None
    thread_id: Optional[UUID] = None
    participant_id: Optional[UUID] = None
    url: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class SearchQuery:
    """Search query with processing metadata."""
    text: str
    filters: Optional[SearchFilters] = None
    limit: int = 50
    offset: int = 0
    include_snippets: bool = True
    include_context: bool = True

    # Processing metadata
    intent: Optional[QueryIntent] = None
    processed_text: Optional[str] = None
    extracted_entities: Optional[List[Dict[str, Any]]] = None
    temporal_constraints: Optional[Dict[str, Any]] = None


@dataclass
class FusionWeights:
    """Weights for combining lexical and vector search results."""
    lexical_weight: float = 0.6
    vector_weight: float = 0.4
    recency_boost: float = 0.1
    relevance_boost: float = 0.2
    platform_boost: Dict[str, float] = field(default_factory=dict)
    participant_boost: Dict[str, float] = field(default_factory=dict)

    def normalize(self) -> "FusionWeights":
        """Normalize weights to sum to 1.0."""
        total = self.lexical_weight + self.vector_weight
        if total > 0:
            self.lexical_weight /= total
            self.vector_weight /= total
        return self


@dataclass
class SearchStats:
    """Statistics for search operations."""
    total_results: int = 0
    lexical_results: int = 0
    vector_results: int = 0
    processing_time_ms: float = 0.0
    query_intent: Optional[QueryIntent] = None
    filters_applied: int = 0


@dataclass
class SearchResponse:
    """Complete search response."""
    results: List[SearchResult]
    stats: SearchStats
    query: SearchQuery
    suggestions: Optional[List[str]] = None
    facets: Optional[Dict[str, List[Dict[str, Any]]]] = None
