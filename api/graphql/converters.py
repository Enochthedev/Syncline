"""Conversion utilities for GraphQL resolvers."""

import json
from typing import Optional, Dict, Any
from db.models.message import Message as MessageModel
from db.models.thread import Thread as ThreadModel
from db.models.participant import Participant as ParticipantModel
from db.models.summary import Summary as SummaryModel
from db.models.memory import ContactDossier as ContactDossierModel, FileReference as FileReferenceModel
from .types import (
    Message, Thread, Participant, Summary, ContactDossier, FileReference,
    SearchResponse, SearchResult, SearchStats
)


def serialize_json(data: Any) -> Optional[str]:
    """Serialize data to JSON string."""
    if data is None:
        return None
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return None


def convert_message(message: MessageModel) -> Message:
    """Convert database message to GraphQL type."""
    return Message(
        id=str(message.id),
        platform=message.platform,
        platform_message_id=message.platform_message_id,
        thread_id=str(message.thread_id),
        sender_id=str(message.sender_id),
        content_text=message.content_text,
        content_html=message.content_html,
        content_markdown=message.content_markdown,
        timestamp=message.timestamp,
        created_at=message.created_at,
        updated_at=message.updated_at,
        message_metadata=serialize_json(message.message_metadata),
        raw_data=serialize_json(message.raw_data)
    )


def convert_thread(thread: ThreadModel) -> Thread:
    """Convert database thread to GraphQL type."""
    return Thread(
        id=str(thread.id),
        platform=thread.platform,
        platform_thread_id=thread.platform_thread_id,
        title=thread.title,
        participants=[str(p) for p in (thread.participants or [])],
        message_count=thread.message_count or 0,
        last_message_at=thread.last_message_at,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        thread_metadata=serialize_json(thread.thread_metadata)
    )


def convert_participant(participant: ParticipantModel) -> Participant:
    """Convert database participant to GraphQL type."""
    return Participant(
        id=str(participant.id),
        platform=participant.platform,
        platform_user_id=participant.platform_user_id,
        display_name=participant.display_name,
        email=participant.email,
        phone=participant.phone,
        avatar_url=participant.avatar_url,
        created_at=participant.created_at,
        updated_at=participant.updated_at,
        participant_metadata=serialize_json(participant.participant_metadata)
    )


def convert_summary(summary: SummaryModel) -> Summary:
    """Convert database summary to GraphQL type."""
    return Summary(
        id=str(summary.id),
        type=summary.type,
        scope_type=summary.scope_type,
        scope_id=str(summary.scope_id) if summary.scope_id else None,
        content=summary.content,
        key_points=summary.key_points,
        action_items=summary.action_items,
        entities=[str(e)
                  for e in summary.entities] if summary.entities else None,
        timeframe_start=summary.timeframe_start,
        timeframe_end=summary.timeframe_end,
        created_at=summary.created_at,
        summary_metadata=serialize_json(summary.summary_metadata)
    )


def convert_contact_dossier(dossier: ContactDossierModel) -> ContactDossier:
    """Convert database contact dossier to GraphQL type."""
    return ContactDossier(
        id=str(dossier.id),
        contact_id=str(dossier.contact_id),
        user_id=str(dossier.user_id),
        first_interaction=dossier.first_interaction,
        last_interaction=dossier.last_interaction,
        total_messages=dossier.total_messages or 0,
        total_threads=dossier.total_threads or 0,
        relationship_strength=dossier.relationship_strength or 0.0,
        communication_style=dossier.communication_style,
        interaction_frequency=dossier.interaction_frequency,
        key_topics=dossier.key_topics,
        common_entities=dossier.common_entities,
        summary=dossier.summary,
        personality_insights=dossier.personality_insights,
        suggested_actions=dossier.suggested_actions,
        generated_at=dossier.generated_at,
        last_updated=dossier.last_updated
    )


def convert_file_reference(file_ref: FileReferenceModel) -> FileReference:
    """Convert database file reference to GraphQL type."""
    return FileReference(
        id=str(file_ref.id),
        filename=file_ref.filename,
        file_type=file_ref.file_type,
        file_size=file_ref.file_size,
        file_url=file_ref.file_url,
        shared_by=str(file_ref.shared_by),
        shared_with=file_ref.shared_with,
        shared_at=file_ref.shared_at,
        source_message_id=str(
            file_ref.source_message_id) if file_ref.source_message_id else None,
        source_thread_id=str(
            file_ref.source_thread_id) if file_ref.source_thread_id else None,
        source_platform=file_ref.source_platform,
        content_summary=file_ref.content_summary,
        extracted_topics=file_ref.extracted_topics
    )


def convert_search_response(search_response) -> SearchResponse:
    """Convert internal search response to GraphQL type."""
    # Convert results
    results = []
    for result in search_response.results:
        results.append(SearchResult(
            id=result.id,
            type=result.type.value,
            title=result.title,
            content=result.content,
            snippet=result.snippet,
            metadata=serialize_json(result.metadata),
            ranking=serialize_json({
                "lexical_score": result.ranking.lexical_score,
                "vector_score": result.ranking.vector_score,
                "combined_score": result.ranking.combined_score,
                "boost_factors": result.ranking.boost_factors,
                "explanation": result.ranking.explanation
            }),
            timestamp=result.timestamp,
            platform=result.platform,
            thread_id=str(result.thread_id) if result.thread_id else None,
            participant_id=str(
                result.participant_id) if result.participant_id else None,
            url=result.url
        ))

    # Convert stats
    stats = SearchStats(
        total_results=search_response.stats.total_results,
        lexical_results=search_response.stats.lexical_results,
        vector_results=search_response.stats.vector_results,
        processing_time_ms=search_response.stats.processing_time_ms,
        query_intent=search_response.stats.query_intent.value if search_response.stats.query_intent else None,
        filters_applied=search_response.stats.filters_applied
    )

    # Convert query
    query = {
        "text": search_response.query.text,
        "processed_text": search_response.query.processed_text,
        "intent": search_response.query.intent.value if search_response.query.intent else None,
        "filters": convert_filters_to_dict(search_response.query.filters),
        "limit": search_response.query.limit,
        "offset": search_response.query.offset
    }

    return SearchResponse(
        results=results,
        stats=stats,
        query=serialize_json(query),
        suggestions=search_response.suggestions,
        facets=serialize_json(search_response.facets)
    )


def convert_filters_to_dict(filters) -> Optional[Dict[str, Any]]:
    """Convert SearchFilters to dictionary."""
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
