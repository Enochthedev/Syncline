"""
Thread Grouper Service

This module provides functionality for grouping messages into conversation threads
and associating them with contacts.

Features:
- Group messages by platform thread ID
- Create and update thread records
- Associate threads with contacts
- Track thread participants
- Emit thread lifecycle events
"""

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.contact import Contact
from db.models.message import Message
from db.models.participant import Participant
from db.models.thread import Thread
from services.event_bus import get_event_bus
from services.events.types import EventType, ThreadEvent

logger = logging.getLogger(__name__)


class ThreadGrouper:
    """
    Service for grouping messages into conversation threads.
    
    Handles:
    - Thread creation and updates
    - Message-to-thread association
    - Contact-to-thread linking
    - Participant tracking
    - Thread statistics
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the thread grouper.
        
        Args:
            session: Database session
        """
        self.session = session
        self.event_bus = get_event_bus()
    
    async def group_message(
        self,
        message: Message,
        contact_id: UUID | None = None
    ) -> Thread:
        """
        Group a message into its thread, creating the thread if necessary.
        
        Args:
            message: Message to group
            contact_id: Optional contact ID to associate with thread
        
        Returns:
            Thread instance
        """
        if not message.thread_id:
            logger.warning(
                f"Message {message.id} has no thread_id, cannot group"
            )
            raise ValueError("Message must have a thread_id to be grouped")
        
        # Find or create thread
        thread = await self._find_or_create_thread(
            platform=message.platform,
            platform_thread_id=message.thread_id,
            contact_id=contact_id
        )
        
        # Update thread statistics
        await self._update_thread_stats(thread, message)
        
        # Track participants
        if message.sender_id:
            await self._add_participant_to_thread(thread, message.sender_id)
        
        # Add recipients as participants
        recipients = message.message_metadata.get("recipients", []) if message.message_metadata else []
        for recipient in recipients:
            if isinstance(recipient, dict) and "participant_id" in recipient:
                await self._add_participant_to_thread(
                    thread,
                    UUID(recipient["participant_id"])
                )
        
        await self.session.commit()
        
        logger.info(
            f"Grouped message {message.id} into thread {thread.id} "
            f"(platform={thread.platform}, thread_id={thread.platform_thread_id})"
        )
        
        return thread
    
    async def _find_or_create_thread(
        self,
        platform: str,
        platform_thread_id: str,
        contact_id: UUID | None = None
    ) -> Thread:
        """
        Find an existing thread or create a new one.
        
        Args:
            platform: Platform name
            platform_thread_id: Platform-specific thread identifier
            contact_id: Optional contact ID
        
        Returns:
            Thread instance
        """
        # Try to find existing thread
        stmt = select(Thread).where(
            Thread.platform == platform,
            Thread.platform_thread_id == platform_thread_id
        )
        result = await self.session.execute(stmt)
        thread = result.scalar_one_or_none()
        
        if thread:
            # Update contact if provided and different
            if contact_id and thread.contact_id != contact_id:
                thread.contact_id = contact_id
                thread.updated_at = datetime.utcnow()
                
                # Emit thread updated event
                await self._emit_thread_event(
                    EventType.THREAD_UPDATED,
                    thread
                )
            
            return thread
        
        # Create new thread
        thread = Thread(
            platform=platform,
            platform_thread_id=platform_thread_id,
            contact_id=contact_id,
            participant_ids=[],
            message_count=0
        )
        
        self.session.add(thread)
        await self.session.flush()  # Get the ID
        
        # Emit thread created event
        await self._emit_thread_event(
            EventType.THREAD_CREATED,
            thread
        )
        
        logger.info(
            f"Created new thread {thread.id} "
            f"(platform={platform}, thread_id={platform_thread_id})"
        )
        
        return thread
    
    async def _update_thread_stats(
        self,
        thread: Thread,
        message: Message
    ) -> None:
        """
        Update thread statistics based on a new message.
        
        Args:
            thread: Thread to update
            message: New message
        """
        # Increment message count
        thread.message_count += 1
        
        # Update first message timestamp
        if not thread.first_message_at or message.timestamp < thread.first_message_at:
            thread.first_message_at = message.timestamp
        
        # Update last message timestamp
        if not thread.last_message_at or message.timestamp > thread.last_message_at:
            thread.last_message_at = message.timestamp
        
        # Update title if not set and message has subject
        if not thread.title and message.message_metadata:
            subject = message.message_metadata.get("subject")
            if subject:
                thread.title = subject[:500]  # Limit to 500 chars
        
        thread.updated_at = datetime.utcnow()
    
    async def _add_participant_to_thread(
        self,
        thread: Thread,
        participant_id: UUID
    ) -> None:
        """
        Add a participant to the thread's participant list.
        
        Args:
            thread: Thread to update
            participant_id: Participant UUID
        """
        if not thread.participant_ids:
            thread.participant_ids = []
        
        # Add participant if not already in list
        if participant_id not in thread.participant_ids:
            thread.participant_ids.append(participant_id)
            thread.updated_at = datetime.utcnow()
    
    async def associate_thread_with_contact(
        self,
        thread_id: UUID,
        contact_id: UUID
    ) -> Thread:
        """
        Associate a thread with a contact.
        
        Args:
            thread_id: Thread UUID
            contact_id: Contact UUID
        
        Returns:
            Updated thread
        """
        # Get thread
        stmt = select(Thread).where(Thread.id == thread_id)
        result = await self.session.execute(stmt)
        thread = result.scalar_one_or_none()
        
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")
        
        # Verify contact exists
        contact_stmt = select(Contact).where(Contact.id == contact_id)
        contact_result = await self.session.execute(contact_stmt)
        contact = contact_result.scalar_one_or_none()
        
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Update thread
        thread.contact_id = contact_id
        thread.updated_at = datetime.utcnow()
        
        await self.session.commit()
        
        # Emit thread updated event
        await self._emit_thread_event(
            EventType.THREAD_UPDATED,
            thread
        )
        
        logger.info(
            f"Associated thread {thread_id} with contact {contact_id}"
        )
        
        return thread
    
    async def get_thread_participants(
        self,
        thread_id: UUID
    ) -> List[Participant]:
        """
        Get all participants in a thread.
        
        Args:
            thread_id: Thread UUID
        
        Returns:
            List of Participant instances
        """
        # Get thread
        stmt = select(Thread).where(Thread.id == thread_id)
        result = await self.session.execute(stmt)
        thread = result.scalar_one_or_none()
        
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")
        
        if not thread.participant_ids:
            return []
        
        # Get participants
        participant_stmt = select(Participant).where(
            Participant.id.in_(thread.participant_ids)
        )
        participant_result = await self.session.execute(participant_stmt)
        participants = participant_result.scalars().all()
        
        return list(participants)
    
    async def get_thread_by_platform_id(
        self,
        platform: str,
        platform_thread_id: str
    ) -> Thread | None:
        """
        Get a thread by platform and platform thread ID.
        
        Args:
            platform: Platform name
            platform_thread_id: Platform-specific thread identifier
        
        Returns:
            Thread instance or None
        """
        stmt = select(Thread).where(
            Thread.platform == platform,
            Thread.platform_thread_id == platform_thread_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_threads_for_contact(
        self,
        contact_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Thread]:
        """
        Get all threads associated with a contact.
        
        Args:
            contact_id: Contact UUID
            limit: Maximum number of threads to return
            offset: Number of threads to skip
        
        Returns:
            List of Thread instances
        """
        stmt = (
            select(Thread)
            .where(Thread.contact_id == contact_id)
            .order_by(Thread.last_message_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def recalculate_thread_stats(
        self,
        thread_id: UUID
    ) -> Thread:
        """
        Recalculate thread statistics from messages.
        
        Useful for fixing inconsistencies or after bulk operations.
        
        Args:
            thread_id: Thread UUID
        
        Returns:
            Updated thread
        """
        # Get thread
        stmt = select(Thread).where(Thread.id == thread_id)
        result = await self.session.execute(stmt)
        thread = result.scalar_one_or_none()
        
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")
        
        # Get messages for this thread
        message_stmt = select(Message).where(
            Message.platform == thread.platform,
            Message.thread_id == thread.platform_thread_id
        )
        message_result = await self.session.execute(message_stmt)
        messages = list(message_result.scalars().all())
        
        if not messages:
            # No messages, reset stats
            thread.message_count = 0
            thread.first_message_at = None
            thread.last_message_at = None
            thread.participant_ids = []
        else:
            # Recalculate stats
            thread.message_count = len(messages)
            thread.first_message_at = min(msg.timestamp for msg in messages)
            thread.last_message_at = max(msg.timestamp for msg in messages)
            
            # Collect unique participants
            participant_ids = set()
            for msg in messages:
                if msg.sender_id:
                    participant_ids.add(msg.sender_id)
                
                # Add recipients
                if msg.message_metadata:
                    recipients = msg.message_metadata.get("recipients", [])
                    for recipient in recipients:
                        if isinstance(recipient, dict) and "participant_id" in recipient:
                            participant_ids.add(UUID(recipient["participant_id"]))
            
            thread.participant_ids = list(participant_ids)
            
            # Update title from first message if available
            if not thread.title:
                first_msg = min(messages, key=lambda m: m.timestamp)
                if first_msg.message_metadata:
                    subject = first_msg.message_metadata.get("subject")
                    if subject:
                        thread.title = subject[:500]
        
        thread.updated_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(
            f"Recalculated stats for thread {thread_id}: "
            f"{thread.message_count} messages, "
            f"{len(thread.participant_ids or [])} participants"
        )
        
        return thread
    
    async def _emit_thread_event(
        self,
        event_type: EventType,
        thread: Thread
    ) -> None:
        """
        Emit a thread lifecycle event.
        
        Args:
            event_type: Type of event
            thread: Thread instance
        """
        try:
            event = ThreadEvent(
                event_id=str(UUID(int=0)),  # Will be replaced by event bus
                event_type=event_type,
                source="thread_grouper",
                payload={
                    "thread_id": str(thread.id),
                    "platform": thread.platform,
                    "platform_thread_id": thread.platform_thread_id,
                    "contact_id": str(thread.contact_id) if thread.contact_id else None,
                    "participant_ids": [str(pid) for pid in (thread.participant_ids or [])],
                    "message_count": thread.message_count,
                    "title": thread.title,
                }
            )
            
            await self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to emit thread event: {e}")
            # Don't raise - event emission failure shouldn't break the operation


# Export public API
__all__ = [
    "ThreadGrouper",
]
