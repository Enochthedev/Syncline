"""Contact merger service for unifying duplicate contacts."""

import logging
from typing import List, Optional, Dict, Any, Set
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import selectinload

from db.models.unified_contact import (
    UnifiedContact, ContactIdentity, ContactInsight,
    ContactPreference, ContactRelationship
)

logger = logging.getLogger(__name__)


class ContactMerger:
    """Service for merging duplicate contacts and managing contact identities."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def merge_contacts(
        self,
        primary_id: UUID,
        duplicate_ids: List[UUID],
        tenant_id: UUID,
        user_id: UUID
    ) -> UnifiedContact:
        """Merge duplicate contacts into a primary contact."""
        # Get all contacts to merge
        all_ids = [primary_id] + duplicate_ids

        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.id.in_(all_ids),
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        ).options(
            selectinload(UnifiedContact.identities),
            selectinload(UnifiedContact.insights),
            selectinload(UnifiedContact.preferences)
        )

        result = await self.db.execute(query)
        contacts = result.scalars().all()

        if not contacts:
            raise ValueError("No contacts found to merge")

        # Find the primary contact
        primary_contact = None
        duplicate_contacts = []

        for contact in contacts:
            if contact.id == primary_id:
                primary_contact = contact
            else:
                duplicate_contacts.append(contact)

        if not primary_contact:
            raise ValueError("Primary contact not found")

        if not duplicate_contacts:
            logger.warning("No duplicate contacts found to merge")
            return primary_contact

        # Merge data into primary contact
        await self._merge_contact_data(primary_contact, duplicate_contacts)

        # Merge identities
        await self._merge_identities(primary_contact, duplicate_contacts)

        # Merge insights
        await self._merge_insights(primary_contact, duplicate_contacts)

        # Merge preferences
        await self._merge_preferences(primary_contact, duplicate_contacts)

        # Update relationships
        await self._update_relationships(primary_contact, duplicate_contacts)

        # Delete duplicate contacts
        await self._delete_duplicate_contacts(duplicate_contacts)

        # Update primary contact metadata
        primary_contact.updated_at = datetime.utcnow()
        await self.db.commit()

        # Refresh to get updated relationships
        await self.db.refresh(primary_contact)

        logger.info(
            f"Successfully merged {len(duplicate_contacts)} contacts into {primary_id}")
        return primary_contact

    async def _merge_contact_data(
        self,
        primary: UnifiedContact,
        duplicates: List[UnifiedContact]
    ) -> None:
        """Merge basic contact data, preferring non-null values."""
        # Collect all values for each field
        all_contacts = [primary] + duplicates

        # Merge basic fields (prefer non-null, non-empty values)
        if not primary.display_name:
            for contact in duplicates:
                if contact.display_name:
                    primary.display_name = contact.display_name
                    break

        if not primary.profile_photo_url:
            for contact in duplicates:
                if contact.profile_photo_url:
                    primary.profile_photo_url = contact.profile_photo_url
                    break

        if not primary.primary_email:
            for contact in duplicates:
                if contact.primary_email:
                    primary.primary_email = contact.primary_email
                    break

        if not primary.primary_phone:
            for contact in duplicates:
                if contact.primary_phone:
                    primary.primary_phone = contact.primary_phone
                    break

        # Merge timestamps (earliest first interaction, latest last interaction)
        first_interactions = [
            c.first_interaction for c in all_contacts if c.first_interaction]
        if first_interactions:
            primary.first_interaction = min(first_interactions)

        last_interactions = [
            c.last_interaction for c in all_contacts if c.last_interaction]
        if last_interactions:
            primary.last_interaction = max(last_interactions)

        # Sum message and thread counts
        primary.total_messages = sum(
            c.total_messages or 0 for c in all_contacts)
        primary.total_threads = sum(c.total_threads or 0 for c in all_contacts)

        # Merge platforms (union of all platforms)
        all_platforms = set()
        for contact in all_contacts:
            if contact.platforms:
                all_platforms.update(contact.platforms)
        primary.platforms = list(all_platforms)

        # Use highest relationship strength
        strengths = [
            c.relationship_strength for c in all_contacts if c.relationship_strength]
        if strengths:
            primary.relationship_strength = max(strengths)

        # Merge tags (union)
        all_tags = set()
        for contact in all_contacts:
            if contact.tags:
                all_tags.update(contact.tags)
        primary.tags = list(all_tags)

        # Merge custom notes
        notes = []
        for contact in all_contacts:
            if contact.custom_notes:
                notes.append(
                    f"From {contact.primary_name}: {contact.custom_notes}")
        if notes:
            primary.custom_notes = "\n\n".join(notes)

        # Keep favorite status if any contact is favorite
        primary.is_favorite = primary.is_favorite or any(
            c.is_favorite for c in duplicates)

        # Merge metadata
        merged_metadata = {}
        for contact in all_contacts:
            if contact.extra_metadata:
                merged_metadata.update(contact.extra_metadata)
        primary.extra_metadata = merged_metadata

    async def _merge_identities(
        self,
        primary: UnifiedContact,
        duplicates: List[UnifiedContact]
    ) -> None:
        """Merge contact identities, avoiding duplicates."""
        # Get existing identity keys for primary contact
        existing_keys = set()
        for identity in primary.identities:
            key = (identity.platform, identity.platform_user_id)
            existing_keys.add(key)

        # Collect identities from duplicates
        identities_to_merge = []
        for contact in duplicates:
            for identity in contact.identities:
                key = (identity.platform, identity.platform_user_id)
                if key not in existing_keys:
                    identities_to_merge.append(identity)
                    existing_keys.add(key)

        # Update identities to point to primary contact
        for identity in identities_to_merge:
            identity.unified_contact_id = primary.id
            identity.updated_at = datetime.utcnow()

    async def _merge_insights(
        self,
        primary: UnifiedContact,
        duplicates: List[UnifiedContact]
    ) -> None:
        """Merge contact insights, keeping the most recent and relevant ones."""
        # Get all insights from duplicates
        insights_to_merge = []
        for contact in duplicates:
            for insight in contact.insights:
                if insight.is_active:
                    insights_to_merge.append(insight)

        # Update insights to point to primary contact
        for insight in insights_to_merge:
            insight.unified_contact_id = primary.id

        # Deactivate duplicate insights of the same type
        await self._deactivate_duplicate_insights(primary.id)

    async def _deactivate_duplicate_insights(self, contact_id: UUID) -> None:
        """Deactivate duplicate insights of the same type, keeping the most recent."""
        # Get all insights for the contact grouped by type
        query = select(ContactInsight).where(
            and_(
                ContactInsight.unified_contact_id == contact_id,
                ContactInsight.is_active == True
            )
        ).order_by(ContactInsight.insight_type, ContactInsight.generated_at.desc())

        result = await self.db.execute(query)
        insights = result.scalars().all()

        # Group by type and keep only the most recent
        seen_types = set()
        for insight in insights:
            if insight.insight_type in seen_types:
                insight.is_active = False
            else:
                seen_types.add(insight.insight_type)

    async def _merge_preferences(
        self,
        primary: UnifiedContact,
        duplicates: List[UnifiedContact]
    ) -> None:
        """Merge contact preferences, preferring primary contact's settings."""
        # If primary has no preferences, use the first duplicate's preferences
        if not primary.preferences and duplicates:
            for contact in duplicates:
                if contact.preferences:
                    for pref in contact.preferences:
                        pref.unified_contact_id = primary.id
                        pref.updated_at = datetime.utcnow()
                    break

        # Delete duplicate preferences (keep only one set per contact)
        for contact in duplicates:
            if contact.preferences and primary.preferences:
                for pref in contact.preferences:
                    await self.db.delete(pref)

    async def _update_relationships(
        self,
        primary: UnifiedContact,
        duplicates: List[UnifiedContact]
    ) -> None:
        """Update contact relationships to point to the primary contact."""
        duplicate_ids = [c.id for c in duplicates]

        # Update relationships where duplicates are contact_a
        query_a = select(ContactRelationship).where(
            ContactRelationship.contact_a_id.in_(duplicate_ids)
        )
        result_a = await self.db.execute(query_a)
        relationships_a = result_a.scalars().all()

        for rel in relationships_a:
            rel.contact_a_id = primary.id

        # Update relationships where duplicates are contact_b
        query_b = select(ContactRelationship).where(
            ContactRelationship.contact_b_id.in_(duplicate_ids)
        )
        result_b = await self.db.execute(query_b)
        relationships_b = result_b.scalars().all()

        for rel in relationships_b:
            rel.contact_b_id = primary.id

        # Remove duplicate relationships (same contact pair)
        await self._remove_duplicate_relationships(primary.id)

    async def _remove_duplicate_relationships(self, contact_id: UUID) -> None:
        """Remove duplicate relationships for a contact."""
        query = select(ContactRelationship).where(
            or_(
                ContactRelationship.contact_a_id == contact_id,
                ContactRelationship.contact_b_id == contact_id
            )
        ).order_by(ContactRelationship.discovered_at.desc())

        result = await self.db.execute(query)
        relationships = result.scalars().all()

        # Track seen relationships (normalize contact pairs)
        seen_pairs = set()
        to_delete = []

        for rel in relationships:
            # Normalize pair (smaller ID first)
            pair = tuple(sorted([rel.contact_a_id, rel.contact_b_id]))

            if pair in seen_pairs:
                to_delete.append(rel)
            else:
                seen_pairs.add(pair)

        # Delete duplicates
        for rel in to_delete:
            await self.db.delete(rel)

    async def _delete_duplicate_contacts(self, duplicates: List[UnifiedContact]) -> None:
        """Delete duplicate contacts and their remaining relationships."""
        for contact in duplicates:
            await self.db.delete(contact)

    async def find_potential_duplicates(
        self,
        tenant_id: UUID,
        user_id: UUID,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Find potential duplicate contacts based on similarity."""
        # Get all contacts for the user
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.is_archived == False
            )
        ).options(selectinload(UnifiedContact.identities))

        result = await self.db.execute(query)
        contacts = result.scalars().all()

        if len(contacts) < 2:
            return []

        duplicates = []
        processed = set()

        for i, contact_a in enumerate(contacts):
            if contact_a.id in processed:
                continue

            similar_contacts = []

            for j, contact_b in enumerate(contacts[i+1:], i+1):
                if contact_b.id in processed:
                    continue

                similarity = self._calculate_contact_similarity(
                    contact_a, contact_b)

                if similarity >= similarity_threshold:
                    similar_contacts.append({
                        'contact': contact_b,
                        'similarity': similarity
                    })
                    processed.add(contact_b.id)

            if similar_contacts:
                duplicates.append({
                    'primary_contact': contact_a,
                    'similar_contacts': similar_contacts,
                    'group_size': len(similar_contacts) + 1
                })
                processed.add(contact_a.id)

        return duplicates

    def _calculate_contact_similarity(
        self,
        contact_a: UnifiedContact,
        contact_b: UnifiedContact
    ) -> float:
        """Calculate similarity score between two contacts."""
        score = 0.0
        max_score = 0.0

        # Name similarity (weight: 0.4)
        name_weight = 0.4
        max_score += name_weight

        if contact_a.primary_name and contact_b.primary_name:
            name_similarity = self._calculate_string_similarity(
                contact_a.primary_name.lower(),
                contact_b.primary_name.lower()
            )
            score += name_similarity * name_weight

        # Email similarity (weight: 0.3)
        email_weight = 0.3
        max_score += email_weight

        if contact_a.primary_email and contact_b.primary_email:
            if contact_a.primary_email.lower() == contact_b.primary_email.lower():
                score += email_weight

        # Phone similarity (weight: 0.2)
        phone_weight = 0.2
        max_score += phone_weight

        if contact_a.primary_phone and contact_b.primary_phone:
            # Normalize phone numbers for comparison
            phone_a = ''.join(filter(str.isdigit, contact_a.primary_phone))
            phone_b = ''.join(filter(str.isdigit, contact_b.primary_phone))

            if phone_a and phone_b and phone_a == phone_b:
                score += phone_weight

        # Platform identity overlap (weight: 0.1)
        identity_weight = 0.1
        max_score += identity_weight

        identities_a = {(i.platform, i.platform_user_id)
                        for i in contact_a.identities}
        identities_b = {(i.platform, i.platform_user_id)
                        for i in contact_b.identities}

        if identities_a and identities_b:
            overlap = len(identities_a.intersection(identities_b))
            total = len(identities_a.union(identities_b))
            if total > 0:
                identity_similarity = overlap / total
                score += identity_similarity * identity_weight

        return score / max_score if max_score > 0 else 0.0

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using simple algorithm."""
        if not str1 or not str2:
            return 0.0

        if str1 == str2:
            return 1.0

        # Simple Levenshtein-like similarity
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0

        # Count matching characters
        matches = 0
        for i in range(min(len(str1), len(str2))):
            if str1[i] == str2[i]:
                matches += 1

        return matches / max_len

    async def suggest_merge_candidates(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Suggest merge candidates for a specific contact."""
        # Get the target contact
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        ).options(selectinload(UnifiedContact.identities))

        result = await self.db.execute(query)
        target_contact = result.scalar_one_or_none()

        if not target_contact:
            return []

        # Get other contacts for comparison
        other_query = select(UnifiedContact).where(
            and_(
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                UnifiedContact.id != contact_id,
                UnifiedContact.is_archived == False
            )
        ).options(selectinload(UnifiedContact.identities))

        other_result = await self.db.execute(other_query)
        other_contacts = other_result.scalars().all()

        # Calculate similarities
        candidates = []
        for contact in other_contacts:
            similarity = self._calculate_contact_similarity(
                target_contact, contact)
            if similarity > 0.5:  # Only suggest reasonably similar contacts
                candidates.append({
                    'contact_id': str(contact.id),
                    'primary_name': contact.primary_name,
                    'similarity': similarity,
                    'reasons': self._get_similarity_reasons(target_contact, contact)
                })

        # Sort by similarity and return top candidates
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        return candidates[:limit]

    def _get_similarity_reasons(
        self,
        contact_a: UnifiedContact,
        contact_b: UnifiedContact
    ) -> List[str]:
        """Get reasons why two contacts might be duplicates."""
        reasons = []

        # Check name similarity
        if contact_a.primary_name and contact_b.primary_name:
            name_sim = self._calculate_string_similarity(
                contact_a.primary_name.lower(),
                contact_b.primary_name.lower()
            )
            if name_sim > 0.8:
                reasons.append("Very similar names")
            elif name_sim > 0.6:
                reasons.append("Similar names")

        # Check email match
        if (contact_a.primary_email and contact_b.primary_email and
                contact_a.primary_email.lower() == contact_b.primary_email.lower()):
            reasons.append("Same email address")

        # Check phone match
        if contact_a.primary_phone and contact_b.primary_phone:
            phone_a = ''.join(filter(str.isdigit, contact_a.primary_phone))
            phone_b = ''.join(filter(str.isdigit, contact_b.primary_phone))
            if phone_a and phone_b and phone_a == phone_b:
                reasons.append("Same phone number")

        # Check platform overlap
        identities_a = {(i.platform, i.platform_user_id)
                        for i in contact_a.identities}
        identities_b = {(i.platform, i.platform_user_id)
                        for i in contact_b.identities}
        overlap = identities_a.intersection(identities_b)

        if overlap:
            platforms = [platform for platform, _ in overlap]
            reasons.append(f"Same identity on {', '.join(platforms)}")

        return reasons
