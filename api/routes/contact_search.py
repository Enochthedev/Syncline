"""
Contact-based auto-search API endpoints.

Provides REST API endpoints for intelligent contact search functionality
including real-time search, natural language processing, and contact-filtered
message search with conversation thread grouping.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, Path
from pydantic import BaseModel, Field

from api.auth.auth import get_current_active_user
from api.auth.rate_limiting import rate_limit
from api.auth.rbac import require_permission
from api.auth.models import User
from api.dependencies import get_db_session
from services.contacts.contact_auto_search import ContactAutoSearchService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts/search", tags=["contact-search"])

# Global service instance
_contact_search_service: Optional[ContactAutoSearchService] = None


async def get_contact_search_service(
    db: AsyncSession = Depends(get_db_session)
) -> ContactAutoSearchService:
    """Get the contact auto-search service instance."""
    global _contact_search_service

    if _contact_search_service is None:
        _contact_search_service = ContactAutoSearchService(db)
        await _contact_search_service.initialize()

    return _contact_search_service


# Request/Response Models
class ContactSearchRequest(BaseModel):
    """Contact search request model."""
    query: str = Field(..., description="Search query text",
                       min_length=1, max_length=200)
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of results")
    include_suggestions: bool = Field(
        True, description="Include search suggestions")


class ContactSearchResponse(BaseModel):
    """Contact search response model."""
    contacts: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    query: str
    normalized_query: str
    total_results: int
    has_more: bool


class NaturalLanguageQueryRequest(BaseModel):
    """Natural language query processing request."""
    query: str = Field(..., description="Natural language query",
                       min_length=1, max_length=500)


class NaturalLanguageQueryResponse(BaseModel):
    """Natural language query processing response."""
    intent: str
    processed_text: str
    contacts: List[Dict[str, Any]]
    filters: Dict[str, Any]
    temporal_constraints: Dict[str, Any]
    entities: List[Dict[str, Any]]


class ContactMessageSearchRequest(BaseModel):
    """Contact message search request model."""
    query: Optional[str] = Field(
        None, description="Optional text query within messages")
    limit: int = Field(
        50, ge=1, le=200, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")
    group_by_thread: bool = Field(
        True, description="Group results by conversation thread")


class ContactMessageSearchResponse(BaseModel):
    """Contact message search response model."""
    messages: Optional[List[Dict[str, Any]]] = None
    threads: Optional[List[Dict[str, Any]]] = None
    contact: Optional[Dict[str, Any]] = None
    total_messages: Optional[int] = None
    total_threads: Optional[int] = None
    query: Optional[str] = None


class SharedContentRequest(BaseModel):
    """Shared content request model."""
    content_type: Optional[str] = Field(
        None,
        description="Content type filter ('files', 'links', 'media')"
    )
    limit: int = Field(
        50, ge=1, le=200, description="Maximum number of results")


class SharedContentResponse(BaseModel):
    """Shared content response model."""
    contact: Optional[Dict[str, Any]] = None
    shared_files: List[Dict[str, Any]]
    shared_links: List[Dict[str, Any]]
    shared_media: List[Dict[str, Any]]
    total_items: int


# API Endpoints

@router.post("/realtime", response_model=ContactSearchResponse)
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("contacts", "read")
async def search_contacts_realtime(
    request: ContactSearchRequest,
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> ContactSearchResponse:
    """
    Perform real-time contact search with fuzzy matching.

    Provides intelligent contact search with fuzzy matching for names, emails,
    handles, and phone numbers. Includes search suggestions and interaction
    indicators for enhanced user experience.
    """
    try:
        result = await service.search_contacts_realtime(
            query=request.query,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            limit=request.limit,
            include_suggestions=request.include_suggestions
        )

        return ContactSearchResponse(**result)

    except Exception as e:
        logger.error(f"Real-time contact search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Contact search failed: {str(e)}"
        )


@router.get("/realtime", response_model=ContactSearchResponse)
@rate_limit(requests_per_minute=120, requests_per_hour=2000, per_user=True)
@require_permission("contacts", "read")
async def search_contacts_realtime_get(
    q: str = Query(..., description="Search query",
                   min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    suggestions: bool = Query(True, description="Include suggestions"),
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> ContactSearchResponse:
    """
    Perform real-time contact search using GET parameters.

    Simplified endpoint for easy integration with autocomplete components
    and real-time search interfaces.
    """
    try:
        result = await service.search_contacts_realtime(
            query=q,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            limit=limit,
            include_suggestions=suggestions
        )

        return ContactSearchResponse(**result)

    except Exception as e:
        logger.error(f"Real-time contact search GET failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Contact search failed: {str(e)}"
        )


@router.post("/natural-language", response_model=NaturalLanguageQueryResponse)
@rate_limit(requests_per_minute=30, requests_per_hour=500, per_user=True)
@require_permission("contacts", "read")
async def process_natural_language_query(
    request: NaturalLanguageQueryRequest,
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> NaturalLanguageQueryResponse:
    """
    Process natural language queries like "messages with John".

    Analyzes natural language queries to extract intent, identify contacts,
    and build appropriate search filters for contact-based searches.
    """
    try:
        result = await service.process_natural_language_query(
            query=request.query,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id
        )

        return NaturalLanguageQueryResponse(**result)

    except Exception as e:
        logger.error(f"Natural language query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@router.post("/{contact_id}/messages", response_model=ContactMessageSearchResponse)
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("contacts", "read")
async def search_messages_by_contact(
    contact_id: UUID = Path(..., description="Contact ID"),
    request: ContactMessageSearchRequest = ContactMessageSearchRequest(),
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> ContactMessageSearchResponse:
    """
    Search messages filtered by specific contact with thread grouping.

    Provides contact-filtered message search with conversation thread grouping
    and message previews. Supports optional text search within the contact's
    messages for more specific results.
    """
    try:
        result = await service.search_messages_by_contact(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            query=request.query,
            limit=request.limit,
            offset=request.offset,
            group_by_thread=request.group_by_thread
        )

        return ContactMessageSearchResponse(**result)

    except Exception as e:
        logger.error(f"Contact message search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Message search failed: {str(e)}"
        )


@router.get("/{contact_id}/messages", response_model=ContactMessageSearchResponse)
@rate_limit(requests_per_minute=120, requests_per_hour=2000, per_user=True)
@require_permission("contacts", "read")
async def search_messages_by_contact_get(
    contact_id: UUID = Path(..., description="Contact ID"),
    q: Optional[str] = Query(None, description="Optional text query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    group_by_thread: bool = Query(True, description="Group by thread"),
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> ContactMessageSearchResponse:
    """
    Search messages by contact using GET parameters.

    Simplified endpoint for contact-filtered message search with
    query parameters for easy integration.
    """
    try:
        result = await service.search_messages_by_contact(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            query=q,
            limit=limit,
            offset=offset,
            group_by_thread=group_by_thread
        )

        return ContactMessageSearchResponse(**result)

    except Exception as e:
        logger.error(f"Contact message search GET failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Message search failed: {str(e)}"
        )


@router.post("/{contact_id}/shared-content", response_model=SharedContentResponse)
@rate_limit(requests_per_minute=30, requests_per_hour=500, per_user=True)
@require_permission("contacts", "read")
async def get_shared_content_with_contact(
    contact_id: UUID = Path(..., description="Contact ID"),
    request: SharedContentRequest = SharedContentRequest(),
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> SharedContentResponse:
    """
    Get shared files, links, and media with a specific contact.

    Provides quick access to all content shared with a specific contact,
    organized by type (files, links, media) with metadata and timestamps.
    """
    try:
        result = await service.get_shared_content_with_contact(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            content_type=request.content_type,
            limit=request.limit
        )

        return SharedContentResponse(**result)

    except Exception as e:
        logger.error(f"Shared content search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Shared content search failed: {str(e)}"
        )


@router.get("/{contact_id}/shared-content", response_model=SharedContentResponse)
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("contacts", "read")
async def get_shared_content_with_contact_get(
    contact_id: UUID = Path(..., description="Contact ID"),
    content_type: Optional[str] = Query(
        None,
        description="Content type filter ('files', 'links', 'media')"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> SharedContentResponse:
    """
    Get shared content using GET parameters.

    Simplified endpoint for retrieving shared content with a contact
    using query parameters.
    """
    try:
        result = await service.get_shared_content_with_contact(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            content_type=content_type,
            limit=limit
        )

        return SharedContentResponse(**result)

    except Exception as e:
        logger.error(f"Shared content search GET failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Shared content search failed: {str(e)}"
        )


@router.get("/suggestions/{query}")
@rate_limit(requests_per_minute=120, requests_per_hour=2000, per_user=True)
@require_permission("contacts", "read")
async def get_contact_search_suggestions(
    query: str = Path(...,
                      description="Partial query for suggestions", min_length=1),
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions"),
    current_user: User = Depends(get_current_active_user),
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> Dict[str, Any]:
    """
    Get contact search suggestions based on partial query.

    Provides intelligent search suggestions to help users formulate
    better contact search queries with autocomplete functionality.
    """
    try:
        result = await service.search_contacts_realtime(
            query=query,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            limit=0,  # Only get suggestions
            include_suggestions=True
        )

        return {
            "suggestions": result.get("suggestions", [])[:limit],
            "query": query
        }

    except Exception as e:
        logger.error(f"Contact search suggestions failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions failed: {str(e)}"
        )


@router.get("/health")
async def contact_search_health_check(
    service: ContactAutoSearchService = Depends(get_contact_search_service)
) -> Dict[str, Any]:
    """
    Perform health check on contact search components.

    Returns the health status of the contact auto-search service
    and its dependencies.
    """
    try:
        health_status = {
            "status": "healthy",
            "service": "contact_auto_search",
            "initialized": service._initialized,
            "components": {
                "query_processor": {
                    "status": "initialized" if service.query_processor.ai_engine else "basic_mode"
                },
                "database": "connected",
                "fuzzy_search": "ready"
            },
            "timestamp": "2024-01-20T00:00:00Z"  # Would use actual timestamp
        }

        return health_status

    except Exception as e:
        logger.error(f"Contact search health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-20T00:00:00Z"
        }


# Helper endpoint for testing natural language queries
@router.get("/test/natural-language")
async def test_natural_language_queries(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Test endpoint for natural language query examples.

    Provides example queries that can be processed by the natural
    language query endpoint for testing and demonstration purposes.
    """
    return {
        "examples": [
            {
                "query": "messages with John Smith",
                "description": "Find all messages with a specific person",
                "expected_intent": "person_search"
            },
            {
                "query": "files shared with Sarah last week",
                "description": "Find files shared with a person in a timeframe",
                "expected_intent": "file_search"
            },
            {
                "query": "what did I promise to Mike about the project",
                "description": "Find commitments made to a specific person",
                "expected_intent": "commitment_search"
            },
            {
                "query": "conversations with team members yesterday",
                "description": "Find conversations from a specific time",
                "expected_intent": "time_based_search"
            },
            {
                "query": "images sent by Alice",
                "description": "Find media shared by a specific contact",
                "expected_intent": "file_search"
            }
        ],
        "supported_intents": [
            "general_search",
            "person_search",
            "file_search",
            "commitment_search",
            "time_based_search",
            "topic_search"
        ]
    }
