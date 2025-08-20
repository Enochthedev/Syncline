"""
Search API endpoints for the MESH ingestion system.

Provides REST API endpoints for hybrid search functionality
with support for various search types and filtering options.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from api.auth.auth import get_current_active_user
from api.auth.rate_limiting import rate_limit
from api.auth.rbac import require_permission
from api.auth.models import User
from services.ai.search.agent import HybridSearchAgent
from services.ai.search.types import SearchFilters, FusionWeights, QueryIntent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# Global search agent instance
_search_agent: Optional[HybridSearchAgent] = None


async def get_search_agent() -> HybridSearchAgent:
    """Get the global search agent instance."""
    global _search_agent

    if _search_agent is None:
        _search_agent = HybridSearchAgent()
        await _search_agent.initialize()

    return _search_agent


# Request/Response Models
class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query text",
                       min_length=1, max_length=500)
    platforms: Optional[List[str]] = Field(
        None, description="Filter by platforms")
    participants: Optional[List[str]] = Field(
        None, description="Filter by participants")
    date_from: Optional[datetime] = Field(
        None, description="Filter messages from this date")
    date_to: Optional[datetime] = Field(
        None, description="Filter messages to this date")
    thread_ids: Optional[List[UUID]] = Field(
        None, description="Filter by thread IDs")
    entity_types: Optional[List[str]] = Field(
        None, description="Filter by entity types")
    has_attachments: Optional[bool] = Field(
        None, description="Filter by attachment presence")
    content_types: Optional[List[str]] = Field(
        None, description="Filter by content types")
    min_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum confidence score")
    limit: int = Field(
        50, ge=1, le=200, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    include_suggestions: bool = Field(
        True, description="Include search suggestions")
    include_facets: bool = Field(False, description="Include search facets")


class FusionWeightsRequest(BaseModel):
    """Custom fusion weights for search."""
    lexical_weight: float = Field(0.6, ge=0.0, le=1.0)
    vector_weight: float = Field(0.4, ge=0.0, le=1.0)
    recency_boost: float = Field(0.1, ge=0.0, le=1.0)
    relevance_boost: float = Field(0.2, ge=0.0, le=1.0)
    platform_boost: Optional[Dict[str, float]] = Field(None)
    participant_boost: Optional[Dict[str, float]] = Field(None)


class SearchResultResponse(BaseModel):
    """Individual search result response."""
    id: str
    type: str
    title: str
    content: str
    snippet: str
    metadata: Dict[str, Any]
    ranking: Dict[str, Any]
    timestamp: datetime
    platform: Optional[str] = None
    thread_id: Optional[UUID] = None
    participant_id: Optional[UUID] = None
    url: Optional[str] = None


class SearchStatsResponse(BaseModel):
    """Search statistics response."""
    total_results: int
    lexical_results: int
    vector_results: int
    processing_time_ms: float
    query_intent: Optional[str] = None
    filters_applied: int


class SearchResponse(BaseModel):
    """Complete search response."""
    results: List[SearchResultResponse]
    stats: SearchStatsResponse
    query: Dict[str, Any]
    suggestions: Optional[List[str]] = None
    facets: Optional[Dict[str, List[Dict[str, Any]]]] = None


class CommitmentSearchRequest(BaseModel):
    """Commitment search request."""
    person: Optional[str] = Field(None, description="Person name to filter by")
    topic: Optional[str] = Field(None, description="Topic to filter by")
    timeframe: Optional[str] = Field(
        None, description="Timeframe (e.g., 'last week')")
    limit: int = Field(20, ge=1, le=100)


class FileSearchRequest(BaseModel):
    """File search request."""
    contact: Optional[str] = Field(
        None, description="Contact name to filter by")
    file_type: Optional[str] = Field(
        None, description="File type to filter by")
    limit: int = Field(20, ge=1, le=100)


# API Endpoints
@router.post("/", response_model=SearchResponse)
@rate_limit(requests_per_minute=30, requests_per_hour=500, per_user=True)
@require_permission("search", "read")
async def search_messages(
    request: SearchRequest,
    fusion_weights: Optional[FusionWeightsRequest] = None,
    current_user: User = Depends(get_current_active_user),
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> SearchResponse:
    """
    Perform hybrid search across all message data.

    Combines lexical and vector search with intelligent query processing
    and result fusion for comprehensive search results.
    """
    try:
        # Convert request to search filters
        filters = SearchFilters(
            platforms=request.platforms,
            participants=request.participants,
            date_from=request.date_from,
            date_to=request.date_to,
            thread_ids=request.thread_ids,
            entity_types=request.entity_types,
            has_attachments=request.has_attachments,
            content_types=request.content_types,
            min_confidence=request.min_confidence
        )

        # Convert fusion weights if provided
        weights = None
        if fusion_weights:
            weights = FusionWeights(
                lexical_weight=fusion_weights.lexical_weight,
                vector_weight=fusion_weights.vector_weight,
                recency_boost=fusion_weights.recency_boost,
                relevance_boost=fusion_weights.relevance_boost,
                platform_boost=fusion_weights.platform_boost or {},
                participant_boost=fusion_weights.participant_boost or {}
            )

        # Perform search
        search_response = await search_agent.search(
            query_text=request.query,
            filters=filters,
            limit=request.limit,
            offset=request.offset,
            fusion_weights=weights,
            include_suggestions=request.include_suggestions,
            include_facets=request.include_facets
        )

        # Convert to API response format
        return _convert_search_response(search_response)

    except Exception as e:
        logger.error(f"Search API error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/", response_model=SearchResponse)
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("search", "read")
async def search_messages_get(
    q: str = Query(..., description="Search query",
                   min_length=1, max_length=500),
    platforms: Optional[str] = Query(
        None, description="Comma-separated platform names"),
    participants: Optional[str] = Query(
        None, description="Comma-separated participant names"),
    date_from: Optional[datetime] = Query(
        None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(
        None, description="Filter to date (ISO format)"),
    has_attachments: Optional[bool] = Query(
        None, description="Filter by attachment presence"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_active_user),
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> SearchResponse:
    """
    Perform hybrid search using GET parameters.

    Simplified search endpoint using query parameters for easy integration.
    """
    try:
        # Parse comma-separated values
        platform_list = platforms.split(",") if platforms else None
        participant_list = participants.split(",") if participants else None

        # Create filters
        filters = SearchFilters(
            platforms=platform_list,
            participants=participant_list,
            date_from=date_from,
            date_to=date_to,
            has_attachments=has_attachments
        )

        # Perform search
        search_response = await search_agent.search(
            query_text=q,
            filters=filters,
            limit=limit,
            offset=offset,
            include_suggestions=True,
            include_facets=False
        )

        return _convert_search_response(search_response)

    except Exception as e:
        logger.error(f"Search GET API error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/commitments", response_model=SearchResponse)
async def search_commitments(
    request: CommitmentSearchRequest,
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> SearchResponse:
    """
    Search for commitments and promises.

    Specialized search endpoint optimized for finding commitments,
    promises, and action items with contextual filtering.
    """
    try:
        search_response = await search_agent.search_commitments(
            person=request.person,
            topic=request.topic,
            timeframe=request.timeframe,
            limit=request.limit
        )

        return _convert_search_response(search_response)

    except Exception as e:
        logger.error(f"Commitment search API error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Commitment search failed: {str(e)}")


@router.post("/files", response_model=SearchResponse)
async def search_shared_files(
    request: FileSearchRequest,
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> SearchResponse:
    """
    Search for shared files and attachments.

    Specialized search endpoint for finding files, documents,
    and attachments shared in conversations.
    """
    try:
        search_response = await search_agent.search_shared_files(
            contact=request.contact,
            file_type=request.file_type,
            limit=request.limit
        )

        return _convert_search_response(search_response)

    except Exception as e:
        logger.error(f"File search API error: {e}")
        raise HTTPException(
            status_code=500, detail=f"File search failed: {str(e)}")


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Partial query for suggestions",
                   min_length=1),
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> Dict[str, List[str]]:
    """
    Get search suggestions based on partial query.

    Provides intelligent search suggestions to help users
    formulate better search queries.
    """
    try:
        suggestions = search_agent.query_processor.generate_search_suggestions(
            q)

        return {
            "suggestions": suggestions,
            "query": q
        }

    except Exception as e:
        logger.error(f"Search suggestions API error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/stats")
async def get_search_statistics(
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> Dict[str, Any]:
    """
    Get comprehensive search statistics.

    Returns statistics about search usage, performance,
    and component health.
    """
    try:
        stats = await search_agent.get_search_statistics()
        return stats

    except Exception as e:
        logger.error(f"Search stats API error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/health")
async def search_health_check(
    search_agent: HybridSearchAgent = Depends(get_search_agent)
) -> Dict[str, Any]:
    """
    Perform health check on search components.

    Returns the health status of all search system components
    including lexical search, vector search, and AI processing.
    """
    try:
        health = await search_agent.health_check()
        return health

    except Exception as e:
        logger.error(f"Search health check API error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Health check failed: {str(e)}")


# Helper Functions
def _convert_search_response(search_response) -> SearchResponse:
    """Convert internal search response to API response format."""
    try:
        # Convert results
        api_results = []
        for result in search_response.results:
            api_result = SearchResultResponse(
                id=result.id,
                type=result.type.value,
                title=result.title,
                content=result.content,
                snippet=result.snippet,
                metadata=result.metadata,
                ranking={
                    "lexical_score": result.ranking.lexical_score,
                    "vector_score": result.ranking.vector_score,
                    "combined_score": result.ranking.combined_score,
                    "boost_factors": result.ranking.boost_factors,
                    "explanation": result.ranking.explanation
                },
                timestamp=result.timestamp,
                platform=result.platform,
                thread_id=result.thread_id,
                participant_id=result.participant_id,
                url=result.url
            )
            api_results.append(api_result)

        # Convert stats
        api_stats = SearchStatsResponse(
            total_results=search_response.stats.total_results,
            lexical_results=search_response.stats.lexical_results,
            vector_results=search_response.stats.vector_results,
            processing_time_ms=search_response.stats.processing_time_ms,
            query_intent=search_response.stats.query_intent.value if search_response.stats.query_intent else None,
            filters_applied=search_response.stats.filters_applied
        )

        # Convert query
        api_query = {
            "text": search_response.query.text,
            "processed_text": search_response.query.processed_text,
            "intent": search_response.query.intent.value if search_response.query.intent else None,
            "filters": _convert_filters_to_dict(search_response.query.filters),
            "limit": search_response.query.limit,
            "offset": search_response.query.offset
        }

        return SearchResponse(
            results=api_results,
            stats=api_stats,
            query=api_query,
            suggestions=search_response.suggestions,
            facets=search_response.facets
        )

    except Exception as e:
        logger.error(f"Failed to convert search response: {e}")
        raise


def _convert_filters_to_dict(filters: Optional[SearchFilters]) -> Optional[Dict[str, Any]]:
    """Convert SearchFilters to dictionary for API response."""
    if not filters:
        return None

    return {
        "platforms": filters.platforms,
        "participants": filters.participants,
        "date_from": filters.date_from.isoformat() if filters.date_from else None,
        "date_to": filters.date_to.isoformat() if filters.date_to else None,
        "thread_ids": [str(tid) for tid in filters.thread_ids] if filters.thread_ids else None,
        "entity_types": filters.entity_types,
        "has_attachments": filters.has_attachments,
        "content_types": filters.content_types,
        "min_confidence": filters.min_confidence
    }
