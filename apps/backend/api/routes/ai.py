"""
AI API Endpoints

Provides AI-powered functionality:
- Semantic search across messages
- Thread summarization
- Entity extraction from messages
- Contact insights and analytics
- Similar message finding
- Natural language queries
- Communication pattern analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID
import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from db.models.contact import Contact
from db.models.message import Message
from db.models.thread import Thread
from services.ai.embeddings import get_embedding_service
from services.ai.entity_extraction import (
    get_entity_extraction_service,
    EntityType,
)
from services.ai.insight_generator import get_insight_generator
from services.ai.semantic_search import (
    get_semantic_search_engine,
    SearchFilter,
    MessageSearchResult,
)
from services.ai.summary.agent import get_summary_agent, SummaryType
from services.event_bus import get_event_bus
from services.events.types import EventType, AIEvent

logger = logging.getLogger(__name__)

router = APIRouter()

__all__ = ["router"]


# =============================================================================
# Request/Response Models
# =============================================================================


class SemanticSearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str = Field(..., min_length=1, description="Search query text")
    platforms: Optional[list[str]] = Field(default=None, description="Filter by platforms")
    thread_ids: Optional[list[str]] = Field(default=None, description="Filter by thread IDs")
    start_date: Optional[datetime] = Field(default=None, description="Filter messages after this date")
    end_date: Optional[datetime] = Field(default=None, description="Filter messages before this date")
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity score")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


class SemanticSearchResponse(BaseModel):
    """Response model for semantic search."""

    query: str
    results: list[MessageSearchResult]
    total: int

    class Config:
        from_attributes = True


class SummarizeRequest(BaseModel):
    """Request model for thread summarization."""

    summary_type: SummaryType = Field(
        default=SummaryType.BRIEF,
        description="Type of summary to generate"
    )
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration if summary exists"
    )


class SummaryResponse(BaseModel):
    """Response model for summary."""

    thread_id: UUID
    summary_type: str
    content: str
    metadata: dict
    generated_at: datetime

    class Config:
        from_attributes = True


class EntityResponse(BaseModel):
    """Response model for entity."""

    id: UUID
    entity_type: str
    entity_text: str
    confidence: Optional[float]
    metadata: dict

    class Config:
        from_attributes = True


class EntitiesResponse(BaseModel):
    """Response model for entities list."""

    message_id: UUID
    entities: list[EntityResponse]
    total: int


class InsightResponse(BaseModel):
    """Response model for insight."""

    type: str
    title: str
    description: str
    data: dict
    confidence: float
    generated_at: str


class InsightsResponse(BaseModel):
    """Response model for contact insights."""

    contact_id: UUID
    insights: list[InsightResponse]
    total: int


class SimilarMessagesResponse(BaseModel):
    """Response model for similar messages."""

    reference_message_id: UUID
    similar_messages: list[MessageSearchResult]
    total: int


class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language query."""

    question: str = Field(..., min_length=1, description="Natural language question")
    context: Optional[dict] = Field(default=None, description="Additional context for query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


class NaturalLanguageQueryResponse(BaseModel):
    """Response model for natural language query."""

    question: str
    answer: str
    sources: list[MessageSearchResult]
    confidence: float


class MemoryRecommendationContext(BaseModel):
    """Context for generating recommendations."""
    
    current_contact: Optional[str] = Field(default=None, description="Current contact ID")
    current_thread: Optional[str] = Field(default=None, description="Current thread ID")
    current_platform: Optional[str] = Field(default=None, description="Current platform")
    keywords: Optional[list[str]] = Field(default=None, description="Relevant keywords")


class MemoryRecommendationItem(BaseModel):
    """A single memory recommendation."""
    
    id: str
    type: str = Field(description="Recommendation type: commitment, follow_up, relationship, context")
    title: str
    description: str
    priority: float = Field(ge=0.0, le=1.0, description="Priority score")
    memory_id: Optional[str] = None
    contact_id: Optional[str] = None
    action: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class MemoryRecommendationsResponse(BaseModel):
    """Response model for memory recommendations."""
    
    recommendations: list[MemoryRecommendationItem]
    total: int


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics."""
    
    total_memories: int = 0
    memories_by_type: dict = Field(default_factory=dict)
    memories_by_importance: dict = Field(default_factory=dict)
    recent_memories_count: int = 0
    active_commitments: int = 0


# Pattern Analysis Models
class DateRange(BaseModel):
    start: datetime
    end: datetime

class AnalyzePatternsRequest(BaseModel):
    contact_id: Optional[UUID] = None
    platform: Optional[str] = None
    date_range: Optional[DateRange] = None

class TopicTrend(BaseModel):
    topic: str
    frequency: int
    trend: str  # increasing, decreasing, stable

class SentimentPoint(BaseModel):
    date: str
    sentiment: float

class SentimentAnalysis(BaseModel):
    overall_sentiment: str  # positive, neutral, negative
    sentiment_over_time: list[SentimentPoint]

class ResponsePatterns(BaseModel):
    avg_response_time: float
    response_rate: float

class AnalyzePatternsResponse(BaseModel):
    communication_frequency: Dict[str, int]
    topic_trends: list[TopicTrend]
    sentiment_analysis: SentimentAnalysis
    response_patterns: ResponsePatterns


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    summary="AI Services Health",
    description="Check health of AI services"
)
async def ai_health_check() -> dict:
    """
    Check health of AI services.

    Returns:
        Health status of each AI component
    """
    health = {
        "status": "healthy",
        "components": {},
    }

    try:
        # Check embedding service
        try:
            embedding_service = get_embedding_service()
            embedding_health = await embedding_service.health_check()
            health["components"]["embedding_service"] = {
                "status": "healthy" if all(embedding_health.values()) else "degraded",
                "details": embedding_health,
            }
        except Exception as e:
            health["components"]["embedding_service"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Check semantic search engine
        try:
            search_engine = get_semantic_search_engine()
            search_health = await search_engine.health_check()
            health["components"]["semantic_search"] = {
                "status": "healthy" if all(search_health.values()) else "degraded",
                "details": search_health,
            }
        except Exception as e:
            health["components"]["semantic_search"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Check entity extraction
        try:
            extraction_service = get_entity_extraction_service()
            extraction_health = await extraction_service.health_check()
            health["components"]["entity_extraction"] = {
                "status": "healthy" if extraction_health else "unhealthy",
            }
        except Exception as e:
            health["components"]["entity_extraction"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Check insight generator
        try:
            insight_generator = get_insight_generator()
            insight_health = await insight_generator.health_check()
            health["components"]["insight_generator"] = {
                "status": "healthy" if insight_health else "unhealthy",
            }
        except Exception as e:
            health["components"]["insight_generator"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Determine overall status
        component_statuses = [comp["status"] for comp in health["components"].values()]
        if any(s == "unhealthy" for s in component_statuses):
            health["status"] = "degraded"
        elif all(s == "healthy" for s in component_statuses):
            health["status"] = "healthy"
        else:
            health["status"] = "degraded"

        return health

    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# =============================================================================
# AI Endpoints
# =============================================================================


@router.post(
    "/search",
    response_model=SemanticSearchResponse,
    summary="Semantic Search",
    description="Search messages using semantic similarity"
)
async def semantic_search(
    request: SemanticSearchRequest,
    db: AsyncSession = Depends(get_database_session),
) -> SemanticSearchResponse:
    """
    Perform semantic search across messages.

    Uses vector embeddings to find semantically similar messages,
    even if they don't contain exact keyword matches.

    Args:
        request: Search request with query and filters
        db: Database session

    Returns:
        Search results with similarity scores

    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(f"Semantic search: '{request.query}'")

        # Get search engine
        search_engine = get_semantic_search_engine()

        # Build search filters
        filters = SearchFilter(
            platforms=request.platforms,
            thread_ids=request.thread_ids,
            start_date=request.start_date,
            end_date=request.end_date,
            min_score=request.min_score,
        )

        # Perform search
        results = await search_engine.search(
            query=request.query,
            db=db,
            limit=request.limit,
            filters=filters,
        )

        return SemanticSearchResponse(
            query=request.query,
            results=results,
            total=len(results),
        )

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post(
    "/summarize/{thread_id}",
    response_model=SummaryResponse,
    summary="Generate Thread Summary",
    description="Generate AI-powered summary of a conversation thread"
)
async def summarize_thread(
    thread_id: UUID,
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_database_session),
) -> SummaryResponse:
    """
    Generate AI-powered summary of a thread.

    Uses AI to analyze the conversation and generate
    a concise, coherent summary.

    Args:
        thread_id: Thread ID
        request: Summarization request
        db: Database session

    Returns:
        Generated summary

    Raises:
        HTTPException: If thread not found or summarization fails
    """
    try:
        logger.info(f"Summarizing thread {thread_id} ({request.summary_type})")

        # Get summary agent
        summary_agent = get_summary_agent()

        # Generate summary
        summary = await summary_agent.generate_thread_summary(
            thread_id=thread_id,
            db=db,
            summary_type=request.summary_type,
            force_regenerate=request.force_regenerate,
        )

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread {thread_id} not found or summarization failed"
            )

        # Emit event
        try:
            event_bus = get_event_bus()
            await event_bus.publish(
                AIEvent(
                    event_id=str(UUID(int=0)),
                    event_type=EventType.SUMMARY_GENERATED,
                    source="ai_api",
                    payload={
                        "thread_id": str(thread_id),
                        "summary_type": request.summary_type.value,
                    }
                )
            )
        except Exception as e:
            logger.warning(f"Failed to emit SUMMARY_GENERATED event: {e}")

        return SummaryResponse(
            thread_id=thread_id,
            summary_type=summary.summary_type,
            content=summary.content,
            metadata=summary.summary_metadata or {},
            generated_at=summary.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thread summarization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {str(e)}"
        )


@router.get(
    "/entities/{message_id}",
    response_model=EntitiesResponse,
    summary="Get Message Entities",
    description="Extract named entities from a message"
)
async def get_message_entities(
    message_id: UUID,
    entity_type: Optional[EntityType] = Query(default=None, description="Filter by entity type"),
    db: AsyncSession = Depends(get_database_session),
) -> EntitiesResponse:
    """
    Get entities extracted from a message.

    Returns named entities (people, organizations, dates, etc.)
    that were extracted from the message using NLP.

    Args:
        message_id: Message ID
        entity_type: Optional filter by entity type
        db: Database session

    Returns:
        Extracted entities

    Raises:
        HTTPException: If message not found or extraction fails
    """
    try:
        logger.info(f"Extracting entities from message {message_id}")

        # Get message
        message = await db.get(Message, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )

        # Get entity extraction service
        entity_service = get_entity_extraction_service()

        # Get entities
        entities = await entity_service.get_entities_for_message(
            message_id=message_id,
            db=db,
            entity_type=entity_type,
        )

        # If no entities exist, try to extract them
        if not entities:
            logger.info("No entities found, extracting...")

            entities = await entity_service.extract_and_store_entities(
                message=message,
                db=db,
            )

        # Emit event if entities were extracted
        if entities:
            try:
                event_bus = get_event_bus()
                await event_bus.publish(
                    AIEvent(
                        event_id=str(UUID(int=0)),
                        event_type=EventType.ENTITIES_EXTRACTED,
                        source="ai_api",
                        payload={
                            "message_id": str(message_id),
                            "entity_count": len(entities),
                        }
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to emit ENTITIES_EXTRACTED event: {e}")

        # Convert to response format
        entity_responses = [
            EntityResponse(
                id=entity.id,
                entity_type=entity.entity_type,
                entity_text=entity.entity_text,
                confidence=entity.confidence,
                metadata=entity.entity_metadata or {},
            )
            for entity in entities
        ]

        return EntitiesResponse(
            message_id=message_id,
            entities=entity_responses,
            total=len(entity_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction failed: {str(e)}"
        )


@router.post(
    "/insights/{contact_id}",
    response_model=InsightsResponse,
    summary="Generate Contact Insights",
    description="Generate AI-powered insights about communication with a contact"
)
async def generate_contact_insights(
    contact_id: UUID,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_database_session),
) -> InsightsResponse:
    """
    Generate insights for a contact.

    Analyzes communication patterns and generates insights about:
    - Message frequency
    - Trending topics
    - Sentiment analysis
    - Relationship patterns

    Args:
        contact_id: Contact ID
        days: Number of days to analyze (default: 30)
        db: Database session

    Returns:
        Generated insights

    Raises:
        HTTPException: If contact not found or insight generation fails
    """
    try:
        logger.info(f"Generating insights for contact {contact_id} ({days} days)")

        # Check if contact exists
        contact = await db.get(Contact, contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact {contact_id} not found"
            )

        # Get insight generator
        insight_generator = get_insight_generator()

        # Generate insights
        insights = await insight_generator.generate_contact_insights(
            contact_id=contact_id,
            db=db,
            days=days,
        )

        logger.info(f"Generated {len(insights)} insights for contact {contact_id}")

        # Convert to response format
        insight_responses = [
            InsightResponse(
                type=insight.insight_type.value,
                title=insight.title,
                description=insight.description,
                data=insight.data,
                confidence=insight.confidence,
                generated_at=insight.generated_at.isoformat(),
            )
            for insight in insights
        ]

        return InsightsResponse(
            contact_id=contact_id,
            insights=insight_responses,
            total=len(insight_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate contact insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insight generation failed: {str(e)}"
        )


@router.get(
    "/similar/{message_id}",
    response_model=SimilarMessagesResponse,
    summary="Find Similar Messages",
    description="Find messages similar to a given message using semantic similarity"
)
async def find_similar_messages(
    message_id: UUID,
    platforms: Optional[list[str]] = Query(default=None, description="Filter by platforms"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_database_session),
) -> SimilarMessagesResponse:
    """
    Find semantically similar messages.

    Uses vector embeddings to find messages with similar content
    based on semantic similarity.

    Args:
        message_id: Reference message ID
        platforms: Optional platform filter
        limit: Maximum number of results
        db: Database session

    Returns:
        List of similar messages

    Raises:
        HTTPException: If message not found or search fails
    """
    try:
        # Get message
        message = await db.get(Message, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )

        # Find similar messages
        search_engine = get_semantic_search_engine()

        filters = SearchFilter(
            platforms=platforms,
        )

        similar_messages = await search_engine.find_similar_messages(
            message_id=message_id,
            db=db,
            limit=limit,
            filters=filters,
        )

        logger.info(f"Found {len(similar_messages)} similar messages")

        return SimilarMessagesResponse(
            reference_message_id=message_id,
            similar_messages=similar_messages,
            total=len(similar_messages),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar message search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Similar message search failed: {str(e)}"
        )


@router.post(
    "/ask",
    response_model=NaturalLanguageQueryResponse,
    summary="Natural Language Query",
    description="Ask questions about your messages in natural language"
)
async def natural_language_query(
    request: NaturalLanguageQueryRequest,
    db: AsyncSession = Depends(get_database_session),
) -> NaturalLanguageQueryResponse:
    """
    Process natural language query and return answer with relevant messages.

    Uses semantic search to find relevant messages and generates an
    AI-powered answer based on the message content.

    Args:
        request: Natural language query
        db: Database session

    Returns:
        Answer with relevant messages and confidence

    Raises:
        HTTPException: If query processing fails
    """
    try:
        logger.info(f"Processing natural language query: '{request.question}'")

        # Get search engine and summary agent
        search_engine = get_semantic_search_engine()
        summary_agent = get_summary_agent()

        # Perform semantic search to find relevant messages
        results = await search_engine.search(
            query=request.question,
            db=db,
            limit=request.limit,
        )

        if not results:
            return NaturalLanguageQueryResponse(
                question=request.question,
                answer="I couldn't find any relevant messages to answer your question.",
                sources=[],
                confidence=0.0,
            )

        # Build context from search results for answer generation
        context_messages = []
        for result in results[:5]:  # Use top 5 results for context
            if result.message_id:
                message = await db.get(Message, result.message_id)
                if message:
                    context_messages.append(message)

        # Generate answer using LLM
        from services.ai.providers import get_llm_provider, GenerationConfig

        llm_provider = get_llm_provider()

        # Build prompt for answer generation
        prompt = f"""Based on the following messages, answer this question: {request.question}

Messages:
{chr(10).join(f"[{msg.timestamp.isoformat()}] ({msg.platform}): {msg.content.get('text', '')}" for msg in context_messages[:5])}

Provide a direct, concise answer based on the information in these messages.
If the messages don't contain enough information to answer the question, say so.
"""

        config = GenerationConfig(
            temperature=0.3,
            max_tokens=500,
        )

        answer = await llm_provider.generate(
            prompt=prompt,
            model="tinyllama:latest",
            config=config,
        )

        # Calculate confidence based on search scores
        avg_score = sum(r.similarity_score for r in results) / len(results)
        confidence = min(avg_score * 1.2, 1.0)  # Boost slightly, cap at 1.0

        logger.info(f"Generated answer with confidence: {confidence:.2f}")

        return NaturalLanguageQueryResponse(
            question=request.question,
            answer=answer,
            sources=results,
            confidence=confidence,
        )

    except Exception as e:
        logger.error(f"Natural language query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )

@router.post(
    "/analyze/patterns",
    response_model=AnalyzePatternsResponse,
    summary="Analyze Communication Patterns",
    description="Analyze communication patterns, trends, and sentiment"
)
async def analyze_patterns(
    request: AnalyzePatternsRequest,
    db: AsyncSession = Depends(get_database_session),
) -> AnalyzePatternsResponse:
    """
    Analyze communication patterns for a contact or generally.
    
    Generates mock data for now to support the daily summary feature.
    """
    try:
        # Mock Response
        # In a real implementation, this would aggregate data from DB
        
        return AnalyzePatternsResponse(
            communication_frequency={
                "whatsapp": random.randint(5, 50),
                "slack": random.randint(10, 30),
                "discord": random.randint(2, 15)
            },
            topic_trends=[
                TopicTrend(topic="Project A", frequency=12, trend="increasing"),
                TopicTrend(topic="Meeting", frequency=8, trend="stable"),
                TopicTrend(topic="Lunch", frequency=5, trend="decreasing")
            ],
            sentiment_analysis=SentimentAnalysis(
                overall_sentiment="positive",
                sentiment_over_time=[
                    SentimentPoint(date=(datetime.now() - timedelta(days=i)).isoformat(), sentiment=0.5 + (random.random() * 0.4))
                    for i in range(7)
                ]
            ),
            response_patterns=ResponsePatterns(
                avg_response_time=15.5,
                response_rate=0.85
            )
        )
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pattern analysis failed: {str(e)}"
        )
