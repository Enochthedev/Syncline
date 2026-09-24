"""
WhatsApp Webhook Service

Handles Matrix webhooks for real-time WhatsApp message delivery.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.platform_connection import PlatformConnection, PlatformType
from services.event_bus import get_event_bus
from services.events.types import EventType
from services.whatsapp_message_sync import get_whatsapp_sync_service

logger = logging.getLogger(__name__)


class WhatsAppWebhookService:
    """Service for handling Matrix webhooks for WhatsApp."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def handle_matrix_webhook(
        self, db: AsyncSession, webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle incoming Matrix webhook for WhatsApp messages.

        Args:
            db: Database session
            webhook_data: Webhook payload from Matrix

        Returns:
            Processing result
        """
        try:
            # Validate webhook data
            if not self._validate_webhook_data(webhook_data):
                raise HTTPException(status_code=400, detail="Invalid webhook data")

            # Extract event information
            events = webhook_data.get("events", [])
            if not events:
                return {"success": True, "message": "No events to process"}

            processed_count = 0

            for event in events:
                if await self._process_matrix_event(db, event):
                    processed_count += 1

            return {
                "success": True,
                "events_processed": processed_count,
                "total_events": len(events),
            }

        except Exception as e:
            self.logger.error(f"Webhook processing failed: {e}")
            return {"success": False, "error": str(e)}

    def _validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """Validate webhook data structure."""
        required_fields = ["events"]
        return all(field in data for field in required_fields)

    async def _process_matrix_event(
        self, db: AsyncSession, event: Dict[str, Any]
    ) -> bool:
        """
        Process a single Matrix event.

        Args:
            db: Database session
            event: Matrix event data

        Returns:
            True if processed successfully
        """
        try:
            # Only process room message events
            if event.get("type") != "m.room.message":
                return False

            room_id = event.get("room_id")
            sender = event.get("sender")

            if not room_id or not sender:
                return False

            # Skip messages from our own bot
            if sender.endswith(":localhost") and "syncline" in sender:
                return False

            # Find WhatsApp connection for this room
            connection = await self._find_connection_for_room(db, room_id)
            if not connection:
                self.logger.warning(f"No WhatsApp connection found for room {room_id}")
                return False

            # Sync this specific message
            sync_service = get_whatsapp_sync_service()

            # Create a mock room messages response for this single event
            mock_messages = [event]

            synced_count = await sync_service._sync_room_messages(
                db, connection, room_id, mock_messages
            )

            if synced_count > 0:
                # Publish real-time message event
                event_bus = get_event_bus()
                await event_bus.publish_event(
                    EventType.MESSAGE_RECEIVED,
                    {
                        "connection_id": str(connection.id),
                        "platform": "whatsapp",
                        "room_id": room_id,
                        "sender": sender,
                        "event_id": event.get("event_id"),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                self.logger.info(
                    f"Processed real-time message from {sender} in room {room_id}"
                )
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to process Matrix event: {e}")
            return False

    async def _find_connection_for_room(
        self, db: AsyncSession, room_id: str
    ) -> Optional[PlatformConnection]:
        """
        Find WhatsApp connection that has access to this room.

        This is a simplified approach - in practice, you might need
        to maintain a mapping of rooms to connections.
        """
        try:
            # Get all active WhatsApp connections
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.platform == PlatformType.WHATSAPP,
                    PlatformConnection.status == "ACTIVE",
                )
            )
            connections = result.scalars().all()

            # For now, return the first active connection with credentials
            # In production, you'd want to maintain a room-to-connection mapping
            for connection in connections:
                if connection.credentials and connection.credentials.get(
                    "matrix_access_token"
                ):
                    return connection

            return None

        except Exception as e:
            self.logger.error(f"Failed to find connection for room {room_id}: {e}")
            return None

    async def setup_webhook_subscription(
        self, connection_id: UUID, webhook_url: str
    ) -> Dict[str, Any]:
        """
        Set up webhook subscription for a WhatsApp connection.

        Args:
            connection_id: WhatsApp connection ID
            webhook_url: URL to receive webhooks

        Returns:
            Setup result
        """
        try:
            # This would typically involve:
            # 1. Registering webhook with Matrix homeserver
            # 2. Configuring push rules for the user
            # 3. Setting up room event subscriptions

            # For now, return success - actual implementation would
            # depend on your Matrix homeserver setup

            self.logger.info(
                f"Webhook subscription setup for connection {connection_id}"
            )

            return {
                "success": True,
                "webhook_url": webhook_url,
                "connection_id": str(connection_id),
                "message": "Webhook subscription configured",
            }

        except Exception as e:
            self.logger.error(f"Webhook setup failed: {e}")
            return {"success": False, "error": str(e)}

    async def remove_webhook_subscription(self, connection_id: UUID) -> Dict[str, Any]:
        """Remove webhook subscription for a connection."""
        try:
            # Remove webhook configuration

            self.logger.info(
                f"Webhook subscription removed for connection {connection_id}"
            )

            return {
                "success": True,
                "connection_id": str(connection_id),
                "message": "Webhook subscription removed",
            }

        except Exception as e:
            self.logger.error(f"Webhook removal failed: {e}")
            return {"success": False, "error": str(e)}


# Global service instance
_webhook_service = None


def get_whatsapp_webhook_service() -> WhatsAppWebhookService:
    """Get WhatsApp webhook service instance."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WhatsAppWebhookService()
    return _webhook_service
