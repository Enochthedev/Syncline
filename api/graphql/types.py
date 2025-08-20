"""GraphQL type definitions for MESH ingestion system."""

import strawberry
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import json


@strawberry.type
class Participant:
    """GraphQL type for participant data."""
    id: str
    platform: str
    platform_user_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    participant_metadata: Optional[str] = None  # JSON string


@strawberry.type
class Thread:
    """GraphQL type for thread data."""
    id: str
    platform: str
    platform_thread_id: str
    title: Optional[str] = None
    participants: List[str]
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    thread_metadata: Optional[str] = None  # JSON string


@strawberry.type
class Message:
    """GraphQL type for message data."""
    id: str
    platform: str
    platform_message_id: str
    thread_id: str
    sender_id: str
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    content_markdown: Optional[str] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_metadata: Optional[str] = None  # JSON string
    raw_data: Optional[str] = None  # JSON string


@strawberry.type
class Entity:
    """GraphQL type for extracted entities."""
    id: str
    type: str
    value: str
    normalized_value: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Optional[str] = None  # JSON string
    created_at: Optional[datetime] = None


@strawberry.type
class Summary:
    """GraphQL type for AI-generated summaries."""
    id: str
    type: str
    scope_type: str
    scope_id: Optional[str] = None
    content: str
    key_points: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    timeframe_start: Optional[datetime] = None
    timeframe_end: Optional[datetime] = None
    created_at: Optional[datetime] = None
    summary_metadata: Optional[str] = None  # JSON string


@strawberry.type
class ContactDossier:
    """GraphQL type for contact dossier data."""
    id: str
    contact_id: str
    user_id: str
    first_interaction: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    total_messages: int
    total_threads: int
    relationship_strength: float
    communication_style: Optional[str] = None
    interaction_frequency: Optional[str] = None
    key_topics: Optional[List[str]] = None
    common_entities: Optional[List[str]] = None
    summary: Optional[str] = None
    personality_insights: Optional[str] = None
    suggested_actions: Optional[List[str]] = None
    generated_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


@strawberry.type
class FileReference:
    """GraphQL type for file references."""
    id: str
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    file_url: Optional[str] = None
    shared_by: str
    shared_with: Optional[List[str]] = None
    shared_at: Optional[datetime] = None
    source_message_id: Optional[str] = None
    source_thread_id: Optional[str] = None
    source_platform: Optional[str] = None
    content_summary: Optional[str] = None
    extracted_topics: Optional[List[str]] = None


@strawberry.type
class SearchResult:
    """GraphQL type for search results."""
    id: str
    type: str
    title: str
    content: str
    snippet: str
    metadata: str  # JSON string
    ranking: str  # JSON string
    timestamp: datetime
    platform: Optional[str] = None
    thread_id: Optional[str] = None
    participant_id: Optional[str] = None
    url: Optional[str] = None


@strawberry.type
class SearchStats:
    """GraphQL type for search statistics."""
    total_results: int
    lexical_results: int
    vector_results: int
    processing_time_ms: float
    query_intent: Optional[str] = None
    filters_applied: int


@strawberry.type
class SearchResponse:
    """GraphQL type for complete search response."""
    results: List[SearchResult]
    stats: SearchStats
    query: str  # JSON string
    suggestions: Optional[List[str]] = None
    facets: Optional[str] = None  # JSON string


# Input types for mutations and queries
@strawberry.input
class SearchFiltersInput:
    """GraphQL input type for search filters."""
    platforms: Optional[List[str]] = None
    participants: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    thread_ids: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    has_attachments: Optional[bool] = None
    content_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None


@strawberry.input
class PaginationInput:
    """GraphQL input type for pagination."""
    limit: int = 50
    offset: int = 0


@strawberry.input
class DateRangeInput:
    """GraphQL input type for date ranges."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None


@strawberry.input
class SummaryRequestInput:
    """GraphQL input type for summary requests."""
    scope_type: str
    scope_id: Optional[str] = None
    since_date: Optional[datetime] = None
    summary_type: Optional[str] = None
