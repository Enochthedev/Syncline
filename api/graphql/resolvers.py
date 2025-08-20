"""GraphQL resolvers for MESH ingestion system."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from db.session import get_db
from db.models.message import Message as MessageModel
from db.models.thread import Thread as ThreadModel
from db.models.participant import Participant as ParticipantModel
from db.models.entity import Entity as EntityModel
from db.models.summary import Summary as SummaryModel
from db.models.memory import ContactDossier as ContactDossierModel, FileReference as FileReferenceModel
from services.ai.search.agent import HybridSearchAgent
from services.ai.summary.agent import SummaryGenerationAgent
from .types import (
    Message, Thread, Participant, Entity, Summary, ContactDossier, FileReference,
    SearchResponse, SearchFiltersInput, PaginationInput, DateRangeInput, SummaryRequestInput
)
from .converters import (
    convert_message, convert_thread, convert_participant, convert_summary,
    convert_contact_dossier, convert_file_reference, convert_search_response
)

logger = logging.getLogger(__name__)


class Resolvers:
    """GraphQL resolvers for all queries and mutations."""

    def __init__(self):
        self._search_agent: Optional[HybridSearchAgent] = None
        self._summary_agent: Optional[SummaryGenerationAgent] = None

    async def get_search_agent(self) -> HybridSearchAgent:
        """Get the search agent instance."""
        if self._search_agent is None:
            self._search_agent = HybridSearchAgent()
            await self._search_agent.initialize()
        return self._search_agent

    async def get_summary_agent(self) -> SummaryGenerationAgent:
        """Get the summary agent instance."""
        if self._summary_agent is None:
            self._summary_agent = SummaryGenerationAgent()
            await self._summary_agent.initialize()
        return self._summary_agent

    # Query resolvers
    async def get_messages(
        self,
        info,
        filters: Optional[SearchFiltersInput] = None,
        pagination: Optional[PaginationInput] = None,
        date_range: Optional[DateRangeInput] = None
    ) -> List[Message]:
        """Get messages with optional filtering."""
        try:
            async with get_db() as db:
                query = select(MessageModel)

                # Apply filters
                if filters:
                    if filters.platforms:
                        query = query.where(
                            MessageModel.platform.in_(filters.platforms))
                    if filters.thread_ids:
                        thread_uuids = [UUID(tid)
                                        for tid in filters.thread_ids]
                        query = query.where(
                            MessageModel.thread_id.in_(thread_uuids))

                # Apply date range
                if date_range:
                    if date_range.start:
                        query = query.where(
                            MessageModel.timestamp >= date_range.start)
                    if date_range.end:
                        query = query.where(
                            MessageModel.timestamp <= date_range.end)

                # Apply pagination
                if pagination:
                    query = query.offset(
                        pagination.offset).limit(pagination.limit)
                else:
                    query = query.limit(50)  # Default limit

                # Order by timestamp
                query = query.order_by(desc(MessageModel.timestamp))

                result = await db.execute(query)
                messages = result.scalars().all()

                return [convert_message(msg) for msg in messages]

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise

    async def get_message(self, info, id: str) -> Optional[Message]:
        """Get a specific message by ID."""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(MessageModel).where(MessageModel.id == UUID(id))
                )
                message = result.scalar_one_or_none()

                if message:
                    return convert_message(message)
                return None

        except Exception as e:
            logger.error(f"Error getting message {id}: {e}")
            raise

    async def get_threads(
        self,
        info,
        platform: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[Thread]:
        """Get threads with optional filtering."""
        try:
            async with get_db() as db:
                query = select(ThreadModel)

                if platform:
                    query = query.where(ThreadModel.platform == platform)

                # Apply pagination
                if pagination:
                    query = query.offset(
                        pagination.offset).limit(pagination.limit)
                else:
                    query = query.limit(100)  # Default limit

                # Order by last message time
                query = query.order_by(desc(ThreadModel.last_message_at))

                result = await db.execute(query)
                threads = result.scalars().all()

                return [convert_thread(thread) for thread in threads]

        except Exception as e:
            logger.error(f"Error getting threads: {e}")
            raise

    async def get_thread(self, info, id: str) -> Optional[Thread]:
        """Get a specific thread by ID."""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(ThreadModel).where(ThreadModel.id == UUID(id))
                )
                thread = result.scalar_one_or_none()

                if thread:
                    return convert_thread(thread)
                return None

        except Exception as e:
            logger.error(f"Error getting thread {id}: {e}")
            raise

    async def get_participants(
        self,
        info,
        platform: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[Participant]:
        """Get participants with optional filtering."""
        try:
            async with get_db() as db:
                query = select(ParticipantModel)

                if platform:
                    query = query.where(ParticipantModel.platform == platform)

                # Apply pagination
                if pagination:
                    query = query.offset(
                        pagination.offset).limit(pagination.limit)
                else:
                    query = query.limit(100)  # Default limit

                result = await db.execute(query)
                participants = result.scalars().all()

                return [convert_participant(participant) for participant in participants]

        except Exception as e:
            logger.error(f"Error getting participants: {e}")
            raise

    async def get_participant(self, info, id: str) -> Optional[Participant]:
        """Get a specific participant by ID."""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(ParticipantModel).where(
                        ParticipantModel.id == UUID(id))
                )
                participant = result.scalar_one_or_none()

                if participant:
                    return convert_participant(participant)
                return None

        except Exception as e:
            logger.error(f"Error getting participant {id}: {e}")
            raise

    async def search_messages(
        self,
        info,
        query: str,
        filters: Optional[SearchFiltersInput] = None,
        pagination: Optional[PaginationInput] = None
    ) -> SearchResponse:
        """Perform hybrid search across messages."""
        try:
            search_agent = await self.get_search_agent()

            # Convert GraphQL filters to search filters
            from services.ai.search.types import SearchFilters
            search_filters = None
            if filters:
                search_filters = SearchFilters(
                    platforms=filters.platforms,
                    participants=filters.participants,
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                    thread_ids=[
                        UUID(tid) for tid in filters.thread_ids] if filters.thread_ids else None,
                    entity_types=filters.entity_types,
                    has_attachments=filters.has_attachments,
                    content_types=filters.content_types,
                    min_confidence=filters.min_confidence
                )

            # Set pagination defaults
            limit = pagination.limit if pagination else 50
            offset = pagination.offset if pagination else 0

            # Perform search
            search_response = await search_agent.search(
                query_text=query,
                filters=search_filters,
                limit=limit,
                offset=offset,
                include_suggestions=True,
                include_facets=True
            )

            return convert_search_response(search_response)

        except Exception as e:
            logger.error(f"Error performing search: {e}")
            raise

    async def get_contact_dossiers(
        self,
        info,
        user_id: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[ContactDossier]:
        """Get contact dossiers."""
        try:
            async with get_db() as db:
                query = select(ContactDossierModel)

                if user_id:
                    query = query.where(
                        ContactDossierModel.user_id == UUID(user_id))

                # Apply pagination
                if pagination:
                    query = query.offset(
                        pagination.offset).limit(pagination.limit)
                else:
                    query = query.limit(50)  # Default limit

                # Order by last updated
                query = query.order_by(desc(ContactDossierModel.last_updated))

                result = await db.execute(query)
                dossiers = result.scalars().all()

                return [convert_contact_dossier(dossier) for dossier in dossiers]

        except Exception as e:
            logger.error(f"Error getting contact dossiers: {e}")
            raise

    async def get_contact_dossier(self, info, id: str) -> Optional[ContactDossier]:
        """Get a specific contact dossier by ID."""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(ContactDossierModel).where(
                        ContactDossierModel.id == UUID(id))
                )
                dossier = result.scalar_one_or_none()

                if dossier:
                    return convert_contact_dossier(dossier)
                return None

        except Exception as e:
            logger.error(f"Error getting contact dossier {id}: {e}")
            raise

    async def get_summaries(
        self,
        info,
        request: SummaryRequestInput,
        pagination: Optional[PaginationInput] = None
    ) -> List[Summary]:
        """Get summaries with filtering."""
        try:
            async with get_db() as db:
                query = select(SummaryModel)

                # Apply filters from request
                query = query.where(
                    SummaryModel.scope_type == request.scope_type)

                if request.scope_id:
                    query = query.where(
                        SummaryModel.scope_id == UUID(request.scope_id))

                if request.summary_type:
                    query = query.where(SummaryModel.type ==
                                        request.summary_type)

                if request.since_date:
                    query = query.where(
                        SummaryModel.created_at >= request.since_date)

                # Apply pagination
                if pagination:
                    query = query.offset(
                        pagination.offset).limit(pagination.limit)
                else:
                    query = query.limit(50)  # Default limit

                # Order by creation time
                query = query.order_by(desc(SummaryModel.created_at))

                result = await db.execute(query)
                summaries = result.scalars().all()

                return [convert_summary(summary) for summary in summaries]

        except Exception as e:
            logger.error(f"Error getting summaries: {e}")
            raise

    async def get_file_references(
        self,
        info,
        contact: Optional[str] = None,
        file_type: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[FileReference]:
        """Get file references with filtering."""
        try:
            async with get_db() as db:
                query = select(FileReferenceModel)

                if file_type:
                    query = query.where(
                        FileReferenceModel.file_type == file_type)

                # Apply pagination
                if pagination:
                    query = query.offset(
                        pagination.offset).limit(pagination.limit)
                else:
                    query = query.limit(50)  # Default limit

                # Order by shared time
                query = query.order_by(desc(FileReferenceModel.shared_at))

                result = await db.execute(query)
                files = result.scalars().all()

                return [convert_file_reference(file_ref) for file_ref in files]

        except Exception as e:
            logger.error(f"Error getting file references: {e}")
            raise
