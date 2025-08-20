"""
WebSocket event handler for real-time notifications and updates.

Handles conversation updates, nudge delivery, and system notifications.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from services.ai.memory.agent import ProactiveMemoryAgent
from services.event_bus import get_event_bus, Event, EventType, ConsumerConfig

from .types import (
    WebSocketMessage,
    WebSocketMessageType,
    ConversationUpdate,
    NudgeDelivery,
    SystemNotification
)
from .manager import WebSocketManager

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Handles WebSocket events for real-time notifications.

    Provides conversation updates, nudge delivery, and system notifications.
    """

    def __init__(self, manager: WebSocketManager):
        """Initialize event handler."""
        self.manager = manager
        self.memory_agent = ProactiveMemoryAgent()

        logger.info("EventHandler initialized")

    async def send_conversation_update(self, update: ConversationUpdate) -> int:
        """
        Send conversation update to relevant subscribers.

        Args:
            update: Conversation update to send

        Returns:
            Number of connections the update was sent to
        """
        try:
            message = WebSocketMessage(
                type=WebSocketMessageType.MESSAGE_RECEIVED if update.update_type == "message_received"
                else WebSocketMessageType.THREAD_UPDATED,
                data=update.model_dump()
            )

            # Send to thread subscribers
            thread_subscription = f"thread:{update.thread_id}"
            sent_count = await self.manager.send_to_subscription(thread_subscription, message)

            # Send to platform subscribers
            platform_subscription = f"platform:{update.platform}"
            sent_count += await self.manager.send_to_subscription(platform_subscription, message)

            logger.debug(
                f"Sent conversation update to {sent_count} connections")
            return sent_count

        except Exception as e:
            logger.error(f"Error sending conversation update: {e}")
            return 0

    async def send_nudge_to_user(self, user_id: str, nudge_delivery: NudgeDelivery) -> int:
        """
        Send proactive nudge to a specific user.

        Args:
            user_id: User ID to send nudge to
            nudge_delivery: Nudge delivery data

        Returns:
            Number of connections the nudge was sent to
        """
        try:
            message = WebSocketMessage(
                type=WebSocketMessageType.NUDGE_DELIVERY,
                data=nudge_delivery.model_dump(),
                user_id=user_id
            )

            sent_count = await self.manager.send_to_user(user_id, message)

            logger.info(
                f"Sent nudge to user {user_id}: {sent_count} connections")
            return sent_count

        except Exception as e:
            logger.error(f"Error sending nudge to user {user_id}: {e}")
            return 0

    async def send_system_notification(
        self,
        notification: SystemNotification,
        target_users: Optional[List[str]] = None,
        target_subscriptions: Optional[List[str]] = None
    ) -> int:
        """
        Send system notification to users or subscribers.

        Args:
            notification: System notification to send
            target_users: Optional list of user IDs to send to
            target_subscriptions: Optional list of subscriptions to send to

        Returns:
            Number of connections the notification was sent to
        """
        try:
            message = WebSocketMessage(
                type=WebSocketMessageType.SYSTEM_NOTIFICATION,
                data=notification.model_dump()
            )

            sent_count = 0

            # Send to specific users
            if target_users:
                for user_id in target_users:
                    sent_count += await self.manager.send_to_user(user_id, message)

            # Send to specific subscriptions
            if target_subscriptions:
                for subscription in target_subscriptions:
                    sent_count += await self.manager.send_to_subscription(subscription, message)

            # If no targets specified, broadcast to all authenticated connections
            if not target_users and not target_subscriptions:
                sent_count = await self.manager.broadcast(message, authenticated_only=True)

            logger.info(
                f"Sent system notification to {sent_count} connections")
            return sent_count

        except Exception as e:
            logger.error(f"Error sending system notification: {e}")
            return 0

    async def start_event_listeners(self) -> None:
        """Start listening to event bus for real-time updates."""
        try:
            event_bus = await get_event_bus()

            # Message events
            message_config = ConsumerConfig(
                group_name="websocket_message_updates",
                consumer_name="websocket_handler",
                stream_name="message_events"
            )

            await event_bus.subscribe(message_config, self._handle_message_event)

            # Nudge events
            nudge_config = ConsumerConfig(
                group_name="websocket_nudge_delivery",
                consumer_name="websocket_handler",
                stream_name="nudge_events"
            )

            await event_bus.subscribe(nudge_config, self._handle_nudge_event)

            logger.info("WebSocket event listeners started")

        except Exception as e:
            logger.error(f"Error starting event listeners: {e}")

    async def _handle_message_event(self, event: Event) -> None:
        """Handle message-related events from the event bus."""
        try:
            if event.type == EventType.MESSAGE_RECEIVED:
                # Create conversation update
                update = ConversationUpdate(
                    update_type="message_received",
                    thread_id=event.data.get("thread_id", ""),
                    message_id=event.data.get("message_id"),
                    platform=event.data.get("platform", ""),
                    content_preview=event.data.get("content_preview"),
                    metadata=event.data
                )

                await self.send_conversation_update(update)

            elif event.type == EventType.THREAD_UPDATED:
                # Create thread update
                update = ConversationUpdate(
                    update_type="thread_updated",
                    thread_id=event.data.get("thread_id", ""),
                    platform=event.data.get("platform", ""),
                    metadata=event.data
                )

                await self.send_conversation_update(update)

        except Exception as e:
            logger.error(f"Error handling message event: {e}")

    async def _handle_nudge_event(self, event: Event) -> None:
        """Handle nudge-related events from the event bus."""
        try:
            if event.type.value == "nudge.generated":  # Custom event type
                user_id = event.data.get("user_id")
                nudge_data = event.data.get("nudge")

                if user_id and nudge_data:
                    # Create nudge delivery
                    from services.ai.memory.types import Nudge
                    nudge = Nudge(**nudge_data)

                    nudge_delivery = NudgeDelivery(
                        nudge=nudge,
                        delivery_context=event.data.get("context", {}),
                        requires_acknowledgment=True
                    )

                    await self.send_nudge_to_user(user_id, nudge_delivery)

        except Exception as e:
            logger.error(f"Error handling nudge event: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on event handler."""
        try:
            return {
                "status": "healthy",
                "memory_agent_ready": True,
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
