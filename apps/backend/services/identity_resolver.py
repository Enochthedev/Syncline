"""
Identity Resolver Service

This module provides functionality for resolving and linking identities across platforms.

Features:
- Cross-platform identity linking
- Confidence scoring for identity matches
- Contact merging and splitting
- Identity conflict resolution
"""

import logging
from typing import List, Dict, Tuple, Optional, Set
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.contact import Contact
from db.models.participant import Participant
from services.event_bus import get_event_bus
from services.events.types import EventType, ContactEvent

logger = logging.getLogger(__name__)


class IdentityResolver:
    """
    Service for resolving identities across platforms.
    
    Handles:
    - Cross-platform identity linking
    - Confidence scoring for matches
    - Contact merging
    - Contact splitting
    - Identity conflict resolution
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9  # Very likely same person
    MEDIUM_CONFIDENCE = 0.7  # Probably same person
    LOW_CONFIDENCE = 0.5  # Possibly same person
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the identity resolver.
        
        Args:
            session: Database session
        """
        self.session = session
        self.event_bus = get_event_bus()
    
    async def link_identities(
        self,
        contact_id: UUID,
        platform: str,
        platform_user_id: str
    ) -> Contact:
        """
        Link a platform identity to a contact.
        
        Args:
            contact_id: Contact UUID
            platform: Platform name
            platform_user_id: Platform-specific user ID
        
        Returns:
            Updated contact
        """
        # Get contact
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await self.session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Update platform identities
        if not contact.platform_identities:
            contact.platform_identities = {}
        
        contact.platform_identities[platform] = platform_user_id
        contact.updated_at = datetime.utcnow()
        
        # Mark as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(contact, "platform_identities")
        
        await self.session.commit()
        
        logger.info(
            f"Linked identity {platform}:{platform_user_id} to contact {contact_id}"
        )
        
        return contact
    
    async def find_cross_platform_matches(
        self,
        contact_id: UUID,
        min_confidence: float = MEDIUM_CONFIDENCE
    ) -> List[Tuple[Contact, float, str]]:
        """
        Find potential cross-platform matches for a contact.
        
        Args:
            contact_id: Contact UUID to find matches for
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of (Contact, confidence, reason) tuples
        """
        # Get the source contact
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await self.session.execute(stmt)
        source_contact = result.scalar_one_or_none()
        
        if not source_contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Get all other contacts
        other_stmt = select(Contact).where(Contact.id != contact_id)
        other_result = await self.session.execute(other_stmt)
        other_contacts = other_result.scalars().all()
        
        matches = []
        
        for contact in other_contacts:
            confidence, reason = self._calculate_identity_confidence(
                source_contact,
                contact
            )
            
            if confidence >= min_confidence:
                matches.append((contact, confidence, reason))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    def _calculate_identity_confidence(
        self,
        contact1: Contact,
        contact2: Contact
    ) -> Tuple[float, str]:
        """
        Calculate confidence that two contacts are the same person.
        
        Args:
            contact1: First contact
            contact2: Second contact
        
        Returns:
            Tuple of (confidence score, reason)
        """
        reasons = []
        confidence_scores = []
        
        # Check for email overlap
        if contact1.emails and contact2.emails:
            email_overlap = set(contact1.emails) & set(contact2.emails)
            if email_overlap:
                confidence_scores.append(1.0)
                reasons.append(f"shared email(s): {', '.join(email_overlap)}")
        
        # Check for phone overlap
        if contact1.phones and contact2.phones:
            phone_overlap = set(contact1.phones) & set(contact2.phones)
            if phone_overlap:
                confidence_scores.append(1.0)
                reasons.append(f"shared phone(s): {', '.join(phone_overlap)}")
        
        # Check for name similarity
        name_similarity = self._calculate_name_similarity(
            contact1.canonical_name,
            contact2.canonical_name
        )
        if name_similarity >= 0.8:
            confidence_scores.append(name_similarity * 0.8)
            reasons.append(f"similar names ({name_similarity:.2f})")
        
        # Check for platform identity overlap (shouldn't happen, but check anyway)
        if contact1.platform_identities and contact2.platform_identities:
            platform_overlap = (
                set(contact1.platform_identities.keys()) &
                set(contact2.platform_identities.keys())
            )
            if platform_overlap:
                # Same platform identities is a strong indicator
                confidence_scores.append(0.9)
                reasons.append(f"shared platform(s): {', '.join(platform_overlap)}")
        
        # Calculate overall confidence
        if not confidence_scores:
            return 0.0, "no matching attributes"
        
        # Use maximum confidence score (any strong match is significant)
        confidence = max(confidence_scores)
        reason = "; ".join(reasons)
        
        return confidence, reason
    
    def _calculate_name_similarity(
        self,
        name1: str,
        name2: str
    ) -> float:
        """
        Calculate similarity between two names.
        
        Args:
            name1: First name
            name2: Second name
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        from difflib import SequenceMatcher
        
        normalized1 = name1.lower().strip()
        normalized2 = name2.lower().strip()
        
        return SequenceMatcher(None, normalized1, normalized2).ratio()
    
    async def merge_contacts(
        self,
        primary_contact_id: UUID,
        secondary_contact_id: UUID
    ) -> Contact:
        """
        Merge two contacts into one.
        
        The secondary contact is merged into the primary contact,
        and the secondary contact is deleted.
        
        Args:
            primary_contact_id: Contact to keep
            secondary_contact_id: Contact to merge and delete
        
        Returns:
            Updated primary contact
        """
        # Get both contacts
        primary_stmt = select(Contact).where(Contact.id == primary_contact_id)
        primary_result = await self.session.execute(primary_stmt)
        primary_contact = primary_result.scalar_one_or_none()
        
        if not primary_contact:
            raise ValueError(f"Primary contact {primary_contact_id} not found")
        
        secondary_stmt = select(Contact).where(Contact.id == secondary_contact_id)
        secondary_result = await self.session.execute(secondary_stmt)
        secondary_contact = secondary_result.scalar_one_or_none()
        
        if not secondary_contact:
            raise ValueError(f"Secondary contact {secondary_contact_id} not found")
        
        # Merge emails
        if secondary_contact.emails:
            if not primary_contact.emails:
                primary_contact.emails = []
            for email in secondary_contact.emails:
                if email not in primary_contact.emails:
                    primary_contact.emails.append(email)
        
        # Merge phones
        if secondary_contact.phones:
            if not primary_contact.phones:
                primary_contact.phones = []
            for phone in secondary_contact.phones:
                if phone not in primary_contact.phones:
                    primary_contact.phones.append(phone)
        
        # Merge platform identities
        if secondary_contact.platform_identities:
            if not primary_contact.platform_identities:
                primary_contact.platform_identities = {}
            for platform, user_id in secondary_contact.platform_identities.items():
                if platform not in primary_contact.platform_identities:
                    primary_contact.platform_identities[platform] = user_id
        
        # Merge metadata
        if secondary_contact.contact_metadata:
            if not primary_contact.contact_metadata:
                primary_contact.contact_metadata = {}
            
            # Merge metadata fields (primary takes precedence)
            for key, value in secondary_contact.contact_metadata.items():
                if key not in primary_contact.contact_metadata:
                    primary_contact.contact_metadata[key] = value
        
        # Mark fields as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(primary_contact, "emails")
        flag_modified(primary_contact, "phones")
        flag_modified(primary_contact, "platform_identities")
        flag_modified(primary_contact, "contact_metadata")
        
        # Update all participants pointing to secondary contact
        participant_stmt = select(Participant).where(
            Participant.contact_id == secondary_contact_id
        )
        participant_result = await self.session.execute(participant_stmt)
        participants = participant_result.scalars().all()
        
        for participant in participants:
            participant.contact_id = primary_contact_id
        
        # Update all threads pointing to secondary contact
        from db.models.thread import Thread
        thread_stmt = select(Thread).where(
            Thread.contact_id == secondary_contact_id
        )
        thread_result = await self.session.execute(thread_stmt)
        threads = thread_result.scalars().all()
        
        for thread in threads:
            thread.contact_id = primary_contact_id
        
        # Delete secondary contact
        await self.session.delete(secondary_contact)
        
        primary_contact.updated_at = datetime.utcnow()
        await self.session.commit()
        
        # Emit contact merged event
        await self._emit_contact_event(
            EventType.CONTACT_MERGED,
            primary_contact,
            extra_data={
                "merged_contact_id": str(secondary_contact_id),
                "participant_count": len(participants),
                "thread_count": len(threads)
            }
        )
        
        logger.info(
            f"Merged contact {secondary_contact_id} into {primary_contact_id} "
            f"({len(participants)} participants, {len(threads)} threads)"
        )
        
        return primary_contact
    
    async def split_contact(
        self,
        contact_id: UUID,
        participant_ids_to_split: List[UUID],
        new_contact_name: str
    ) -> Tuple[Contact, Contact]:
        """
        Split a contact into two contacts.
        
        Creates a new contact and moves specified participants to it.
        
        Args:
            contact_id: Original contact UUID
            participant_ids_to_split: Participant IDs to move to new contact
            new_contact_name: Name for the new contact
        
        Returns:
            Tuple of (original contact, new contact)
        """
        # Get original contact
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await self.session.execute(stmt)
        original_contact = result.scalar_one_or_none()
        
        if not original_contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Get participants to split
        participant_stmt = select(Participant).where(
            Participant.id.in_(participant_ids_to_split)
        )
        participant_result = await self.session.execute(participant_stmt)
        participants = participant_result.scalars().all()
        
        if not participants:
            raise ValueError("No participants found to split")
        
        # Verify all participants belong to the original contact
        for participant in participants:
            if participant.contact_id != contact_id:
                raise ValueError(
                    f"Participant {participant.id} does not belong to contact {contact_id}"
                )
        
        # Create new contact
        new_contact = Contact(
            canonical_name=new_contact_name,
            emails=[],
            phones=[],
            platform_identities={},
            contact_metadata={}
        )
        
        self.session.add(new_contact)
        await self.session.flush()  # Get the ID
        
        # Move participants to new contact
        for participant in participants:
            participant.contact_id = new_contact.id
            
            # Add participant info to new contact
            if participant.email:
                normalized_email = participant.email.lower().strip()
                if normalized_email not in new_contact.emails:
                    new_contact.emails.append(normalized_email)
            
            if participant.phone:
                normalized_phone = self._normalize_phone(participant.phone)
                if normalized_phone not in new_contact.phones:
                    new_contact.phones.append(normalized_phone)
            
            if participant.platform not in new_contact.platform_identities:
                new_contact.platform_identities[participant.platform] = participant.platform_user_id
        
        # Mark fields as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(new_contact, "emails")
        flag_modified(new_contact, "phones")
        flag_modified(new_contact, "platform_identities")
        
        # Update threads if all participants in a thread moved
        from db.models.thread import Thread
        thread_stmt = select(Thread).where(
            Thread.contact_id == contact_id
        )
        thread_result = await self.session.execute(thread_stmt)
        threads = thread_result.scalars().all()
        
        moved_participant_ids = {p.id for p in participants}
        
        for thread in threads:
            if thread.participant_ids:
                thread_participant_ids = set(thread.participant_ids)
                # If all thread participants were moved, move the thread too
                if thread_participant_ids.issubset(moved_participant_ids):
                    thread.contact_id = new_contact.id
        
        original_contact.updated_at = datetime.utcnow()
        await self.session.commit()
        
        # Emit contact created event for new contact
        await self._emit_contact_event(
            EventType.CONTACT_CREATED,
            new_contact,
            extra_data={
                "split_from_contact_id": str(contact_id),
                "participant_count": len(participants)
            }
        )
        
        logger.info(
            f"Split contact {contact_id}: moved {len(participants)} participants "
            f"to new contact {new_contact.id}"
        )
        
        return original_contact, new_contact
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize a phone number.
        
        Args:
            phone: Phone number to normalize
        
        Returns:
            Normalized phone number
        """
        normalized = phone.strip()
        for char in [" ", "-", "(", ")", ".", "+"]:
            normalized = normalized.replace(char, "")
        return normalized
    
    async def resolve_identity_conflicts(
        self,
        min_confidence: float = HIGH_CONFIDENCE
    ) -> List[Tuple[Contact, Contact, float, str]]:
        """
        Find potential duplicate contacts that should be merged.
        
        Args:
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of (contact1, contact2, confidence, reason) tuples
        """
        # Get all contacts
        stmt = select(Contact)
        result = await self.session.execute(stmt)
        contacts = list(result.scalars().all())
        
        conflicts = []
        checked_pairs: Set[Tuple[UUID, UUID]] = set()
        
        # Compare all pairs of contacts
        for i, contact1 in enumerate(contacts):
            for contact2 in contacts[i + 1:]:
                # Create sorted pair to avoid duplicates
                pair = tuple(sorted([contact1.id, contact2.id]))
                
                if pair in checked_pairs:
                    continue
                
                checked_pairs.add(pair)
                
                # Calculate confidence
                confidence, reason = self._calculate_identity_confidence(
                    contact1,
                    contact2
                )
                
                if confidence >= min_confidence:
                    conflicts.append((contact1, contact2, confidence, reason))
        
        # Sort by confidence (highest first)
        conflicts.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(
            f"Found {len(conflicts)} potential duplicate contacts "
            f"(min_confidence={min_confidence})"
        )
        
        return conflicts
    
    async def get_contact_identity_summary(
        self,
        contact_id: UUID
    ) -> Dict:
        """
        Get a summary of a contact's identities across platforms.
        
        Args:
            contact_id: Contact UUID
        
        Returns:
            Dictionary with identity information
        """
        # Get contact
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await self.session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Get all participants
        participant_stmt = select(Participant).where(
            Participant.contact_id == contact_id
        )
        participant_result = await self.session.execute(participant_stmt)
        participants = participant_result.scalars().all()
        
        # Build summary
        summary = {
            "contact_id": str(contact.id),
            "canonical_name": contact.canonical_name,
            "emails": contact.emails or [],
            "phones": contact.phones or [],
            "platform_identities": contact.platform_identities or {},
            "participants": [
                {
                    "id": str(p.id),
                    "platform": p.platform,
                    "platform_user_id": p.platform_user_id,
                    "name": p.name,
                    "email": p.email,
                    "phone": p.phone
                }
                for p in participants
            ],
            "platform_count": len(contact.platform_identities or {}),
            "participant_count": len(participants)
        }
        
        return summary
    
    async def _emit_contact_event(
        self,
        event_type: EventType,
        contact: Contact,
        extra_data: dict = None
    ) -> None:
        """
        Emit a contact lifecycle event.
        
        Args:
            event_type: Type of event
            contact: Contact instance
            extra_data: Additional event data
        """
        try:
            payload = {
                "contact_id": str(contact.id),
                "canonical_name": contact.canonical_name,
                "emails": contact.emails or [],
                "phones": contact.phones or [],
                "platform_identities": contact.platform_identities or {},
            }
            
            if extra_data:
                payload.update(extra_data)
            
            event = ContactEvent(
                event_id=str(UUID(int=0)),  # Will be replaced by event bus
                event_type=event_type,
                source="identity_resolver",
                payload=payload
            )
            
            await self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to emit contact event: {e}")
            # Don't raise - event emission failure shouldn't break the operation


# Export public API
__all__ = [
    "IdentityResolver",
]
