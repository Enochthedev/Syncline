"""
WebSocket message handlers for different types of real-time operations.

This module contains handlers for:
- Authentication
- Search streaming
- Conversation updates
- Nudge delivery
- System notifications
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .types import (
    WebSocketMessage,
    WebSocketMessageType,
    AuthRequest,
    SearchStreamRequest,
    ConversationUpdate,
    NudgeDelivery,
    SystemNotification,
    AuthenticationError
)
from .manager import WebSocketManager
from .search_handler import SearchStreamHandler
from .event_handler import EventHandler

logger = logging.getLogger(__name__)


class WebSocketHandlers:
    """
    WebSocket message handlers for real-time operations.

    Provides handlers for authentication, search streaming, conversation updates,
    and proactive nudge delivery.
    """

    def __init__(self, manager: WebSocketManager):
        """Initialize WebSocket handlers."""
        self.manager = manager
        self.search_handler = SearchStreamHandler(manager)
        self.event_handler = EventHandler(manager)

        # Register handlers
        self._register_handlers()

        logger.info("WebSocketHandlers initialized")

    def _register_handlers(self) -> None:
        """Register all message handlers."""
        handlers = {
            WebSocketMessageType.PING: self._handle_ping,
            WebSocketMessageType.AUTH_REQUEST: self._handle_auth_request,
            WebSocketMessageType.SEARCH_START: self.search_handler.handle_search_start,
            WebSocketMessageType.NUDGE_ACKNOWLEDGED: self._handle_nudge_acknowledged,
        }

        for message_type, handler in handlers.items():
            self.manager.register_handler(message_type, handler)

    async def _handle_ping(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle ping message."""
        await self.manager._send_to_connection(
            connection_id,
            WebSocketMessage(
                type=WebSocketMessageType.PONG,
                data={"timestamp": datetime.utcnow().isoformat()},
                correlation_id=message.correlation_id
            )
        )

    async def _handle_auth_request(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle authentication request."""
        try:
            auth_data = AuthRequest(**message.data)

            success = await self.manager.authenticate(
                connection_id=connection_id,
                user_id=auth_data.user_id or "anonymous",
                token=auth_data.token
            )

            if success:
                # Subscribe to user-specific channels
                user_id = auth_data.user_id or "anonymous"
                await self.manager.subscribe(connection_id, f"user:{user_id}")
                await self.manager.subscribe(connection_id, f"nudges:{user_id}")

                logger.info(f"User {user_id} authenticated and subscribed")

        except Exception as e:
            logger.error(f"Authentication error for {connection_id}: {e}")
            await self.manager._send_error(
                connection_id,
                f"Authentication failed: {str(e)}",
                "AUTH_ERROR"
            )

    async def _handle_nudge_acknowledged(self, connection_id: str, message: WebSocketMessage) -> None:
        """Handle nudge acknowledgment."""
        try:
            nudge_id = message.data.get("nudge_id")
            if not nudge_id:
                raise ValueError("Missing nudge_id")

            # TODO: Update nudge status in database
            logger.info(f"Nudge {nudge_id} acknowledged by {connection_id}")

            # Send confirmation
            await self.manager._send_to_connection(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.SYSTEM_NOTIFICATION,
                    data={
                        "level": "success",
                        "title": "Nudge Acknowledged",
                        "message": "Thank you for acknowledging the nudge.",
                        "auto_dismiss": True
                    },
                    correlation_id=message.correlation_id
                )
            )

        except Exception as e:
            logger.error(
                f"Nudge acknowledgment error for {connection_id}: {e}")

    async def send_conversation_update(self, update: ConversationUpdate) -> int:
        """Send conversation update to relevant subscribers."""
        return await self.event_handler.send_conversation_update(update)

    async def send_nudge_to_user(self, user_id: str, nudge_delivery: NudgeDelivery) -> int:
        """Send proactive nudge to a specific user."""
        return await self.event_handler.send_nudge_to_user(user_id, nudge_delivery)

    async def send_system_notification(
        self,
        notification: SystemNotification,
        target_users: Optional[List[str]] = None,
        target_subscriptions: Optional[List[str]] = None
    ) -> int:
        """Send system notification to users or subscribers."""
        return await self.event_handler.send_system_notification(
            notification, target_users, target_subscriptions
        )

    async def start_event_listeners(self) -> None:
        """Start listening to event bus for real-time updates."""
        await self.event_handler.start_event_listeners()

    async def cleanup_connection(self, connection_id: str) -> None:
        """Clean up resources for a disconnected connection."""
        await self.search_handler.cleanup_connection(connection_id)

    def get_active_searches(self) -> Dict[str, str]:
        """Get information about active searches."""
        return self.search_handler.get_active_searches()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on WebSocket handlers."""
        try:
            search_health = await self.search_handler.health_check()
            event_health = await self.event_handler.health_check()

            return {
                "status": "healthy",
                "search_handler": search_health,
                "event_handler": event_health,
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
