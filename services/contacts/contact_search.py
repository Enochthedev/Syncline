"""Contact search service with fuzzy matching and intelligent suggestions."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, text
from sqlalchemy.orm import selectinload
import re

from db.models.unified_contact import UnifiedContact, ContactIdentity

logger = logging.getLogger(__name__)


class ContactSearchService:
    """Service for intelligent contact search with fuzzy matching."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

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
        if not query.strip():
            return await self._get_default_contacts(tenant_id, user_id, limit, offset)

        # Normalize query
        normalized_query = self._normalize_query(query)

        # Build search conditions
        search_conditions = self._build_search_conditions(normalized_query)

        # Base query
        base_query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_archived == False
            )
        ).options(
            selectinload(UnifiedContact.identities)
        )

        # Apply search conditions
        if search_conditions:
            base_query = base_query.where(or_(*search_conditions))

        # Apply filters
        if filters:
            base_query = self._apply_filters(base_query, filters)

        # Order by relevance (favorites first, then by last interaction)
        base_query = base_query.order_by(
            desc(UnifiedContact.is_favorite),
            desc(UnifiedContact.last_interaction),
            UnifiedContact.primary_name
        )

        # Apply pagination
        base_query = base_query.offset(offset).limit(limit)

        result = await self.db.execute(base_query)
        contacts = result.scalars().all()

        # If we have identity matches, also search by identity
        if not contacts or len(contacts) < limit:
            identity_contacts = await self._search_by_identity(
                normalized_query, tenant_id, user_id, limit - len(contacts)
            )

            # Merge results, avoiding duplicates
            existing_ids = {c.id for c in contacts}
            for contact in identity_contacts:
                if contact.id not in existing_ids:
                    contacts.append(contact)

        return contacts

    def _normalize_query(self, query: str) -> str:
        """Normalize search query for better matching."""
        # Remove extra whitespace and convert to lowercase
        normalized = re.sub(r'\s+', ' ', query.strip().lower())

        # Remove common punctuation
        normalized = re.sub(r'[^\w\s@.-]', '', normalized)

        return normalized

    def _build_search_conditions(self, query: str) -> List:
        """Build search conditions for the query."""
        conditions = []

        # Split query into terms
        terms = query.split()

        for term in terms:
            if len(term) < 2:  # Skip very short terms
                continue

            # Search in primary name (case-insensitive)
            conditions.append(
                UnifiedContact.primary_name.ilike(f"%{term}%")
            )

            # Search in display name
            conditions.append(
                UnifiedContact.display_name.ilike(f"%{term}%")
            )

            # Search in primary email
            if '@' in term or '.' in term:  # Looks like email
                conditions.append(
                    UnifiedContact.primary_email.ilike(f"%{term}%")
                )

            # Search in phone (remove formatting)
            if term.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
                phone_term = re.sub(r'[^\d]', '', term)
                if len(phone_term) >= 3:
                    conditions.append(
                        func.regexp_replace(UnifiedContact.primary_phone, r'[^\d]', '', 'g').ilike(
                            f"%{phone_term}%")
                    )

        # Full name search (all terms together)
        if len(terms) > 1:
            full_query = ' '.join(terms)
            conditions.extend([
                UnifiedContact.primary_name.ilike(f"%{full_query}%"),
                UnifiedContact.display_name.ilike(f"%{full_query}%")
            ])

        return conditions

    async def _search_by_identity(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[UnifiedContact]:
        """Search contacts by their platform identities."""
        terms = query.split()
        identity_conditions = []

        for term in terms:
            if len(term) < 2:
                continue

            # Search in identity display names
            identity_conditions.append(
                ContactIdentity.display_name.ilike(f"%{term}%")
            )

            # Search in platform handles
            identity_conditions.append(
                ContactIdentity.platform_handle.ilike(f"%{term}%")
            )

            # Search in identity emails
            if '@' in term or '.' in term:
                identity_conditions.append(
                    ContactIdentity.email.ilike(f"%{term}%")
                )

            # Search in identity phones
            if term.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
                phone_term = re.sub(r'[^\d]', '', term)
                if len(phone_term) >= 3:
                    identity_conditions.append(
                        func.regexp_replace(ContactIdentity.phone, r'[^\d]', '', 'g').ilike(
                            f"%{phone_term}%")
                    )

        if not identity_conditions:
            return []

        query = select(UnifiedContact).join(ContactIdentity).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_archived == False,
                or_(*identity_conditions)
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).distinct().limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply search filters to the query."""
        if 'platforms' in filters and filters['platforms']:
            # Filter by platforms through identities
            query = query.join(ContactIdentity).where(
                ContactIdentity.platform.in_(filters['platforms'])
            )

        if 'is_favorite' in filters:
            query = query.where(UnifiedContact.is_favorite ==
                                filters['is_favorite'])

        if 'relationship_strength_min' in filters:
            query = query.where(
                UnifiedContact.relationship_strength >= filters['relationship_strength_min']
            )

        if 'communication_frequency' in filters and filters['communication_frequency']:
            query = query.where(
                UnifiedContact.communication_frequency.in_(
                    filters['communication_frequency'])
            )

        if 'tags' in filters and filters['tags']:
            # Search for contacts with any of the specified tags
            for tag in filters['tags']:
                query = query.where(
                    func.json_array_length(
                        func.json_extract_path(
                            UnifiedContact.tags, text(f"'{tag}'"))
                    ) > 0
                )

        if 'last_interaction_days' in filters:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow(
            ) - timedelta(days=filters['last_interaction_days'])
            query = query.where(UnifiedContact.last_interaction >= cutoff_date)

        return query

    async def _get_default_contacts(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int,
        offset: int
    ) -> List[UnifiedContact]:
        """Get default contacts when no search query is provided."""
        # Return favorites first, then recent contacts
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_archived == False
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(
            desc(UnifiedContact.is_favorite),
            desc(UnifiedContact.last_interaction),
            UnifiedContact.primary_name
        ).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_search_suggestions(
        self,
        partial_query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get search suggestions based on partial query."""
        if len(partial_query) < 2:
            return []

        normalized_query = self._normalize_query(partial_query)
        suggestions = []

        # Name suggestions
        name_query = select(
            UnifiedContact.primary_name,
            UnifiedContact.display_name,
            UnifiedContact.id
        ).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_archived == False,
                or_(
                    UnifiedContact.primary_name.ilike(f"{normalized_query}%"),
                    UnifiedContact.display_name.ilike(f"{normalized_query}%")
                )
            )
        ).limit(limit)

        result = await self.db.execute(name_query)
        for row in result:
            suggestions.append({
                'type': 'name',
                'text': row.primary_name or row.display_name,
                'contact_id': str(row.id),
                'match_type': 'name'
            })

        # Email suggestions
        if '@' in normalized_query or '.' in normalized_query:
            email_query = select(
                UnifiedContact.primary_email,
                UnifiedContact.primary_name,
                UnifiedContact.id
            ).where(
                and_(
                    UnifiedContact.tenant_id == tenant_id,
                    UnifiedContact.user_id == user_id,
                    UnifiedContact.is_archived == False,
                    UnifiedContact.primary_email.ilike(f"{normalized_query}%")
                )
            ).limit(limit - len(suggestions))

            result = await self.db.execute(email_query)
            for row in result:
                if row.primary_email:
                    suggestions.append({
                        'type': 'email',
                        'text': row.primary_email,
                        'contact_id': str(row.id),
                        'contact_name': row.primary_name,
                        'match_type': 'email'
                    })

        # Platform handle suggestions
        if len(suggestions) < limit:
            handle_query = select(
                ContactIdentity.platform_handle,
                ContactIdentity.platform,
                UnifiedContact.primary_name,
                UnifiedContact.id
            ).join(UnifiedContact).where(
                and_(
                    UnifiedContact.tenant_id == tenant_id,
                    UnifiedContact.user_id == user_id,
                    UnifiedContact.is_archived == False,
                    ContactIdentity.platform_handle.ilike(
                        f"{normalized_query}%")
                )
            ).limit(limit - len(suggestions))

            result = await self.db.execute(handle_query)
            for row in result:
                if row.platform_handle:
                    suggestions.append({
                        'type': 'handle',
                        'text': f"@{row.platform_handle}",
                        'platform': row.platform,
                        'contact_id': str(row.id),
                        'contact_name': row.primary_name,
                        'match_type': 'handle'
                    })

        return suggestions[:limit]

    async def find_similar_contacts(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 10
    ) -> List[UnifiedContact]:
        """Find contacts similar to the given contact."""
        # Get the reference contact
        ref_contact = await self.db.execute(
            select(UnifiedContact).where(
                and_(
                    UnifiedContact.id == contact_id,
                    UnifiedContact.tenant_id == tenant_id,
                    UnifiedContact.user_id == user_id
                )
            ).options(selectinload(UnifiedContact.identities))
        )
        reference = ref_contact.scalar_one_or_none()

        if not reference:
            return []

        # Find similar contacts based on:
        # 1. Same platforms
        # 2. Similar names
        # 3. Similar communication patterns

        similar_conditions = []

        # Same platforms
        if reference.platforms:
            for platform in reference.platforms:
                similar_conditions.append(
                    func.json_array_length(
                        func.json_extract_path(
                            UnifiedContact.platforms, text(f"'{platform}'"))
                    ) > 0
                )

        # Similar relationship strength
        if reference.relationship_strength > 0:
            strength_range = 0.2  # ±0.2 range
            similar_conditions.extend([
                UnifiedContact.relationship_strength.between(
                    max(0, reference.relationship_strength - strength_range),
                    min(1, reference.relationship_strength + strength_range)
                )
            ])

        # Similar communication frequency
        if reference.communication_frequency:
            similar_conditions.append(
                UnifiedContact.communication_frequency == reference.communication_frequency
            )

        if not similar_conditions:
            return []

        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.id != contact_id,  # Exclude the reference contact
                UnifiedContact.is_archived == False,
                or_(*similar_conditions)
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(
            desc(UnifiedContact.relationship_strength),
            desc(UnifiedContact.last_interaction)
        ).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()
