"""
Chat Manager Service

Manages chat threads, contact linking, and live message synchronization.
Provides unified chat view across all platforms.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from db.models.message import Message
from db.models.thread import Thread
from db.models.contact import Contact
from db.models.participant import Participant
from db.models.platform_connection import PlatformConnection

logger = logging.getLogger(__name__)


class ChatThread(BaseModel):
    """Unified chat thread representation."""
    
    id: str = Field(..., description="Thread ID")
    platform: str = Field(..., description="Platform name")
    contact_id: Optional[UUID] = Field(None, description="Linked contact ID")
    contact_name: Optional[str] = Field(None, description="Contact display name")
    phone_number: Optional[str] = Field(None, description="Phone number if available")
    last_message: Optional[str] = Field(None, description="Last message preview")
    last_message_time: Optional[datetime] = Field(None, description="Last message timestamp")
    unread_count: int = Field(default=0, description="Unread message count")
    platform_metadata: Optional[Dict] = Field(None, description="Platform-specific data")
    is_linked: bool = Field(default=False, description="Whether linked to a contact")


class ChatMessage(BaseModel):
    """Chat message for live view."""
    
    id: UUID = Field(..., description="Message ID")
    thread_id: str = Field(..., description="Thread ID")
    platform: str = Field(..., description="Platform")
    sender_name: str = Field(..., description="Sender display name")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    is_from_me: bool = Field(default=False, description="Whether sent by current user")
    has_attachments: bool = Field(default=False, description="Has attachments")


class ChatManagerService:
    """Service for managing chat threads and live messaging."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_chat_threads(
        self,
        db: AsyncSession,
        user_id: UUID,
        platform: Optional[str] = None,
        limit: int = 50
    ) -> List[ChatThread]:
        """
        Get active chat threads for user.
        
        Groups messages by thread_id and shows as live chats.
        Links to contacts where possible.
        """
        try:
            # Build query - get all messages if no user authentication
            query = (
                select(Message)
                .options(
                    selectinload(Message.sender),
                    selectinload(Message.connection)
                )
                .order_by(desc(Message.timestamp))
            )
            
            # Only filter by user if we have a real user (not default UUID)
            if user_id != UUID("00000000-0000-0000-0000-000000000001"):
                query = query.join(PlatformConnection).where(PlatformConnection.user_id == user_id)
            
            if platform:
                # Handle both uppercase and lowercase platform names
                platform_filter = platform.upper() if isinstance(platform, str) else platform
                query = query.where(Message.platform == platform_filter)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            # Group messages by thread_id or create thread from sender info
            thread_map = {}
            
            for msg in messages:
                # Skip bot welcome messages - these aren't real chats
                if (msg.message_metadata and 
                    msg.message_metadata.get("sender_matrix_id") == "@whatsappbot:localhost" and
                    "Hello, I'm a WhatsApp bridge bot" in (msg.content.get("text", "") if msg.content else "")):
                    continue
                
                # Skip management room messages (login commands, status checks, etc.)
                if (msg.message_metadata and 
                    msg.message_metadata.get("sender_matrix_id") == "@syncline:localhost"):
                    # Skip common management commands
                    message_text = msg.content.get("text", "") if msg.content else ""
                    if message_text.lower() in ["login qr", "login", "help", "status", "sync", "logout"]:
                        continue
                
                # Skip messages that are clearly not real WhatsApp conversations
                if msg.message_metadata:
                    sender_matrix_id = msg.message_metadata.get("sender_matrix_id", "")
                    # Only include messages from actual WhatsApp users (format: @whatsapp_PHONENUMBER:domain)
                    if not sender_matrix_id.startswith("@whatsapp_"):
                        continue
                
                # Create thread ID - use thread_id if available, otherwise create from platform + sender
                thread_id = msg.thread_id
                if not thread_id:
                    # Create thread ID from sender info
                    sender_info = msg.message_metadata.get("sender_matrix_id", "") if msg.message_metadata else ""
                    if sender_info:
                        thread_id = f"{msg.platform}_{sender_info.replace('@', '').replace(':', '_')}"
                    else:
                        thread_id = f"{msg.platform}_{msg.platform_message_id}"
                
                if thread_id not in thread_map:
                    # Try to link to contact
                    contact = await self._find_linked_contact(db, msg, user_id)
                    
                    # Extract sender info
                    sender_name = "Unknown"
                    phone_number = None
                    
                    if msg.message_metadata:
                        sender_name = msg.message_metadata.get("sender_name", sender_name)
                        phone_number = msg.message_metadata.get("sender_phone")
                        
                        # Try to extract phone from Matrix ID if not in metadata
                        if not phone_number:
                            sender_matrix_id = msg.message_metadata.get("sender_matrix_id", "")
                            if "@whatsapp_" in sender_matrix_id:
                                # Extract phone number from Matrix ID (e.g., @whatsapp_1234567890:localhost)
                                phone_match = sender_matrix_id.split("@whatsapp_")[1].split(":")[0]
                                if phone_match and phone_match.isdigit():
                                    phone_number = f"+{phone_match}"
                                    # Create readable name from phone if no name available
                                    if sender_name == "Unknown":
                                        sender_name = f"WhatsApp +{phone_match}"
                    
                    if contact:
                        sender_name = contact.canonical_name
                        if contact.phones:
                            phone_number = contact.phones[0]
                    
                    # Create thread
                    thread = ChatThread(
                        id=thread_id,
                        platform=msg.platform.lower(),  # Convert to lowercase for frontend
                        contact_id=contact.id if contact else None,
                        contact_name=sender_name,
                        phone_number=phone_number,
                        last_message=msg.content.get("text", "")[:100] if msg.content else "",
                        last_message_time=msg.timestamp,
                        unread_count=0,  # TODO: Implement read tracking
                        platform_metadata=msg.message_metadata,
                        is_linked=contact is not None
                    )
                    
                    thread_map[thread_id] = thread
                else:
                    # Update with newer message if this is more recent
                    existing_thread = thread_map[thread_id]
                    if msg.timestamp > existing_thread.last_message_time:
                        existing_thread.last_message = msg.content.get("text", "")[:100] if msg.content else ""
                        existing_thread.last_message_time = msg.timestamp
            
            threads = list(thread_map.values())
            
            # Sort by last message time
            threads.sort(key=lambda t: t.last_message_time or datetime.min, reverse=True)
            
            # Limit results
            threads = threads[:limit]
            
            self.logger.info(f"Retrieved {len(threads)} chat threads for user {user_id}")
            return threads
            
        except Exception as e:
            self.logger.error(f"Failed to get chat threads: {e}")
            return []
    
    async def get_chat_messages(
        self,
        db: AsyncSession,
        user_id: UUID,
        thread_id: str,
        platform: str,
        limit: int = 50,
        before_timestamp: Optional[datetime] = None
    ) -> List[ChatMessage]:
        """Get messages for a specific chat thread."""
        try:
            # Build query - handle both thread_id and constructed thread IDs
            query = (
                select(Message)
                .where(Message.platform == platform.upper())  # Always use uppercase for DB
                .options(
                    selectinload(Message.sender),
                    selectinload(Message.attachments)
                )
                .order_by(desc(Message.timestamp))
                .limit(limit)
            )
            
            # Only filter by user if we have a real user (not default UUID)
            if user_id != UUID("00000000-0000-0000-0000-000000000001"):
                query = query.join(PlatformConnection).where(PlatformConnection.user_id == user_id)
            
            # Handle thread_id matching - either exact match or constructed from sender
            if thread_id.startswith(f"{platform}_"):
                # This is a constructed thread ID, match by sender info
                sender_part = thread_id.replace(f"{platform}_", "").replace("_", ":")
                if not sender_part.startswith("@"):
                    sender_part = f"@{sender_part}"
                
                query = query.where(
                    or_(
                        Message.thread_id == thread_id,
                        Message.message_metadata["sender_matrix_id"].astext == sender_part
                    )
                )
            else:
                # Direct thread_id match
                query = query.where(Message.thread_id == thread_id)
            
            if before_timestamp:
                query = query.where(Message.timestamp < before_timestamp)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            chat_messages = []
            for msg in messages:
                # Extract sender name
                sender_name = "Unknown"
                if msg.message_metadata:
                    sender_name = msg.message_metadata.get("sender_name", sender_name)
                
                if msg.sender:
                    sender_name = msg.sender.name or sender_name
                
                # Check if from current user (basic heuristic)
                is_from_me = False
                if msg.message_metadata:
                    sender_matrix_id = msg.message_metadata.get("sender_matrix_id", "")
                    # TODO: Better logic to detect own messages
                    is_from_me = "bot" in sender_matrix_id.lower()
                
                chat_msg = ChatMessage(
                    id=msg.id,
                    thread_id=thread_id,
                    platform=msg.platform.lower(),  # Convert to lowercase for frontend
                    sender_name=sender_name,
                    content=msg.content.get("text", "") if msg.content else "",
                    timestamp=msg.timestamp,
                    is_from_me=is_from_me,
                    has_attachments=len(msg.attachments) > 0 if msg.attachments else False
                )
                
                chat_messages.append(chat_msg)
            
            # Reverse to show chronological order
            chat_messages.reverse()
            
            self.logger.info(f"Retrieved {len(chat_messages)} messages for thread {thread_id}")
            return chat_messages
            
        except Exception as e:
            self.logger.error(f"Failed to get chat messages: {e}")
            return []
    
    async def link_chat_to_contact(
        self,
        db: AsyncSession,
        user_id: UUID,
        thread_id: str,
        platform: str,
        contact_id: UUID
    ) -> bool:
        """Link a chat thread to a specific contact."""
        try:
            # Verify contact belongs to user
            contact_query = select(Contact).where(
                and_(Contact.id == contact_id, Contact.user_id == user_id)
            )
            result = await db.execute(contact_query)
            contact = result.scalar_one_or_none()
            
            if not contact:
                self.logger.error(f"Contact {contact_id} not found for user {user_id}")
                return False
            
            # Update all messages in this thread to link to contact's participant
            # First, find or create participant for this contact
            participant_query = select(Participant).where(
                and_(
                    Participant.contact_id == contact_id,
                    Participant.platform == platform
                )
            )
            result = await db.execute(participant_query)
            participant = result.scalar_one_or_none()
            
            if not participant:
                # Create participant
                participant = Participant(
                    id=uuid4(),
                    contact_id=contact_id,
                    platform=platform,
                    platform_user_id=f"{platform}_{thread_id}",
                    name=contact.canonical_name
                )
                db.add(participant)
                await db.flush()
            
            # Update messages in thread
            update_query = (
                select(Message)
                .join(PlatformConnection)
                .where(
                    and_(
                        PlatformConnection.user_id == user_id,
                        Message.thread_id == thread_id,
                        Message.platform == platform
                    )
                )
            )
            
            result = await db.execute(update_query)
            messages = result.scalars().all()
            
            for msg in messages:
                msg.sender_id = participant.id
            
            await db.commit()
            
            self.logger.info(f"Linked thread {thread_id} to contact {contact_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to link chat to contact: {e}")
            await db.rollback()
            return False
    
    async def _find_linked_contact(
        self,
        db: AsyncSession,
        message: Message,
        user_id: UUID
    ) -> Optional[Contact]:
        """Try to find a linked contact for a message."""
        try:
            # First check if message has linked sender
            if message.sender and message.sender.contact_id:
                contact_query = select(Contact).where(Contact.id == message.sender.contact_id)
                result = await db.execute(contact_query)
                return result.scalar_one_or_none()
            
            # Try to match by phone number from metadata
            if message.message_metadata:
                phone = message.message_metadata.get("sender_phone")
                if phone:
                    contact_query = select(Contact).where(
                        and_(
                            Contact.user_id == user_id,
                            Contact.phones.contains([phone])
                        )
                    )
                    result = await db.execute(contact_query)
                    return result.scalar_one_or_none()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find linked contact: {e}")
            return None


    async def cleanup_bot_messages(
        self,
        db: AsyncSession,
        user_id: UUID,
        platform: str = "WHATSAPP"
    ) -> Dict[str, int]:
        """
        Clean up bot welcome messages and management room messages.
        
        Args:
            db: Database session
            user_id: User ID
            platform: Platform to clean up
            
        Returns:
            Cleanup statistics
        """
        try:
            # Find bot messages to delete
            bot_message_query = (
                select(Message)
                .join(PlatformConnection)
                .where(
                    and_(
                        PlatformConnection.user_id == user_id,
                        Message.platform == platform,
                        or_(
                            # Bot welcome messages
                            and_(
                                Message.message_metadata["sender_matrix_id"].astext == "@whatsappbot:localhost",
                                Message.content["text"].astext.like("%Hello, I'm a WhatsApp bridge bot%")
                            ),
                            # Management room messages (login commands, etc.)
                            and_(
                                Message.message_metadata["sender_matrix_id"].astext == "@syncline:localhost",
                                Message.content["text"].astext.in_(["login qr", "login", "help", "status"])
                            )
                        )
                    )
                )
            )
            
            result = await db.execute(bot_message_query)
            bot_messages = result.scalars().all()
            
            deleted_count = 0
            for msg in bot_messages:
                await db.delete(msg)
                deleted_count += 1
            
            await db.commit()
            
            self.logger.info(f"Cleaned up {deleted_count} bot messages for user {user_id}")
            
            return {
                "deleted_messages": deleted_count,
                "platform": platform
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Failed to cleanup bot messages: {e}")
            return {
                "deleted_messages": 0,
                "platform": platform,
                "error": str(e)
            }


# Global service instance
_chat_manager_service = None

def get_chat_manager_service() -> ChatManagerService:
    """Get chat manager service instance."""
    global _chat_manager_service
    if _chat_manager_service is None:
        _chat_manager_service = ChatManagerService()
    return _chat_manager_service