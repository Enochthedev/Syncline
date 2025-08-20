"""GraphQL schema definition for MESH ingestion system."""

import strawberry
from typing import List, Optional

from .types import (
    Message, Thread, Participant, Entity, Summary, ContactDossier, FileReference,
    SearchResponse, SearchFiltersInput, PaginationInput, DateRangeInput, SummaryRequestInput
)
from .resolvers import Resolvers


@strawberry.type
class Query:
    """GraphQL Query root type."""

    def __init__(self):
        self.resolvers = Resolvers()

    @strawberry.field
    async def messages(
        self,
        info,
        filters: Optional[SearchFiltersInput] = None,
        pagination: Optional[PaginationInput] = None,
        date_range: Optional[DateRangeInput] = None
    ) -> List[Message]:
        """Get messages with optional filtering and pagination."""
        return await self.resolvers.get_messages(info, filters, pagination, date_range)

    @strawberry.field
    async def message(self, info, id: str) -> Optional[Message]:
        """Get a specific message by ID."""
        return await self.resolvers.get_message(info, id)

    @strawberry.field
    async def threads(
        self,
        info,
        platform: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[Thread]:
        """Get threads with optional filtering and pagination."""
        return await self.resolvers.get_threads(info, platform, pagination)

    @strawberry.field
    async def thread(self, info, id: str) -> Optional[Thread]:
        """Get a specific thread by ID."""
        return await self.resolvers.get_thread(info, id)

    @strawberry.field
    async def participants(
        self,
        info,
        platform: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[Participant]:
        """Get participants with optional filtering and pagination."""
        return await self.resolvers.get_participants(info, platform, pagination)

    @strawberry.field
    async def participant(self, info, id: str) -> Optional[Participant]:
        """Get a specific participant by ID."""
        return await self.resolvers.get_participant(info, id)

    @strawberry.field
    async def search(
        self,
        info,
        query: str,
        filters: Optional[SearchFiltersInput] = None,
        pagination: Optional[PaginationInput] = None
    ) -> SearchResponse:
        """Perform hybrid search across all message data."""
        return await self.resolvers.search_messages(info, query, filters, pagination)

    @strawberry.field
    async def contact_dossiers(
        self,
        info,
        user_id: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[ContactDossier]:
        """Get contact dossiers with optional filtering."""
        return await self.resolvers.get_contact_dossiers(info, user_id, pagination)

    @strawberry.field
    async def contact_dossier(self, info, id: str) -> Optional[ContactDossier]:
        """Get a specific contact dossier by ID."""
        return await self.resolvers.get_contact_dossier(info, id)

    @strawberry.field
    async def summaries(
        self,
        info,
        request: SummaryRequestInput,
        pagination: Optional[PaginationInput] = None
    ) -> List[Summary]:
        """Get summaries with filtering (implements 'summarize since [date]' functionality)."""
        return await self.resolvers.get_summaries(info, request, pagination)

    @strawberry.field
    async def file_references(
        self,
        info,
        contact: Optional[str] = None,
        file_type: Optional[str] = None,
        pagination: Optional[PaginationInput] = None
    ) -> List[FileReference]:
        """Get file references with metadata search capabilities."""
        return await self.resolvers.get_file_references(info, contact, file_type, pagination)


@strawberry.type
class Mutation:
    """GraphQL Mutation root type."""

    @strawberry.field
    async def placeholder(self, info) -> str:
        """Placeholder mutation - mutations will be added in future iterations."""
        return "Mutations not yet implemented"


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
