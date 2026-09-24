"""
Contacts API Endpoints

Provides endpoints for:
- Listing contacts with filtering
- Getting contact details
- Getting threads for a contact
- Merging contacts manually
- Splitting merged contacts
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import (
    PaginationParams,
    get_database_session,
    get_pagination_params,
)
from db.models.contact import Contact
from db.models.participant import Participant
from db.models.thread import Thread
from services.event_bus import get_event_bus
from services.events.types import ContactEvent, EventType

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class ContactResponse(BaseModel):
    """Contact response model."""

    id: UUID = Field(..., description="Contact ID")
    canonical_name: str = Field(..., description="Primary contact name")
    emails: list[str] | None = Field(None, description="Email addresses")
    phones: list[str] | None = Field(None, description="Phone numbers")
    platform_identities: dict[str, str] | None = Field(
        None, description="Platform-specific IDs"
    )
    contact_metadata: dict[str, Any] | None = Field(
        None, description="Additional metadata"
    )
    participant_count: int = Field(
        default=0, description="Number of platform participants"
    )
    thread_count: int = Field(default=0, description="Number of threads")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Paginated contact list response."""

    contacts: list[ContactResponse] = Field(..., description="List of contacts")
    total: int = Field(..., description="Total number of contacts")
    skip: int = Field(..., description="Number of contacts skipped")
    limit: int = Field(..., description="Maximum contacts returned")


class ContactDetailResponse(ContactResponse):
    """Detailed contact response with participants."""

    participants: list[dict[str, Any]] = Field(
        default_factory=list, description="Platform participants"
    )


class ThreadSummary(BaseModel):
    """Thread summary for contact."""

    id: UUID = Field(..., description="Thread ID")
    platform: str = Field(..., description="Platform name")
    platform_thread_id: str = Field(..., description="Platform thread ID")
    title: str | None = Field(None, description="Thread title")
    message_count: int = Field(default=0, description="Number of messages")
    first_message_at: datetime | None = Field(
        None, description="First message timestamp"
    )
    last_message_at: datetime | None = Field(None, description="Last message timestamp")

    class Config:
        from_attributes = True


class ContactThreadsResponse(BaseModel):
    """Contact threads response."""

    contact_id: UUID = Field(..., description="Contact ID")
    contact_name: str = Field(..., description="Contact name")
    threads: list[ThreadSummary] = Field(..., description="List of threads")
    total: int = Field(..., description="Total number of threads")


class MergeContactsRequest(BaseModel):
    """Request to merge contacts."""

    source_contact_ids: list[UUID] = Field(
        ..., description="Contact IDs to merge (will be deleted)"
    )
    target_contact_id: UUID = Field(..., description="Target contact ID (will be kept)")
    merge_strategy: str = Field(
        default="prefer_target",
        description="Merge strategy: prefer_target, prefer_source, combine",
    )


class MergeContactsResponse(BaseModel):
    """Response from merging contacts."""

    merged_contact: ContactResponse = Field(..., description="Resulting merged contact")
    merged_count: int = Field(..., description="Number of contacts merged")
    message: str = Field(..., description="Status message")


class SplitContactRequest(BaseModel):
    """Request to split a contact."""

    contact_id: UUID = Field(..., description="Contact ID to split")
    platform_identities_to_split: list[str] = Field(
        ...,
        description="Platform identities to move to new contact (e.g., ['gmail', 'slack'])",
    )
    new_contact_name: str = Field(..., description="Name for the new contact")


class SplitContactResponse(BaseModel):
    """Response from splitting a contact."""

    original_contact: ContactResponse = Field(
        ..., description="Original contact (modified)"
    )
    new_contact: ContactResponse = Field(..., description="New contact created")
    message: str = Field(..., description="Status message")


# =============================================================================
# Inbox Models (Contacts with Last Message)
# =============================================================================


class LastMessageInfo(BaseModel):
    """Last message preview info."""

    message_id: UUID | None = Field(None, description="Message ID")
    content: str | None = Field(None, description="Message preview text")
    platform: str | None = Field(None, description="Platform of last message")
    timestamp: datetime | None = Field(None, description="Message timestamp")
    sender_name: str | None = Field(None, description="Sender name")
    is_from_me: bool = Field(
        default=False, description="Whether message is from current user"
    )


class InboxContact(BaseModel):
    """Contact with last message info for inbox view."""

    id: UUID = Field(..., description="Contact ID")
    canonical_name: str = Field(..., description="Contact name")
    emails: list[str] | None = Field(None, description="Email addresses")
    phones: list[str] | None = Field(None, description="Phone numbers")
    platform_identities: dict[str, str] | None = Field(
        None, description="Platform-specific IDs"
    )
    avatar_url: str | None = Field(None, description="Avatar URL")
    last_message: LastMessageInfo | None = Field(None, description="Last message info")
    unread_count: int = Field(default=0, description="Unread message count")
    platforms: list[str] = Field(
        default_factory=list, description="Connected platforms"
    )


class InboxResponse(BaseModel):
    """Inbox response with contacts sorted by last message."""

    contacts: list[InboxContact] = Field(..., description="Contacts with last messages")
    total: int = Field(..., description="Total contacts with messages")
    skip: int = Field(..., description="Offset")
    limit: int = Field(..., description="Limit")


# =============================================================================
# Contact Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ContactListResponse,
    summary="List Contacts",
    description="List all contacts with optional filtering and pagination",
)
async def list_contacts(
    db: AsyncSession = Depends(get_database_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    search: str | None = Query(None, description="Search in contact name or email"),
    platform: str | None = Query(None, description="Filter by platform identity"),
    has_email: bool | None = Query(None, description="Filter contacts with email"),
    has_phone: bool | None = Query(None, description="Filter contacts with phone"),
) -> ContactListResponse:
    """
    List contacts with filtering and pagination.

    Args:
        db: Database session
        pagination: Pagination parameters
        user_id: Optional user ID filter
        search: Optional search term
        platform: Optional platform filter
        has_email: Optional email filter
        has_phone: Optional phone filter

    Returns:
        ContactListResponse: Paginated list of contacts
    """
    # Build query
    query = select(Contact)
    count_query = select(func.count(Contact.id))

    # Apply user filter if provided
    if user_id:
        query = query.where(Contact.user_id == user_id)
        count_query = count_query.where(Contact.user_id == user_id)

    # Apply filters
    filters = []

    if search:
        # Search in name or emails
        search_term = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Contact.canonical_name).like(search_term),
                func.lower(func.array_to_string(Contact.emails, " ")).like(search_term),
            )
        )

    if platform:
        # Filter by platform identity
        filters.append(Contact.platform_identities.has_key(platform))

    if has_email is not None:
        if has_email:
            filters.append(Contact.emails.isnot(None))
            filters.append(func.array_length(Contact.emails, 1) > 0)
        else:
            filters.append(
                or_(Contact.emails.is_(None), func.array_length(Contact.emails, 1) == 0)
            )

    if has_phone is not None:
        if has_phone:
            filters.append(Contact.phones.isnot(None))
            filters.append(func.array_length(Contact.phones, 1) > 0)
        else:
            filters.append(
                or_(Contact.phones.is_(None), func.array_length(Contact.phones, 1) == 0)
            )

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Contact.canonical_name)
    query = query.offset(pagination.skip).limit(pagination.limit)

    # Load relationships for counts
    query = query.options(
        selectinload(Contact.participants), selectinload(Contact.threads)
    )

    # Execute query
    result = await db.execute(query)
    contacts = result.scalars().all()

    # Convert to response models
    contact_responses = []
    for contact in contacts:
        contact_responses.append(
            ContactResponse(
                id=contact.id,
                canonical_name=contact.canonical_name,
                emails=contact.emails,
                phones=contact.phones,
                platform_identities=contact.platform_identities,
                contact_metadata=contact.contact_metadata,
                participant_count=(
                    len(contact.participants) if contact.participants else 0
                ),
                thread_count=len(contact.threads) if contact.threads else 0,
                created_at=contact.created_at,
                updated_at=contact.updated_at,
            )
        )

    return ContactListResponse(
        contacts=contact_responses,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/inbox",
    response_model=InboxResponse,
    summary="Get Inbox (Contacts with Messages)",
    description="Get ONLY contacts that have messages, sorted by last message time. For all contacts, use listContacts.",
)
async def get_inbox(
    db: AsyncSession = Depends(get_database_session),
    user_id: UUID | None = Query(None, description="User ID"),
    platform: str | None = Query(None, description="Filter by platform"),
    search: str | None = Query(None, description="Search contacts"),
    limit: int = Query(50, ge=1, le=1000, description="Max contacts"),
    skip: int = Query(0, ge=0, description="Offset"),
) -> InboxResponse:
    """
    Get inbox view: ONLY contacts with messages, sorted by recency.

    This is optimized for the messaging UI:
    - Only shows contacts that have at least one message
    - Sorted by last message timestamp (most recent first)
    - Includes message preview and platform info

    NOTE: This is different from listContacts which shows ALL contacts.
    """
    from sqlalchemy import text

    # Use raw SQL for performance
    # INNER JOIN to only get contacts that have messages
    sql = text("""
        WITH contact_last_messages AS (
            SELECT DISTINCT ON (c.id)
                c.id as contact_id,
                c.canonical_name,
                c.emails,
                c.phones,
                c.platform_identities,
                c.contact_metadata,
                m.id as message_id,
                m.content->>'text' as message_text,
                m.platform as message_platform,
                m.timestamp as message_timestamp,
                m.message_metadata as message_metadata
            FROM contacts c
            INNER JOIN messages m ON (
                -- Match by phone (if message has sender_phone)
                (m.message_metadata->>'sender_phone' IS NOT NULL AND 
                 m.message_metadata->>'sender_phone' = ANY(c.phones))
                OR
                -- Match by WhatsApp identity
                (m.platform = 'WHATSAPP' AND 
                 c.platform_identities->>'whatsapp' IS NOT NULL AND
                 c.platform_identities->>'whatsapp' = m.message_metadata->>'sender_phone')
            )
            WHERE (CAST(:user_id_str AS VARCHAR) IS NULL OR c.user_id = CAST(:user_id_str AS UUID))
            ORDER BY c.id, m.timestamp DESC NULLS LAST
        )
        SELECT 
            contact_id as id,
            canonical_name,
            emails,
            phones,
            platform_identities,
            contact_metadata,
            message_id,
            message_text,
            message_platform,
            message_timestamp,
            message_metadata
        FROM contact_last_messages
        ORDER BY message_timestamp DESC NULLS LAST, canonical_name
        LIMIT :limit OFFSET :skip
    """)

    # Execute query
    result = await db.execute(
        sql,
        {
            "user_id_str": str(user_id) if user_id else None,
            "limit": limit,
            "skip": skip,
        },
    )
    rows = result.fetchall()

    # Get total count of contacts WITH messages
    count_sql = text("""
        SELECT COUNT(DISTINCT c.id) FROM contacts c
        INNER JOIN messages m ON (
            (m.message_metadata->>'sender_phone' IS NOT NULL AND 
             m.message_metadata->>'sender_phone' = ANY(c.phones))
            OR
            (m.platform = 'WHATSAPP' AND 
             c.platform_identities->>'whatsapp' IS NOT NULL AND
             c.platform_identities->>'whatsapp' = m.message_metadata->>'sender_phone')
        )
        WHERE (CAST(:user_id_str AS VARCHAR) IS NULL OR c.user_id = CAST(:user_id_str AS UUID))
    """)
    count_result = await db.execute(
        count_sql, {"user_id_str": str(user_id) if user_id else None}
    )
    total = count_result.scalar() or 0

    # Build response
    inbox_contacts = []
    for row in rows:
        # Extract platforms from platform_identities
        platforms = (
            list(row.platform_identities.keys()) if row.platform_identities else []
        )

        # Extract avatar from metadata
        avatar_url = None
        if row.contact_metadata:
            avatar_url = row.contact_metadata.get("avatar_url")

        # Build last message info
        last_message_info = None
        if row.message_id:
            last_message_info = LastMessageInfo(
                message_id=row.message_id,
                content=row.message_text[:100] if row.message_text else None,
                platform=row.message_platform,
                timestamp=row.message_timestamp,
                sender_name=None,
                is_from_me=False,
            )

        inbox_contacts.append(
            InboxContact(
                id=row.id,
                canonical_name=row.canonical_name,
                emails=row.emails,
                phones=row.phones,
                platform_identities=row.platform_identities,
                avatar_url=avatar_url,
                last_message=last_message_info,
                unread_count=0,
                platforms=platforms,
            )
        )

    return InboxResponse(contacts=inbox_contacts, total=total, skip=skip, limit=limit)


@router.get(
    "/{contact_id}",
    response_model=ContactDetailResponse,
    summary="Get Contact Details",
    description="Get detailed information about a specific contact",
)
async def get_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ContactDetailResponse:
    """
    Get detailed contact information.

    Args:
        contact_id: Contact ID
        db: Database session

    Returns:
        ContactDetailResponse: Detailed contact information

    Raises:
        HTTPException: If contact not found
    """
    # Query with relationships
    query = select(Contact).where(Contact.id == contact_id)
    query = query.options(
        selectinload(Contact.participants), selectinload(Contact.threads)
    )

    result = await db.execute(query)
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact {contact_id} not found",
        )

    # Build participant list
    participants = []
    if contact.participants:
        for participant in contact.participants:
            participants.append(
                {
                    "id": str(participant.id),
                    "platform": participant.platform,
                    "platform_user_id": participant.platform_user_id,
                    "name": participant.name,
                    "email": participant.email,
                    "phone": participant.phone,
                    "metadata": participant.participant_metadata,
                }
            )

    return ContactDetailResponse(
        id=contact.id,
        canonical_name=contact.canonical_name,
        emails=contact.emails,
        phones=contact.phones,
        platform_identities=contact.platform_identities,
        contact_metadata=contact.contact_metadata,
        participant_count=len(participants),
        thread_count=len(contact.threads) if contact.threads else 0,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        participants=participants,
    )


@router.get(
    "/{contact_id}/threads",
    response_model=ContactThreadsResponse,
    summary="Get Contact Threads",
    description="Get all threads associated with a contact",
)
async def get_contact_threads(
    contact_id: UUID,
    db: AsyncSession = Depends(get_database_session),
    platform: str | None = Query(None, description="Filter by platform"),
) -> ContactThreadsResponse:
    """
    Get all threads for a contact.

    Args:
        contact_id: Contact ID
        db: Database session
        platform: Optional platform filter

    Returns:
        ContactThreadsResponse: Contact threads

    Raises:
        HTTPException: If contact not found
    """
    # Check if contact exists
    contact_query = select(Contact).where(Contact.id == contact_id)
    contact_result = await db.execute(contact_query)
    contact = contact_result.scalar_one_or_none()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact {contact_id} not found",
        )

    # Query threads
    query = select(Thread).where(Thread.contact_id == contact_id)

    if platform:
        query = query.where(Thread.platform == platform)

    query = query.order_by(Thread.last_message_at.desc().nullslast())

    result = await db.execute(query)
    threads = result.scalars().all()

    # Convert to response models
    thread_summaries = []
    for thread in threads:
        thread_summaries.append(
            ThreadSummary(
                id=thread.id,
                platform=thread.platform,
                platform_thread_id=thread.platform_thread_id,
                title=thread.title,
                message_count=thread.message_count,
                first_message_at=thread.first_message_at,
                last_message_at=thread.last_message_at,
            )
        )

    return ContactThreadsResponse(
        contact_id=contact_id,
        contact_name=contact.canonical_name,
        threads=thread_summaries,
        total=len(thread_summaries),
    )


@router.post(
    "/merge",
    response_model=MergeContactsResponse,
    summary="Merge Contacts",
    description="Manually merge multiple contacts into one",
)
async def merge_contacts(
    request: MergeContactsRequest,
    db: AsyncSession = Depends(get_database_session),
) -> MergeContactsResponse:
    """
    Merge multiple contacts into a single contact.

    This operation:
    1. Validates all contacts exist
    2. Merges data according to strategy
    3. Updates all participants and threads
    4. Deletes source contacts
    5. Emits CONTACT_MERGED event

    Args:
        request: Merge request
        db: Database session

    Returns:
        MergeContactsResponse: Merge result

    Raises:
        HTTPException: If validation fails
    """
    if not request.source_contact_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one source contact ID is required",
        )

    if request.target_contact_id in request.source_contact_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target contact cannot be in source contacts list",
        )

    try:
        # Load all contacts
        all_contact_ids = [request.target_contact_id] + request.source_contact_ids
        query = select(Contact).where(Contact.id.in_(all_contact_ids))
        query = query.options(
            selectinload(Contact.participants), selectinload(Contact.threads)
        )

        result = await db.execute(query)
        contacts = {c.id: c for c in result.scalars().all()}

        # Validate all contacts exist
        if len(contacts) != len(all_contact_ids):
            missing = set(all_contact_ids) - set(contacts.keys())
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contacts not found: {missing}",
            )

        target_contact = contacts[request.target_contact_id]
        source_contacts = [contacts[cid] for cid in request.source_contact_ids]

        # Merge data based on strategy
        merged_emails = set(target_contact.emails or [])
        merged_phones = set(target_contact.phones or [])
        merged_identities = dict(target_contact.platform_identities or {})
        merged_metadata = dict(target_contact.contact_metadata or {})

        for source in source_contacts:
            # Merge emails
            if source.emails:
                merged_emails.update(source.emails)

            # Merge phones
            if source.phones:
                merged_phones.update(source.phones)

            # Merge platform identities
            if source.platform_identities:
                for platform, identity in source.platform_identities.items():
                    if platform not in merged_identities:
                        merged_identities[platform] = identity

            # Merge metadata (prefer target for conflicts)
            if source.contact_metadata:
                for key, value in source.contact_metadata.items():
                    if key not in merged_metadata:
                        merged_metadata[key] = value

            # Update participants to point to target contact
            if source.participants:
                for participant in source.participants:
                    participant.contact_id = target_contact.id

            # Update threads to point to target contact
            if source.threads:
                for thread in source.threads:
                    thread.contact_id = target_contact.id

        # Update target contact
        target_contact.emails = list(merged_emails) if merged_emails else None
        target_contact.phones = list(merged_phones) if merged_phones else None
        target_contact.platform_identities = (
            merged_identities if merged_identities else None
        )
        target_contact.contact_metadata = merged_metadata if merged_metadata else None
        target_contact.updated_at = datetime.utcnow()

        # Delete source contacts
        for source in source_contacts:
            await db.delete(source)

        await db.commit()
        await db.refresh(target_contact)

        # Emit event
        event_bus = get_event_bus()
        event = ContactEvent(
            event_id=str(uuid4()),
            event_type=EventType.CONTACT_MERGED,
            source="contacts_api",
            payload={
                "contact_id": str(target_contact.id),
                "merged_contact_ids": [str(cid) for cid in request.source_contact_ids],
                "merge_strategy": request.merge_strategy,
                "merged_count": len(request.source_contact_ids),
            },
        )

        await event_bus.publish(event)

        logger.info(
            f"Merged {len(request.source_contact_ids)} contacts into {target_contact.id}"
        )

        # Reload to get updated counts
        query = select(Contact).where(Contact.id == target_contact.id)
        query = query.options(
            selectinload(Contact.participants), selectinload(Contact.threads)
        )
        result = await db.execute(query)
        target_contact = result.scalar_one()

        return MergeContactsResponse(
            merged_contact=ContactResponse(
                id=target_contact.id,
                canonical_name=target_contact.canonical_name,
                emails=target_contact.emails,
                phones=target_contact.phones,
                platform_identities=target_contact.platform_identities,
                contact_metadata=target_contact.contact_metadata,
                participant_count=(
                    len(target_contact.participants)
                    if target_contact.participants
                    else 0
                ),
                thread_count=(
                    len(target_contact.threads) if target_contact.threads else 0
                ),
                created_at=target_contact.created_at,
                updated_at=target_contact.updated_at,
            ),
            merged_count=len(request.source_contact_ids),
            message=f"Successfully merged {len(request.source_contact_ids)} contacts",
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to merge contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge contacts: {str(e)}",
        )


@router.post(
    "/split",
    response_model=SplitContactResponse,
    summary="Split Contact",
    description="Split a contact by moving some platform identities to a new contact",
)
async def split_contact(
    request: SplitContactRequest,
    db: AsyncSession = Depends(get_database_session),
) -> SplitContactResponse:
    """
    Split a contact by moving platform identities to a new contact.

    This operation:
    1. Validates contact exists
    2. Creates new contact with specified identities
    3. Updates participants to point to new contact
    4. Updates threads if all participants moved
    5. Removes identities from original contact

    Args:
        request: Split request
        db: Database session

    Returns:
        SplitContactResponse: Split result

    Raises:
        HTTPException: If validation fails
    """
    if not request.platform_identities_to_split:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one platform identity is required to split",
        )

    try:
        # Load original contact
        query = select(Contact).where(Contact.id == request.contact_id)
        query = query.options(
            selectinload(Contact.participants), selectinload(Contact.threads)
        )

        result = await db.execute(query)
        original_contact = result.scalar_one_or_none()

        if not original_contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact {request.contact_id} not found",
            )

        # Validate platform identities exist
        if not original_contact.platform_identities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contact has no platform identities to split",
            )

        for platform in request.platform_identities_to_split:
            if platform not in original_contact.platform_identities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Platform identity '{platform}' not found in contact",
                )

        # Create new contact
        new_identities = {
            platform: original_contact.platform_identities[platform]
            for platform in request.platform_identities_to_split
        }

        new_contact = Contact(
            canonical_name=request.new_contact_name, platform_identities=new_identities
        )

        db.add(new_contact)
        await db.flush()  # Get new contact ID

        # Move participants
        if original_contact.participants:
            for participant in original_contact.participants:
                if participant.platform in request.platform_identities_to_split:
                    participant.contact_id = new_contact.id

        # Update threads if needed
        # (Only move thread if all participants are moving)
        if original_contact.threads:
            for thread in original_contact.threads:
                if thread.platform in request.platform_identities_to_split:
                    thread.contact_id = new_contact.id

        # Remove identities from original contact
        remaining_identities = {
            platform: identity
            for platform, identity in original_contact.platform_identities.items()
            if platform not in request.platform_identities_to_split
        }

        original_contact.platform_identities = (
            remaining_identities if remaining_identities else None
        )
        original_contact.updated_at = datetime.utcnow()

        await db.commit()

        # Reload contacts with updated relationships
        query = select(Contact).where(
            Contact.id.in_([original_contact.id, new_contact.id])
        )
        query = query.options(
            selectinload(Contact.participants), selectinload(Contact.threads)
        )
        result = await db.execute(query)
        contacts = {c.id: c for c in result.scalars().all()}

        original_contact = contacts[original_contact.id]
        new_contact = contacts[new_contact.id]

        logger.info(
            f"Split contact {original_contact.id}, created new contact {new_contact.id}"
        )

        return SplitContactResponse(
            original_contact=ContactResponse(
                id=original_contact.id,
                canonical_name=original_contact.canonical_name,
                emails=original_contact.emails,
                phones=original_contact.phones,
                platform_identities=original_contact.platform_identities,
                contact_metadata=original_contact.contact_metadata,
                participant_count=(
                    len(original_contact.participants)
                    if original_contact.participants
                    else 0
                ),
                thread_count=(
                    len(original_contact.threads) if original_contact.threads else 0
                ),
                created_at=original_contact.created_at,
                updated_at=original_contact.updated_at,
            ),
            new_contact=ContactResponse(
                id=new_contact.id,
                canonical_name=new_contact.canonical_name,
                emails=new_contact.emails,
                phones=new_contact.phones,
                platform_identities=new_contact.platform_identities,
                contact_metadata=new_contact.contact_metadata,
                participant_count=(
                    len(new_contact.participants) if new_contact.participants else 0
                ),
                thread_count=len(new_contact.threads) if new_contact.threads else 0,
                created_at=new_contact.created_at,
                updated_at=new_contact.updated_at,
            ),
            message=f"Successfully split contact into 2 contacts",
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to split contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to split contact: {str(e)}",
        )


# =============================================================================
# Contact Sync Endpoints
# =============================================================================


class DeviceContact(BaseModel):
    """Device contact for sync."""

    name: str = Field(..., min_length=1, max_length=255)
    emails: list[str] | None = None
    phones: list[str] | None = None


class ContactSyncRequest(BaseModel):
    """Request to sync device contacts."""

    contacts: list[DeviceContact] = Field(..., description="Contacts from device")


class ContactSyncResponse(BaseModel):
    """Sync result."""

    created: int = Field(description="New contacts created")
    updated: int = Field(description="Existing contacts updated")
    duplicates_skipped: int = Field(description="Duplicates found and skipped")
    total_processed: int = Field(description="Total contacts processed")


def normalize_phone(phone: str) -> str:
    """Normalize phone number for comparison."""
    # Keep only digits
    digits = "".join(filter(str.isdigit, phone))
    # Return last 10 digits (handles country codes)
    return digits[-10:] if len(digits) >= 10 else digits


async def find_duplicate_contact(
    db: AsyncSession, user_id: UUID, emails: list[str] | None, phones: list[str] | None
) -> Contact | None:
    """Find existing contact by matching email or phone."""

    # Fetch user's contacts
    result = await db.execute(select(Contact).where(Contact.user_id == user_id))
    contacts = result.scalars().all()

    # Check by email first (most reliable)
    if emails:
        email_set = {e.lower() for e in emails}
        for contact in contacts:
            if contact.emails:
                contact_emails = {e.lower() for e in contact.emails}
                if email_set & contact_emails:  # Intersection
                    return contact

    # Then by phone (normalized)
    if phones:
        phone_set = {normalize_phone(p) for p in phones if len(normalize_phone(p)) >= 7}
        for contact in contacts:
            if contact.phones:
                contact_phones = {
                    normalize_phone(p)
                    for p in contact.phones
                    if len(normalize_phone(p)) >= 7
                }
                if phone_set & contact_phones:
                    return contact

    return None


@router.post(
    "/sync",
    response_model=ContactSyncResponse,
    summary="Sync Device Contacts",
    description="Import and sync contacts from device, handling duplicates",
)
async def sync_contacts(
    user_id: UUID = Query(..., description="User ID"),
    request: ContactSyncRequest = ...,
    db: AsyncSession = Depends(get_database_session),
) -> ContactSyncResponse:
    """
    Sync contacts from device.

    Handles deduplication by matching:
    - Email addresses (case-insensitive)
    - Phone numbers (normalized, last 10 digits)

    For duplicates, merges new info into existing contact.
    """
    created = 0
    updated = 0
    duplicates_skipped = 0

    try:
        for device_contact in request.contacts:
            # Skip contacts without identifiers
            if not device_contact.emails and not device_contact.phones:
                continue

            # Check for existing duplicate
            existing = await find_duplicate_contact(
                db, user_id, device_contact.emails, device_contact.phones
            )

            if existing:
                # Check if we need to update
                changed = False

                # Merge emails
                if device_contact.emails:
                    current_emails = set(existing.emails or [])
                    new_emails = {e.lower() for e in device_contact.emails}
                    if new_emails - {e.lower() for e in current_emails}:
                        existing.emails = list(
                            current_emails | set(device_contact.emails)
                        )
                        changed = True

                # Merge phones
                if device_contact.phones:
                    current_phones = set(existing.phones or [])
                    current_normalized = {normalize_phone(p) for p in current_phones}
                    new_normalized = {normalize_phone(p) for p in device_contact.phones}
                    if new_normalized - current_normalized:
                        existing.phones = list(
                            current_phones | set(device_contact.phones)
                        )
                        changed = True

                if changed:
                    updated += 1
                else:
                    duplicates_skipped += 1
            else:
                # Create new contact
                contact = Contact(
                    id=uuid4(),
                    user_id=user_id,
                    canonical_name=device_contact.name,
                    emails=device_contact.emails,
                    phones=device_contact.phones,
                    platform_identities={},
                    contact_metadata={
                        "source": "device_sync",
                        "synced_at": datetime.utcnow().isoformat(),
                    },
                )
                db.add(contact)
                created += 1

        await db.commit()

        logger.info(
            f"Contact sync for user {user_id}: created={created}, updated={updated}, dupes={duplicates_skipped}"
        )

        return ContactSyncResponse(
            created=created,
            updated=updated,
            duplicates_skipped=duplicates_skipped,
            total_processed=len(request.contacts),
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to sync contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync contacts: {str(e)}",
        )


# =============================================================================
# Export router
# =============================================================================

__all__ = ["router"]
