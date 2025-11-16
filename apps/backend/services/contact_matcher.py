"""
Contact Matcher Service

This module provides functionality for matching participants to contacts across platforms.

Features:
- Email-based matching
- Phone-based matching
- Name similarity matching with fuzzy logic
- Confidence scoring for matches
- Automatic contact creation and merging
"""

import logging
from typing import List, Tuple, Optional
from uuid import UUID
from difflib import SequenceMatcher

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.contact import Contact
from db.models.participant import Participant
from services.event_bus import get_event_bus
from services.events.types import EventType, ContactEvent

logger = logging.getLogger(__name__)


class ContactMatcher:
    """
    Service for matching participants to contacts.
    
    Handles:
    - Email-based matching
    - Phone-based matching
    - Name similarity matching
    - Confidence scoring
    - Contact creation and updates
    """
    
    # Matching thresholds
    EMAIL_MATCH_CONFIDENCE = 1.0  # Exact email match
    PHONE_MATCH_CONFIDENCE = 1.0  # Exact phone match
    NAME_SIMILARITY_THRESHOLD = 0.85  # Minimum similarity for name match
    NAME_MATCH_CONFIDENCE = 0.8  # Confidence for name-based match
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the contact matcher.
        
        Args:
            session: Database session
        """
        self.session = session
        self.event_bus = get_event_bus()
    
    async def match_participant(
        self,
        participant: Participant,
        auto_create: bool = True
    ) -> Tuple[Optional[Contact], float]:
        """
        Match a participant to a contact.
        
        Tries matching strategies in order of confidence:
        1. Email-based matching (confidence: 1.0)
        2. Phone-based matching (confidence: 1.0)
        3. Name similarity matching (confidence: 0.8)
        
        Args:
            participant: Participant to match
            auto_create: Whether to create a new contact if no match found
        
        Returns:
            Tuple of (Contact or None, confidence score)
        """
        # Skip if already matched
        if participant.contact_id:
            stmt = select(Contact).where(Contact.id == participant.contact_id)
            result = await self.session.execute(stmt)
            contact = result.scalar_one_or_none()
            if contact:
                return contact, 1.0
        
        # Try email-based matching
        if participant.email:
            contact, confidence = await self._match_by_email(participant.email)
            if contact:
                await self._link_participant_to_contact(participant, contact)
                return contact, confidence
        
        # Try phone-based matching
        if participant.phone:
            contact, confidence = await self._match_by_phone(participant.phone)
            if contact:
                await self._link_participant_to_contact(participant, contact)
                return contact, confidence
        
        # Try name similarity matching
        if participant.name:
            contact, confidence = await self._match_by_name(participant.name)
            if contact and confidence >= self.NAME_SIMILARITY_THRESHOLD:
                await self._link_participant_to_contact(participant, contact)
                return contact, confidence
        
        # No match found - create new contact if requested
        if auto_create:
            contact = await self._create_contact_from_participant(participant)
            await self._link_participant_to_contact(participant, contact)
            return contact, 1.0
        
        return None, 0.0
    
    async def _match_by_email(
        self,
        email: str
    ) -> Tuple[Optional[Contact], float]:
        """
        Match a contact by email address.
        
        Args:
            email: Email address to match
        
        Returns:
            Tuple of (Contact or None, confidence score)
        """
        normalized_email = email.lower().strip()
        
        # Search for contacts with this email
        stmt = select(Contact).where(
            Contact.emails.contains([normalized_email])
        )
        result = await self.session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if contact:
            logger.info(
                f"Matched contact {contact.id} by email: {normalized_email}"
            )
            return contact, self.EMAIL_MATCH_CONFIDENCE
        
        return None, 0.0
    
    async def _match_by_phone(
        self,
        phone: str
    ) -> Tuple[Optional[Contact], float]:
        """
        Match a contact by phone number.
        
        Args:
            phone: Phone number to match
        
        Returns:
            Tuple of (Contact or None, confidence score)
        """
        normalized_phone = self._normalize_phone(phone)
        
        # Search for contacts with this phone
        stmt = select(Contact).where(
            Contact.phones.contains([normalized_phone])
        )
        result = await self.session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if contact:
            logger.info(
                f"Matched contact {contact.id} by phone: {normalized_phone}"
            )
            return contact, self.PHONE_MATCH_CONFIDENCE
        
        return None, 0.0
    
    async def _match_by_name(
        self,
        name: str
    ) -> Tuple[Optional[Contact], float]:
        """
        Match a contact by name similarity.
        
        Uses fuzzy string matching to find similar names.
        
        Args:
            name: Name to match
        
        Returns:
            Tuple of (Contact or None, confidence score)
        """
        normalized_name = name.lower().strip()
        
        # Get all contacts for comparison
        stmt = select(Contact)
        result = await self.session.execute(stmt)
        contacts = result.scalars().all()
        
        best_match = None
        best_similarity = 0.0
        
        for contact in contacts:
            similarity = self._calculate_name_similarity(
                normalized_name,
                contact.canonical_name.lower().strip()
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = contact
        
        if best_match and best_similarity >= self.NAME_SIMILARITY_THRESHOLD:
            logger.info(
                f"Matched contact {best_match.id} by name similarity: "
                f"{name} ~ {best_match.canonical_name} "
                f"(similarity: {best_similarity:.2f})"
            )
            return best_match, self.NAME_MATCH_CONFIDENCE
        
        return None, 0.0
    
    def _calculate_name_similarity(
        self,
        name1: str,
        name2: str
    ) -> float:
        """
        Calculate similarity between two names.
        
        Uses SequenceMatcher for fuzzy string matching.
        
        Args:
            name1: First name
            name2: Second name
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        return SequenceMatcher(None, name1, name2).ratio()
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize a phone number for matching.
        
        Removes common formatting characters.
        
        Args:
            phone: Phone number to normalize
        
        Returns:
            Normalized phone number
        """
        # Remove common formatting characters
        normalized = phone.strip()
        for char in [" ", "-", "(", ")", ".", "+"]:
            normalized = normalized.replace(char, "")
        
        return normalized
    
    async def _create_contact_from_participant(
        self,
        participant: Participant
    ) -> Contact:
        """
        Create a new contact from a participant.
        
        Args:
            participant: Participant to create contact from
        
        Returns:
            New Contact instance
        """
        # Prepare contact data
        emails = [participant.email.lower().strip()] if participant.email else []
        phones = [self._normalize_phone(participant.phone)] if participant.phone else []
        
        platform_identities = {
            participant.platform: participant.platform_user_id
        }
        
        # Create contact
        contact = Contact(
            canonical_name=participant.name or "Unknown",
            emails=emails if emails else None,
            phones=phones if phones else None,
            platform_identities=platform_identities,
            contact_metadata={}
        )
        
        self.session.add(contact)
        await self.session.flush()  # Get the ID
        
        # Emit contact created event
        await self._emit_contact_event(
            EventType.CONTACT_CREATED,
            contact
        )
        
        logger.info(
            f"Created new contact {contact.id} from participant {participant.id} "
            f"(platform={participant.platform}, name={participant.name})"
        )
        
        return contact
    
    async def _link_participant_to_contact(
        self,
        participant: Participant,
        contact: Contact
    ) -> None:
        """
        Link a participant to a contact.
        
        Updates the participant's contact_id and merges contact information.
        
        Args:
            participant: Participant to link
            contact: Contact to link to
        """
        # Update participant
        participant.contact_id = contact.id
        
        # Merge participant information into contact
        await self._merge_participant_info(contact, participant)
        
        await self.session.flush()
        
        # Emit contact matched event
        await self._emit_contact_event(
            EventType.CONTACT_MATCHED,
            contact,
            extra_data={
                "participant_id": str(participant.id),
                "platform": participant.platform
            }
        )
        
        logger.info(
            f"Linked participant {participant.id} to contact {contact.id}"
        )
    
    async def _merge_participant_info(
        self,
        contact: Contact,
        participant: Participant
    ) -> None:
        """
        Merge participant information into contact.
        
        Updates contact's emails, phones, and platform identities.
        
        Args:
            contact: Contact to update
            participant: Participant with new information
        """
        updated = False
        
        # Add email if not present
        if participant.email:
            normalized_email = participant.email.lower().strip()
            if not contact.emails:
                contact.emails = []
            if normalized_email not in contact.emails:
                contact.emails.append(normalized_email)
                updated = True
        
        # Add phone if not present
        if participant.phone:
            normalized_phone = self._normalize_phone(participant.phone)
            if not contact.phones:
                contact.phones = []
            if normalized_phone not in contact.phones:
                contact.phones.append(normalized_phone)
                updated = True
        
        # Add platform identity
        if not contact.platform_identities:
            contact.platform_identities = {}
        
        if participant.platform not in contact.platform_identities:
            contact.platform_identities[participant.platform] = participant.platform_user_id
            updated = True
        
        if updated:
            # Mark as modified for SQLAlchemy to detect changes
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(contact, "emails")
            flag_modified(contact, "phones")
            flag_modified(contact, "platform_identities")
    
    async def match_all_unmatched_participants(
        self,
        platform: Optional[str] = None,
        limit: int = 100
    ) -> int:
        """
        Match all unmatched participants to contacts.
        
        Args:
            platform: Optional platform filter
            limit: Maximum number of participants to process
        
        Returns:
            Number of participants matched
        """
        # Find unmatched participants
        stmt = select(Participant).where(Participant.contact_id.is_(None))
        
        if platform:
            stmt = stmt.where(Participant.platform == platform)
        
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        participants = result.scalars().all()
        
        matched_count = 0
        
        for participant in participants:
            try:
                contact, confidence = await self.match_participant(
                    participant,
                    auto_create=True
                )
                
                if contact:
                    matched_count += 1
                    
            except Exception as e:
                logger.error(
                    f"Failed to match participant {participant.id}: {e}"
                )
                continue
        
        await self.session.commit()
        
        logger.info(
            f"Matched {matched_count} of {len(participants)} unmatched participants"
        )
        
        return matched_count
    
    async def get_potential_matches(
        self,
        participant: Participant,
        min_confidence: float = 0.5
    ) -> List[Tuple[Contact, float]]:
        """
        Get potential contact matches for a participant.
        
        Returns all contacts that match with confidence >= min_confidence.
        
        Args:
            participant: Participant to find matches for
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of (Contact, confidence) tuples
        """
        matches = []
        
        # Try email matching
        if participant.email:
            contact, confidence = await self._match_by_email(participant.email)
            if contact and confidence >= min_confidence:
                matches.append((contact, confidence))
        
        # Try phone matching
        if participant.phone:
            contact, confidence = await self._match_by_phone(participant.phone)
            if contact and confidence >= min_confidence:
                # Check if already in matches
                if not any(c.id == contact.id for c, _ in matches):
                    matches.append((contact, confidence))
        
        # Try name matching
        if participant.name:
            contact, confidence = await self._match_by_name(participant.name)
            if contact and confidence >= min_confidence:
                # Check if already in matches
                if not any(c.id == contact.id for c, _ in matches):
                    matches.append((contact, confidence))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
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
                source="contact_matcher",
                payload=payload
            )
            
            await self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to emit contact event: {e}")
            # Don't raise - event emission failure shouldn't break the operation


# Export public API
__all__ = [
    "ContactMatcher",
]
