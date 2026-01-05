"""
Chat API Endpoints

Provides live chat functionality:
- List active chat threads
- Get messages for specific chats
- Link chats to contacts
- Send new messages
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session, get_optional_current_user
from db.models.user import User
from services.chat_manager import (
    get_chat_manager_service,
    ChatThread,
    ChatMessage,
    ChatManagerService
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class LinkChatRequest(BaseModel):
    """Request to link chat to contact."""
    
    contact_id: UUID = Field(..., description="Contact ID to link to")


class LinkChatResponse(BaseModel):
    """Response for chat linking."""
    
    success: bool = Field(..., description="Whether linking succeeded")
    message: str = Field(..., description="Status message")


class SendMessageRequest(BaseModel):
    """Request to send a new message."""
    
    content: str = Field(..., min_length=1, description="Message content")
    reply_to: Optional[UUID] = Field(None, description="Message ID to reply to")


class SendMessageResponse(BaseModel):
    """Response for sending message."""
    
    success: bool = Field(..., description="Whether message was sent")
    message_id: Optional[UUID] = Field(None, description="Sent message ID")
    message: str = Field(..., description="Status message")


class ChatThreadsResponse(BaseModel):
    """Response for chat threads list."""
    
    threads: List[ChatThread] = Field(..., description="List of chat threads")
    total: int = Field(..., description="Total number of threads")


class ChatMessagesResponse(BaseModel):
    """Response for chat messages."""
    
    messages: List[ChatMessage] = Field(..., description="List of messages")
    thread_id: str = Field(..., description="Thread ID")
    platform: str = Field(..., description="Platform")
    has_more: bool = Field(default=False, description="Whether more messages available")


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.get(
    "/threads",
    response_model=ChatThreadsResponse,
    summary="Get Chat Threads",
    description="Get active chat threads for the current user"
)
async def get_chat_threads(
    db: AsyncSession = Depends(get_database_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=100, description="Maximum threads to return"),
) -> ChatThreadsResponse:
    """
    Get active chat threads for the current user.
    
    Returns live chat threads grouped by conversation, with contact linking
    where available.
    
    Args:
        db: Database session
        current_user: Current authenticated user (optional)
        platform: Optional platform filter
        limit: Maximum threads to return
        
    Returns:
        ChatThreadsResponse: List of active chat threads
    """
    try:
        # For now, use a default user ID if no auth
        user_id = current_user.id if current_user else UUID("00000000-0000-0000-0000-000000000001")
        
        chat_service = get_chat_manager_service()
        
        threads = await chat_service.get_chat_threads(
            db=db,
            user_id=user_id,
            platform=platform,
            limit=limit
        )
        
        logger.info(f"Retrieved {len(threads)} chat threads for user {user_id}")
        
        return ChatThreadsResponse(
            threads=threads,
            total=len(threads)
        )
        
    except Exception as e:
        logger.error(f"Failed to get chat threads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat threads: {str(e)}"
        )


@router.get(
    "/threads/{thread_id}/messages",
    response_model=ChatMessagesResponse,
    summary="Get Chat Messages",
    description="Get messages for a specific chat thread"
)
async def get_chat_messages(
    thread_id: str,
    platform: str = Query(..., description="Platform of the thread"),
    db: AsyncSession = Depends(get_database_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
    limit: int = Query(50, ge=1, le=100, description="Maximum messages to return"),
    before: Optional[datetime] = Query(None, description="Get messages before this timestamp"),
) -> ChatMessagesResponse:
    """
    Get messages for a specific chat thread.
    
    Args:
        thread_id: Thread ID
        platform: Platform name
        db: Database session
        current_user: Current authenticated user (optional)
        limit: Maximum messages to return
        before: Get messages before this timestamp (for pagination)
        
    Returns:
        ChatMessagesResponse: List of messages in the thread
    """
    try:
        # For now, use a default user ID if no auth
        user_id = current_user.id if current_user else UUID("00000000-0000-0000-0000-000000000001")
        
        chat_service = get_chat_manager_service()
        
        messages = await chat_service.get_chat_messages(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            platform=platform,
            limit=limit,
            before_timestamp=before
        )
        
        logger.info(f"Retrieved {len(messages)} messages for thread {thread_id}")
        
        return ChatMessagesResponse(
            messages=messages,
            thread_id=thread_id,
            platform=platform,
            has_more=len(messages) == limit  # Simple heuristic
        )
        
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat messages: {str(e)}"
        )


@router.post(
    "/threads/{thread_id}/link",
    response_model=LinkChatResponse,
    summary="Link Chat to Contact",
    description="Link a chat thread to a specific contact"
)
async def link_chat_to_contact(
    thread_id: str,
    platform: str = Query(..., description="Platform of the thread"),
    request: LinkChatRequest = ...,
    db: AsyncSession = Depends(get_database_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> LinkChatResponse:
    """
    Link a chat thread to a specific contact.
    
    This allows for unified contact management across platforms.
    
    Args:
        thread_id: Thread ID to link
        platform: Platform name
        request: Link request with contact ID
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        LinkChatResponse: Link operation result
    """
    try:
        # For now, use a default user ID if no auth
        user_id = current_user.id if current_user else UUID("00000000-0000-0000-0000-000000000001")
        
        chat_service = get_chat_manager_service()
        
        success = await chat_service.link_chat_to_contact(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            platform=platform,
            contact_id=request.contact_id
        )
        
        if success:
            return LinkChatResponse(
                success=True,
                message=f"Successfully linked chat {thread_id} to contact"
            )
        else:
            return LinkChatResponse(
                success=False,
                message="Failed to link chat to contact"
            )
        
    except Exception as e:
        logger.error(f"Failed to link chat to contact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link chat: {str(e)}"
        )


@router.post(
    "/threads/{thread_id}/messages",
    response_model=SendMessageResponse,
    summary="Send Message",
    description="Send a new message to a chat thread"
)
async def send_message(
    thread_id: str,
    platform: str = Query(..., description="Platform to send message on"),
    request: SendMessageRequest = ...,
    db: AsyncSession = Depends(get_database_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> SendMessageResponse:
    """
    Send a new message to a chat thread.
    
    Args:
        thread_id: Thread ID to send message to (this is the Matrix room_id for WhatsApp)
        platform: Platform to send on
        request: Message content and options
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        SendMessageResponse: Send operation result
    """
    from sqlalchemy import select
    from db.models.connection import PlatformConnection, PlatformType, ConnectionStatus
    from integrations.whatsapp_connector import WhatsAppConnector
    
    try:
        # For now, use a default user ID if no auth
        user_id = current_user.id if current_user else UUID("00000000-0000-0000-0000-000000000001")
        
        logger.info(f"Send message request for thread {thread_id} on {platform}")
        
        # Normalize platform name
        platform_upper = platform.upper()
        
        # Currently only WhatsApp is supported for sending
        if platform_upper != "WHATSAPP":
            return SendMessageResponse(
                success=False,
                message_id=None,
                message=f"Sending messages via {platform} is not yet supported. Only WhatsApp is available."
            )
        
        # Get user's active WhatsApp connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == PlatformType.WHATSAPP,
                PlatformConnection.status == ConnectionStatus.ACTIVE
            )
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            return SendMessageResponse(
                success=False,
                message_id=None,
                message="No active WhatsApp connection found. Please connect WhatsApp first."
            )
        
        # Initialize WhatsApp connector
        connector = WhatsAppConnector(
            user_id=str(user_id),
            connection_id=str(connection.id),
            credentials=connection.credentials or {}
        )
        
        # thread_id is the Matrix room_id for WhatsApp chats
        room_id = thread_id
        
        # Send message via connector
        event_id = await connector.send_message(
            room_id=room_id,
            content=request.content
        )
        
        logger.info(f"Message sent to room {room_id}: event_id={event_id}")
        
        return SendMessageResponse(
            success=True,
            message_id=None,  # We don't have a UUID, just the Matrix event ID
            message=f"Message sent successfully (event: {event_id})"
        )
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.post(
    "/cleanup/{platform}",
    summary="Cleanup Bot Messages",
    description="Remove bot welcome messages for a platform"
)
async def cleanup_bot_messages(
    platform: str,
    db: AsyncSession = Depends(get_database_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> Dict[str, Any]:
    """
    Clean up bot messages for a platform.
    
    Removes bot welcome messages and management room clutter
    to show only real conversations.
    
    Args:
        platform: Platform to clean up (e.g., 'whatsapp')
        db: Database session
        current_user: Current authenticated user (optional)
        
    Returns:
        Cleanup results
    """
    try:
        # For now, use a default user ID if no auth
        user_id = current_user.id if current_user else UUID("00000000-0000-0000-0000-000000000001")
        
        chat_service = get_chat_manager_service()
        
        cleanup_result = await chat_service.cleanup_bot_messages(
            db=db,
            user_id=user_id,
            platform=platform.upper()
        )
        
        logger.info(f"Cleaned up {cleanup_result.get('deleted_messages', 0)} bot messages for platform {platform}")
        
        return {
            "platform": platform,
            "cleanup_result": cleanup_result,
            "message": f"Cleaned up {cleanup_result.get('deleted_messages', 0)} bot messages"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup bot messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup messages: {str(e)}"
        )


# =============================================================================
# Export router
# =============================================================================

__all__ = ["router"]