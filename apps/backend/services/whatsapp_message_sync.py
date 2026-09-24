"""
WhatsApp Message Sync Service

Syncs messages from Matrix bridge to unified database schema.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.message import Message
from db.models.participant import Participant
from db.models.platform_connection import PlatformConnection
from db.models.raw_message import RawMessage
from integrations.whatsapp_connector import MatrixMessage, WhatsAppConnector

logger = logging.getLogger(__name__)


class WhatsAppMessageSyncService:
    """Service for syncing WhatsApp messages from Matrix to database."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def sync_messages_for_connection(
        self, db: AsyncSession, connection_id: UUID, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Sync messages for a specific WhatsApp connection.

        Args:
            db: Database session
            connection_id: WhatsApp connection ID
            limit: Maximum messages to sync per room

        Returns:
            Sync results
        """
        try:
            # Get connection
            result = await db.execute(
                select(PlatformConnection).where(PlatformConnection.id == connection_id)
            )
            connection = result.scalar_one_or_none()

            if not connection:
                return {"success": False, "error": "Connection not found"}

            # Create connector
            connector = WhatsAppConnector(
                connection_id=connection.id, credentials=connection.credentials
            )

            await connector.connect()

            try:
                # Get all WhatsApp rooms
                rooms = await connector.get_rooms()
                self.logger.info(f"Found {len(rooms)} WhatsApp rooms to sync")

                total_synced = 0
                room_results = []

                for room_info in rooms:
                    room_id = room_info["room_id"]

                    try:
                        # Fetch messages from this room
                        matrix_messages = await connector.fetch_messages(room_id, limit)

                        # Sync messages to database
                        synced_count = await self._sync_room_messages(
                            db, connection, room_id, matrix_messages
                        )

                        total_synced += synced_count
                        room_results.append(
                            {
                                "room_id": room_id,
                                "messages_found": len(matrix_messages),
                                "messages_synced": synced_count,
                            }
                        )

                        self.logger.info(
                            f"Synced {synced_count}/{len(matrix_messages)} messages from room {room_id}"
                        )

                    except Exception as e:
                        self.logger.error(f"Failed to sync room {room_id}: {e}")
                        room_results.append({"room_id": room_id, "error": str(e)})

                await db.commit()

                return {
                    "success": True,
                    "total_rooms": len(rooms),
                    "total_messages_synced": total_synced,
                    "room_results": room_results,
                }

            finally:
                await connector.disconnect()

        except Exception as e:
            self.logger.error(f"Message sync failed: {e}")
            return {"success": False, "error": str(e)}

    async def _sync_room_messages(
        self,
        db: AsyncSession,
        connection: PlatformConnection,
        room_id: str,
        matrix_messages: List[Dict[str, Any]],
    ) -> int:
        """
        Sync messages from a specific room.

        Args:
            db: Database session
            connection: Platform connection
            room_id: Matrix room ID
            matrix_messages: List of Matrix message events

        Returns:
            Number of messages synced
        """
        synced_count = 0

        for msg_event in matrix_messages:
            try:
                # Parse Matrix message
                client = WhatsAppConnector(
                    connection.id, connection.credentials
                )._get_client()
                matrix_msg = client.parse_matrix_message(msg_event)

                if not matrix_msg:
                    continue

                # Check if message already exists
                existing = await self._find_existing_message(
                    db, connection.id, matrix_msg.event_id
                )
                if existing:
                    continue

                # Create raw message
                raw_message = await self._create_raw_message(
                    db, connection, matrix_msg, msg_event
                )

                # Create normalized message
                await self._create_normalized_message(
                    db, connection, raw_message, matrix_msg, room_id
                )

                synced_count += 1

            except Exception as e:
                self.logger.error(
                    f"Failed to sync message {msg_event.get('event_id', 'unknown')}: {e}"
                )
                continue

        return synced_count

    async def _find_existing_message(
        self, db: AsyncSession, connection_id: UUID, event_id: str
    ) -> Optional[Message]:
        """Check if message already exists in database."""
        result = await db.execute(
            select(Message).where(
                Message.connection_id == connection_id,
                Message.platform_message_id == event_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_raw_message(
        self,
        db: AsyncSession,
        connection: PlatformConnection,
        matrix_msg: MatrixMessage,
        raw_event: Dict[str, Any],
    ) -> RawMessage:
        """Create raw message record."""
        raw_message = RawMessage(
            id=uuid4(),
            connection_id=connection.id,
            platform="whatsapp",
            platform_message_id=matrix_msg.event_id,
            raw_data=raw_event,
            processed=True,
        )

        db.add(raw_message)
        await db.flush()
        return raw_message

    async def _create_normalized_message(
        self,
        db: AsyncSession,
        connection: PlatformConnection,
        raw_message: RawMessage,
        matrix_msg: MatrixMessage,
        room_id: str,
    ) -> Message:
        """Create normalized message record."""
        # Get or create sender participant
        sender = await self._get_or_create_participant(
            db, connection, matrix_msg.sender
        )

        # Create normalized message
        message = Message(
            id=uuid4(),
            connection_id=connection.id,
            raw_message_id=raw_message.id,
            platform="whatsapp",
            platform_message_id=matrix_msg.event_id,
            thread_id=room_id,
            sender_id=sender.id if sender else None,
            content={"text": matrix_msg.content, "format": "plain"},
            message_metadata={
                "matrix_room_id": room_id,
                "matrix_sender": matrix_msg.sender,
                "msg_type": matrix_msg.msg_type,
                "whatsapp_id": matrix_msg.whatsapp_id,
                "reply_to": matrix_msg.reply_to,
                "media_url": matrix_msg.media_url,
                "media_type": matrix_msg.media_type,
            },
            timestamp=matrix_msg.timestamp,
            collected_at=datetime.utcnow(),
            cleaned_at=datetime.utcnow(),
        )

        db.add(message)
        await db.flush()
        return message

    async def _get_or_create_participant(
        self, db: AsyncSession, connection: PlatformConnection, matrix_sender: str
    ) -> Optional[Participant]:
        """Get or create participant for message sender."""
        try:
            # Check if participant exists
            result = await db.execute(
                select(Participant).where(
                    Participant.platform == "whatsapp",
                    Participant.platform_user_id == matrix_sender,
                )
            )
            participant = result.scalar_one_or_none()

            if participant:
                return participant

            # Create new participant
            participant = Participant(
                id=uuid4(),
                platform="whatsapp",
                platform_user_id=matrix_sender,
                name=matrix_sender,
                participant_metadata={
                    "matrix_user_id": matrix_sender,
                    "connection_id": str(connection.id),
                },
            )

            db.add(participant)
            await db.flush()
            return participant

        except Exception as e:
            self.logger.error(
                f"Failed to get/create participant for {matrix_sender}: {e}"
            )
            return None


# Global service instance
_sync_service = None


def get_whatsapp_sync_service() -> WhatsAppMessageSyncService:
    """Get WhatsApp message sync service instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = WhatsAppMessageSyncService()
    return _sync_service
