"""
Intelligent contact-based auto-search functionality.

This service provides real-time contact search with fuzzy matching,
natural language query processing, and intelligent suggestions for
contact-based searches across all platforms.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, text
from sqlalchemy.orm import selectinload

from db.models.unified_contact import UnifiedContact, ContactIdentity
from db.models.message import Message
from db.models.thread import Thread
from db.models.participant import Participant
from db.models.attachment import Attachment
from services.ai.search.query_processor import QueryProcessor
from services.ai.search.types import SearchQuery, QueryIntent, SearchFilters

logger = logging.getLogger(__name__)


class ContactAutoSearchService:
    """
    Intelligent contact-based auto-search service.

    Provides real-time contact search with fuzzy matching, natural language
    processing, and intelligent suggestions for contact-based queries.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.query_processor = QueryProcessor()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the auto-search service."""
        try:
            await self.query_processor.initialize()
            self._initialized = True
            logger.info("ContactAutoSearchService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ContactAutoSearchService: {e}")
            raise

    async def search_contacts_realtime(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 10,
        include_suggestions: bool = True
    ) -> Dict[str, Any]:
        """
        Perform real-time contact search with fuzzy matching.

        Args:
            query: Search query text
            tenant_id: Tenant ID for multi-tenant isolation
            user_id: User ID for user-specific contacts
            limit: Maximum number of results
            include_suggestions: Whether to include search suggestions

        Returns:
            Dictionary containing contacts, suggestions, and metadata
        """
        try:
            if not self._initialized:
                await self.initialize()

            # Normalize and process query
            normalized_query = self._normalize_query(query)

            if len(normalized_query) < 2:
                return await self._get_default_suggestions(tenant_id, user_id, limit)

            # Perform fuzzy contact search
            contacts = await self._fuzzy_contact_search(
                normalized_query, tenant_id, user_id, limit
            )

            # Generate search suggestions if requested
            suggestions = []
            if include_suggestions:
                suggestions = await self._generate_contact_suggestions(
                    normalized_query, tenant_id, user_id, limit=5
                )

            # Add interaction indicators and platform distribution
            enriched_contacts = await self._enrich_contact_results(
                contacts, tenant_id, user_id
            )

            return {
                "contacts": enriched_contacts,
                "suggestions": suggestions,
                "query": query,
                "normalized_query": normalized_query,
                "total_results": len(contacts),
                "has_more": len(contacts) == limit
            }

        except Exception as e:
            logger.error(f"Real-time contact search failed: {e}")
            return {
                "contacts": [],
                "suggestions": [],
                "query": query,
                "error": str(e)
            }

    async def process_natural_language_query(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Process natural language queries like "messages with John".

        Args:
            query: Natural language query
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Processed query with extracted contacts and filters
        """
        try:
            # Create search query object
            search_query = SearchQuery(text=query)

            # Process with query processor
            processed_query = await self.query_processor.process_query(search_query)

            # Extract contact information from entities
            contact_info = await self._extract_contact_from_entities(
                processed_query.extracted_entities or [], tenant_id, user_id
            )

            # Build search filters based on intent
            filters = await self._build_filters_from_intent(
                processed_query, contact_info, tenant_id, user_id
            )

            return {
                "intent": processed_query.intent.value if processed_query.intent else "general",
                "processed_text": processed_query.processed_text,
                "contacts": contact_info,
                "filters": filters,
                "temporal_constraints": processed_query.temporal_constraints or {},
                "entities": processed_query.extracted_entities or []
            }

        except Exception as e:
            logger.error(f"Natural language query processing failed: {e}")
            return {
                "intent": "general",
                "processed_text": query,
                "contacts": [],
                "filters": {},
                "error": str(e)
            }

    def _normalize_query(self, query: str) -> str:
        """Normalize search query for better matching."""
        # Remove extra whitespace and convert to lowercase
        normalized = re.sub(r'\s+', ' ', query.strip().lower())

        # Remove common punctuation but keep @ and . for emails
        normalized = re.sub(r'[^\w\s@.-]', '', normalized)

        return normalized

    async def _fuzzy_contact_search(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[UnifiedContact]:
        """Perform fuzzy contact search with multiple matching strategies."""
        search_conditions = []
        terms = query.split()

        for term in terms:
            if len(term) < 2:
                continue

            # Name matching (primary and display names)
            search_conditions.extend([
                UnifiedContact.primary_name.ilike(f"%{term}%"),
                UnifiedContact.display_name.ilike(f"%{term}%")
            ])

            # Email matching
            if '@' in term or '.' in term:
                search_conditions.append(
                    UnifiedContact.primary_email.ilike(f"%{term}%")
                )

            # Phone matching (remove formatting)
            if term.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
                phone_term = re.sub(r'[^\d]', '', term)
                if len(phone_term) >= 3:
                    search_conditions.append(
                        func.regexp_replace(
                            UnifiedContact.primary_phone, r'[^\d]', '', 'g'
                        ).ilike(f"%{phone_term}%")
                    )

        # Full name search for multi-word queries
        if len(terms) > 1:
            full_query = ' '.join(terms)
            search_conditions.extend([
                UnifiedContact.primary_name.ilike(f"%{full_query}%"),
                UnifiedContact.display_name.ilike(f"%{full_query}%")
            ])

        if not search_conditions:
            return []

        # Build main query
        main_query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_archived == False,
                or_(*search_conditions)
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(
            desc(UnifiedContact.is_favorite),
            desc(UnifiedContact.last_interaction),
            UnifiedContact.primary_name
        ).limit(limit)

        result = await self.db.execute(main_query)
        contacts = result.scalars().all()

        # If we don't have enough results, search by identity
        if len(contacts) < limit:
            identity_contacts = await self._search_by_identity(
                query, tenant_id, user_id, limit - len(contacts)
            )

            # Merge results, avoiding duplicates
            existing_ids = {c.id for c in contacts}
            for contact in identity_contacts:
                if contact.id not in existing_ids:
                    contacts.append(contact)

        return contacts

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

            # Search in identity fields
            identity_conditions.extend([
                ContactIdentity.display_name.ilike(f"%{term}%"),
                ContactIdentity.platform_handle.ilike(f"%{term}%")
            ])

            # Email in identity
            if '@' in term or '.' in term:
                identity_conditions.append(
                    ContactIdentity.email.ilike(f"%{term}%")
                )

            # Phone in identity
            if term.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
                phone_term = re.sub(r'[^\d]', '', term)
                if len(phone_term) >= 3:
                    identity_conditions.append(
                        func.regexp_replace(
                            ContactIdentity.phone, r'[^\d]', '', 'g'
                        ).ilike(f"%{phone_term}%")
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

    async def _generate_contact_suggestions(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate intelligent contact search suggestions."""
        suggestions = []

        try:
            # Name-based suggestions
            if len(query) >= 2:
                name_suggestions = await self._get_name_suggestions(
                    query, tenant_id, user_id, limit
                )
                suggestions.extend(name_suggestions)

            # Platform-specific suggestions
            platform_suggestions = await self._get_platform_suggestions(
                query, tenant_id, user_id, limit - len(suggestions)
            )
            suggestions.extend(platform_suggestions)

            # Recent contacts suggestions
            if len(suggestions) < limit:
                recent_suggestions = await self._get_recent_contact_suggestions(
                    tenant_id, user_id, limit - len(suggestions)
                )
                suggestions.extend(recent_suggestions)

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")

        return suggestions[:limit]

    async def _get_default_suggestions(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> Dict[str, Any]:
        """Get default suggestions when query is too short."""
        try:
            # Get favorite contacts
            favorites = await self._get_favorite_contacts(tenant_id, user_id, limit // 2)

            # Get recent contacts
            recent = await self._get_recent_contacts(tenant_id, user_id, limit // 2)

            return {
                "contacts": [],
                "suggestions": [
                    {
                        "type": "favorites",
                        "title": "Favorite Contacts",
                        "contacts": [self._serialize_contact(c) for c in favorites]
                    },
                    {
                        "type": "recent",
                        "title": "Recent Contacts",
                        "contacts": [self._serialize_contact(c) for c in recent]
                    }
                ],
                "query": "",
                "total_results": 0
            }

        except Exception as e:
            logger.error(f"Failed to get default suggestions: {e}")
            return {"contacts": [], "suggestions": [], "query": ""}

    async def _enrich_contact_results(
        self,
        contacts: List[UnifiedContact],
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Enrich contact results with interaction indicators and platform distribution."""
        enriched = []

        for contact in contacts:
            try:
                # Get recent interaction indicator
                recent_interaction = await self._get_recent_interaction_indicator(
                    contact, tenant_id
                )

                # Get platform distribution
                platform_distribution = await self._get_platform_distribution(
                    contact, tenant_id
                )

                # Serialize contact with enrichments
                contact_data = self._serialize_contact(contact)
                contact_data.update({
                    "recent_interaction": recent_interaction,
                    "platform_distribution": platform_distribution,
                    "interaction_indicators": {
                        "has_recent_messages": recent_interaction.get("days_since", float('inf')) <= 7,
                        "is_frequent_contact": contact.communication_frequency in ["frequent", "daily"],
                        "has_unread_messages": False  # Would need to implement
                    }
                })

                enriched.append(contact_data)

            except Exception as e:
                logger.error(f"Failed to enrich contact {contact.id}: {e}")
                # Add basic contact data even if enrichment fails
                enriched.append(self._serialize_contact(contact))

        return enriched

    def _serialize_contact(self, contact: UnifiedContact) -> Dict[str, Any]:
        """Serialize contact to dictionary format."""
        return {
            "id": str(contact.id),
            "primary_name": contact.primary_name,
            "display_name": contact.display_name,
            "profile_photo_url": contact.profile_photo_url,
            "primary_email": contact.primary_email,
            "primary_phone": contact.primary_phone,
            "last_interaction": contact.last_interaction.isoformat() if contact.last_interaction else None,
            "total_messages": contact.total_messages,
            "platforms": contact.platforms or [],
            "relationship_strength": contact.relationship_strength,
            "communication_frequency": contact.communication_frequency,
            "is_favorite": contact.is_favorite,
            "tags": contact.tags or [],
            "identities": [
                {
                    "platform": identity.platform,
                    "platform_user_id": identity.platform_user_id,
                    "platform_handle": identity.platform_handle,
                    "display_name": identity.display_name,
                    "is_verified": identity.is_verified
                }
                for identity in (contact.identities or [])
            ]
        }

    async def _extract_contact_from_entities(
        self,
        entities: List[Dict[str, Any]],
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Extract and resolve contact information from entities."""
        contacts = []

        try:
            person_entities = [
                e for e in entities if e.get("type") == "person"]

            for entity in person_entities:
                person_name = entity.get("value", "").strip()
                if not person_name:
                    continue

                # Search for contacts matching this person
                matching_contacts = await self._fuzzy_contact_search(
                    person_name, tenant_id, user_id, limit=3
                )

                if matching_contacts:
                    # Take the best match
                    best_match = matching_contacts[0]
                    contacts.append({
                        "entity": entity,
                        "contact": self._serialize_contact(best_match),
                        "confidence": entity.get("confidence", 0.7)
                    })

        except Exception as e:
            logger.error(f"Failed to extract contacts from entities: {e}")

        return contacts

    async def _build_filters_from_intent(
        self,
        processed_query: SearchQuery,
        contact_info: List[Dict[str, Any]],
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Build search filters based on query intent and extracted contacts."""
        filters = {}

        try:
            # Add contact filters
            if contact_info:
                contact_ids = [c["contact"]["id"] for c in contact_info]
                filters["contact_ids"] = contact_ids

            # Add temporal filters
            if processed_query.temporal_constraints:
                filters.update(processed_query.temporal_constraints)

            # Intent-specific filters
            if processed_query.intent == QueryIntent.FILE_SEARCH:
                filters["has_attachments"] = True
            elif processed_query.intent == QueryIntent.COMMITMENT_SEARCH:
                filters["entity_types"] = ["commitment", "task", "deadline"]

        except Exception as e:
            logger.error(f"Failed to build filters from intent: {e}")

        return filters

    async def _get_recent_interaction_indicator(
        self,
        contact: UnifiedContact,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get recent interaction indicator for a contact."""
        try:
            if not contact.last_interaction:
                return {
                    "has_recent": False,
                    "days_since": None,
                    "last_interaction": None
                }

            days_since = (datetime.utcnow() - contact.last_interaction).days

            return {
                "has_recent": days_since <= 7,
                "days_since": days_since,
                "last_interaction": contact.last_interaction.isoformat(),
                "interaction_level": (
                    "today" if days_since == 0 else
                    "this_week" if days_since <= 7 else
                    "this_month" if days_since <= 30 else
                    "older"
                )
            }

        except Exception as e:
            logger.error(f"Failed to get interaction indicator: {e}")
            return {"has_recent": False, "days_since": None}

    async def _get_platform_distribution(
        self,
        contact: UnifiedContact,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get platform distribution for a contact."""
        try:
            platforms = contact.platforms or []

            # Get message counts per platform (simplified)
            platform_stats = {}
            for platform in platforms:
                platform_stats[platform] = {
                    "message_count": 0,  # Would need to query actual counts
                    "last_message": None,
                    "is_active": True
                }

            return {
                "platforms": platforms,
                "primary_platform": contact.preferred_platform,
                "platform_count": len(platforms),
                "platform_stats": platform_stats
            }

        except Exception as e:
            logger.error(f"Failed to get platform distribution: {e}")
            return {"platforms": [], "platform_count": 0}

    async def _get_name_suggestions(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get name-based suggestions."""
        suggestions = []

        try:
            # Get contacts with names starting with query
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
                        UnifiedContact.primary_name.ilike(f"{query}%"),
                        UnifiedContact.display_name.ilike(f"{query}%")
                    )
                )
            ).limit(limit)

            result = await self.db.execute(name_query)
            for row in result:
                suggestions.append({
                    "type": "name",
                    "text": row.primary_name or row.display_name,
                    "contact_id": str(row.id),
                    "suggestion_type": "name_completion"
                })

        except Exception as e:
            logger.error(f"Failed to get name suggestions: {e}")

        return suggestions

    async def _get_platform_suggestions(
        self,
        query: str,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get platform-specific suggestions."""
        suggestions = []

        try:
            # Get platform handles starting with query
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
                    ContactIdentity.platform_handle.ilike(f"{query}%")
                )
            ).limit(limit)

            result = await self.db.execute(handle_query)
            for row in result:
                if row.platform_handle:
                    suggestions.append({
                        "type": "handle",
                        "text": f"@{row.platform_handle}",
                        "platform": row.platform,
                        "contact_id": str(row.id),
                        "contact_name": row.primary_name,
                        "suggestion_type": "platform_handle"
                    })

        except Exception as e:
            logger.error(f"Failed to get platform suggestions: {e}")

        return suggestions

    async def _get_recent_contact_suggestions(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get recent contact suggestions."""
        suggestions = []

        try:
            recent_contacts = await self._get_recent_contacts(tenant_id, user_id, limit)

            for contact in recent_contacts:
                suggestions.append({
                    "type": "recent",
                    "text": contact.primary_name,
                    "contact_id": str(contact.id),
                    "suggestion_type": "recent_contact",
                    "last_interaction": contact.last_interaction.isoformat() if contact.last_interaction else None
                })

        except Exception as e:
            logger.error(f"Failed to get recent contact suggestions: {e}")

        return suggestions

    async def _get_favorite_contacts(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[UnifiedContact]:
        """Get favorite contacts."""
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_favorite == True,
                UnifiedContact.is_archived == False
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(desc(UnifiedContact.last_interaction)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_recent_contacts(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int
    ) -> List[UnifiedContact]:
        """Get recently interacted contacts."""
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.last_interaction >= cutoff_date,
                UnifiedContact.is_archived == False
            )
        ).options(
            selectinload(UnifiedContact.identities)
        ).order_by(desc(UnifiedContact.last_interaction)).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()
