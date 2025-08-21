"""ContactManager service for unified contact management."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from db.models.unified_contact import (
    UnifiedContact, ContactIdentity, ContactInsight,
    ContactPreference, ContactRelationship
)
from db.models.participant import Participant
from db.models.message import Message
from db.models.thread import Thread
from .contact_search import ContactSearchService
from .contact_insights import ContactInsightsService
from .contact_merger import ContactMerger

logger = logging.getLogger(__name__)


class ContactManager:
    """Unified contact management service with search, insights, and merging capabilities."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.search_service = ContactSearchService(db_session)
        self.insights_service = ContactInsightsService(db_session)
        self.merger = ContactMerger(db_session)

    # Contact Search and Retrieval

    async def search_contacts(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[UnifiedContact]:
        """Search contacts with fuzzy matching and filters."""
        return await self.search_service.search_contacts(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            filters=filters or {}
        )

    async def get_contact(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        include_insights: bool = True
    ) -> Optional[UnifiedContact]:
        """Get a unified contact by ID with optional insights."""
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        ).options(
            selectinload(UnifiedContact.identities),
            selectinload(UnifiedContact.preferences)
        )

        if include_insights:
            query = query.options(selectinload(UnifiedContact.insights))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_unified_contact(
        self,
        identifiers: List[Dict[str, str]],
        tenant_id: UUID,
        user_id: UUID
    ) -> Optional[UnifiedContact]:
        """Get unified contact by platform identifiers."""
        # Build query to find contacts with matching identities
        identity_conditions = []
        for identifier in identifiers:
            if 'platform' in identifier and 'platform_user_id' in identifier:
                identity_conditions.append(
                    and_(
                        ContactIdentity.platform == identifier['platform'],
                        ContactIdentity.platform_user_id == identifier['platform_user_id']
                    )
                )
            elif 'email' in identifier:
                identity_conditions.append(
                    ContactIdentity.email == identifier['email'])
            elif 'phone' in identifier:
                identity_conditions.append(
                    ContactIdentity.phone == identifier['phone'])

        if not identity_conditions:
            return None

        query = select(UnifiedContact).join(ContactIdentity).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                or_(*identity_conditions)
            )
        ).options(
            selectinload(UnifiedContact.identities),
            selectinload(UnifiedContact.insights),
            selectinload(UnifiedContact.preferences)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # Contact-based Message Search

    async def search_messages_by_contact(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """Search messages related to a specific contact."""
        # Get contact's platform identities
        contact = await self.get_contact(contact_id, tenant_id, user_id, include_insights=False)
        if not contact:
            return []

        # Get platform user IDs for the contact
        platform_user_ids = [
            (identity.platform, identity.platform_user_id)
            for identity in contact.identities
        ]

        if not platform_user_ids:
            return []

        # Build query for messages from/to this contact
        participant_conditions = []
        for platform, platform_user_id in platform_user_ids:
            participant_conditions.append(
                and_(
                    Participant.platform == platform,
                    Participant.platform_user_id == platform_user_id
                )
            )

        # Base query for messages
        message_query = select(Message).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        )

        # Add text search if provided
        if query:
            message_query = message_query.where(
                Message.content.ilike(f"%{query}%")
            )

        # Apply filters
        if filters:
            if 'start_date' in filters:
                message_query = message_query.where(
                    Message.timestamp >= filters['start_date'])
            if 'end_date' in filters:
                message_query = message_query.where(
                    Message.timestamp <= filters['end_date'])
            if 'platforms' in filters:
                message_query = message_query.where(
                    Message.platform.in_(filters['platforms']))

        # Apply pagination and ordering
        message_query = message_query.order_by(
            desc(Message.timestamp)).offset(offset).limit(limit)

        result = await self.db.execute(message_query)
        return result.scalars().all()

    async def get_conversation_history(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        platform_filter: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Thread]:
        """Get conversation threads with a specific contact."""
        # Get contact's platform identities
        contact = await self.get_contact(contact_id, tenant_id, user_id, include_insights=False)
        if not contact:
            return []

        # Get platform user IDs for the contact
        platform_user_ids = [
            (identity.platform, identity.platform_user_id)
            for identity in contact.identities
            if not platform_filter or identity.platform in platform_filter
        ]

        if not platform_user_ids:
            return []

        # Build query for threads involving this contact
        participant_conditions = []
        for platform, platform_user_id in platform_user_ids:
            participant_conditions.append(
                and_(
                    Participant.platform == platform,
                    Participant.platform_user_id == platform_user_id
                )
            )

        # Query threads with messages from this contact
        thread_query = select(Thread).join(Message).join(Participant).where(
            and_(
                Thread.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        ).distinct().order_by(desc(Thread.last_message_at)).limit(limit)

        result = await self.db.execute(thread_query)
        return result.scalars().all()

    async def get_shared_files(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        file_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get files shared with a specific contact."""
        # This would integrate with the file attachment system
        # For now, return a placeholder structure
        return []

    # Contact Insights and Analysis

    async def get_contact_insights(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[ContactInsight]:
        """Get AI-generated insights for a contact."""
        return await self.insights_service.get_contact_insights(
            contact_id, tenant_id, user_id
        )

    async def get_communication_patterns(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get communication patterns for a contact."""
        return await self.insights_service.analyze_communication_patterns(
            contact_id, tenant_id, user_id
        )

    async def get_relationship_strength(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get relationship strength metrics for a contact."""
        return await self.insights_service.calculate_relationship_strength(
            contact_id, tenant_id, user_id
        )

    # Contact Management

    async def create_contact(
        self,
        tenant_id: UUID,
        user_id: UUID,
        primary_name: str,
        identities: List[Dict[str, Any]],
        **kwargs
    ) -> UnifiedContact:
        """Create a new unified contact."""
        # Create the unified contact
        contact = UnifiedContact(
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name=primary_name,
            display_name=kwargs.get('display_name', primary_name),
            profile_photo_url=kwargs.get('profile_photo_url'),
            primary_email=kwargs.get('primary_email'),
            primary_phone=kwargs.get('primary_phone'),
            custom_notes=kwargs.get('custom_notes'),
            tags=kwargs.get('tags', []),
            is_favorite=kwargs.get('is_favorite', False),
            extra_metadata=kwargs.get('extra_metadata', {})
        )

        self.db.add(contact)
        await self.db.flush()  # Get the contact ID

        # Create contact identities
        for identity_data in identities:
            identity = ContactIdentity(
                unified_contact_id=contact.id,
                platform=identity_data['platform'],
                platform_user_id=identity_data['platform_user_id'],
                platform_handle=identity_data.get('platform_handle'),
                display_name=identity_data.get('display_name'),
                email=identity_data.get('email'),
                phone=identity_data.get('phone'),
                profile_url=identity_data.get('profile_url'),
                avatar_url=identity_data.get('avatar_url'),
                is_verified=identity_data.get('is_verified', False),
                platform_metadata=identity_data.get('platform_metadata', {})
            )
            self.db.add(identity)

        # Create default preferences
        preferences = ContactPreference(
            unified_contact_id=contact.id,
            notification_enabled=kwargs.get('notification_enabled', True),
            preferred_communication_platform=kwargs.get(
                'preferred_communication_platform'),
            reminder_frequency=kwargs.get('reminder_frequency', 'normal')
        )
        self.db.add(preferences)

        await self.db.commit()

        # Refresh to get relationships
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[UnifiedContact]:
        """Update a unified contact."""
        contact = await self.get_contact(contact_id, tenant_id, user_id, include_insights=False)
        if not contact:
            return None

        # Update basic fields
        for field, value in updates.items():
            if hasattr(contact, field) and field not in ['id', 'tenant_id', 'user_id', 'created_at']:
                setattr(contact, field, value)

        contact.updated_at = datetime.utcnow()
        await self.db.commit()

        return contact

    async def merge_contacts(
        self,
        primary_id: UUID,
        duplicate_ids: List[UUID],
        tenant_id: UUID,
        user_id: UUID
    ) -> UnifiedContact:
        """Merge duplicate contacts into a primary contact."""
        return await self.merger.merge_contacts(
            primary_id, duplicate_ids, tenant_id, user_id
        )

    async def update_contact_preferences(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update contact preferences."""
        # Get existing preferences
        query = select(ContactPreference).join(UnifiedContact).where(
            and_(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        )

        result = await self.db.execute(query)
        contact_prefs = result.scalar_one_or_none()

        if not contact_prefs:
            # Create new preferences
            contact_prefs = ContactPreference(
                unified_contact_id=contact_id,
                **preferences
            )
            self.db.add(contact_prefs)
        else:
            # Update existing preferences
            for field, value in preferences.items():
                if hasattr(contact_prefs, field):
                    setattr(contact_prefs, field, value)
            contact_prefs.updated_at = datetime.utcnow()

        await self.db.commit()
        return True

    async def add_contact_note(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        note: str
    ) -> bool:
        """Add a note to a contact."""
        contact = await self.get_contact(contact_id, tenant_id, user_id, include_insights=False)
        if not contact:
            return False

        # Append to existing notes or create new
        if contact.custom_notes:
            contact.custom_notes += f"\n\n{datetime.utcnow().isoformat()}: {note}"
        else:
            contact.custom_notes = f"{datetime.utcnow().isoformat()}: {note}"

        contact.updated_at = datetime.utcnow()
        await self.db.commit()

        return True

    # Relationship Analysis

    async def find_mutual_contacts(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[UnifiedContact]:
        """Find mutual contacts for a given contact."""
        # This would analyze shared threads and group conversations
        # For now, return empty list as placeholder
        return []

    async def analyze_contact_network(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Analyze the contact's network and relationships."""
        return await self.insights_service.analyze_contact_network(
            contact_id, tenant_id, user_id
        )

    # Bulk Operations

    async def get_contacts_by_platform(
        self,
        platform: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 100
    ) -> List[UnifiedContact]:
        """Get all contacts from a specific platform."""
        query = select(UnifiedContact).join(ContactIdentity).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                ContactIdentity.platform == platform
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_favorite_contacts(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 50
    ) -> List[UnifiedContact]:
        """Get user's favorite contacts."""
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_favorite == True
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(desc(UnifiedContact.last_interaction)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_recent_contacts(
        self,
        tenant_id: UUID,
        user_id: UUID,
        days: int = 30,
        limit: int = 50
    ) -> List[UnifiedContact]:
        """Get recently interacted contacts."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.last_interaction >= cutoff_date
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(desc(UnifiedContact.last_interaction)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    # Statistics and Analytics

    async def get_contact_statistics(
        self,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get contact statistics for the user."""
        # Total contacts
        total_query = select(func.count(UnifiedContact.id)).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        )
        total_result = await self.db.execute(total_query)
        total_contacts = total_result.scalar()

        # Contacts by platform
        platform_query = select(
            ContactIdentity.platform,
            func.count(func.distinct(ContactIdentity.unified_contact_id))
        ).join(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        ).group_by(ContactIdentity.platform)

        platform_result = await self.db.execute(platform_query)
        platform_counts = dict(platform_result.fetchall())

        # Recent activity
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        recent_query = select(func.count(UnifiedContact.id)).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.last_interaction >= recent_cutoff
            )
        )
        recent_result = await self.db.execute(recent_query)
        recent_contacts = recent_result.scalar()

        return {
            "total_contacts": total_contacts,
            "platform_distribution": platform_counts,
            "recent_contacts": recent_contacts,
            "favorite_contacts": len(await self.get_favorite_contacts(tenant_id, user_id, limit=1000))
        }
