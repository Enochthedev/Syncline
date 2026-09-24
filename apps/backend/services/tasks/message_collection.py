"""
Message Collection Background Tasks

Periodic tasks for collecting messages from all connected platforms.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.contact import Contact
from db.models.message import Message
from db.models.platform_connection import ConnectionStatus, PlatformConnection
from db.models.raw_message import RawMessage
from db.session import get_session

logger = logging.getLogger(__name__)


# =============================================================================
# Collection Task
# =============================================================================


async def collect_whatsapp_messages(
    connection_id: UUID,
    db: AsyncSession,
    limit: int = 50,
) -> dict:
    """
    Collect messages from a single WhatsApp connection.

    Returns:
        Dict with collection stats
    """
    from uuid import uuid4

    from config.config import settings
    from integrations.whatsapp_connector import WhatsAppConnector

    # settings = get_settings() # settings is imported directly

    # Get connection
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.platform == "WHATSAPP",
            PlatformConnection.status == ConnectionStatus.ACTIVE,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return {"error": "Connection not found or not active"}

    stats = {
        "messages_collected": 0,
        "contacts_created": 0,
        "errors": 0,
        "connection_id": str(connection_id),
    }

    try:
        # Create connector
        connector = WhatsAppConnector(
            connection_id=connection_id,
            credentials={
                "matrix_homeserver_url": settings.MATRIX_HOMESERVER_URL,
                "matrix_access_token": settings.MATRIX_ACCESS_TOKEN,
                "matrix_user_id": settings.MATRIX_USER_ID,
                "bridge_bot_id": settings.WHATSAPP_BRIDGE_BOT_ID,
            },
        )

        await connector.connect()

        # Get messages
        messages = await connector.list_messages(limit=limit)

        for msg in messages:
            try:
                # Skip if exists
                existing = await db.execute(
                    select(Message).where(Message.platform_message_id == msg.event_id)
                )
                if existing.scalar_one_or_none():
                    continue

                # Extract phone from sender
                phone = None
                if "@whatsapp_" in msg.sender:
                    phone_match = msg.sender.split("@whatsapp_")[1].split(":")[0]
                    if phone_match:
                        phone = f"+{phone_match}"

                # Find/create contact
                contact = None
                sender_name = msg.sender
                if phone:
                    result = await db.execute(
                        select(Contact).where(Contact.user_id == connection.user_id)
                    )
                    for c in result.scalars().all():
                        if c.phones and phone in c.phones:
                            contact = c
                            sender_name = c.canonical_name
                            break

                    if not contact:
                        contact = Contact(
                            id=uuid4(),
                            user_id=connection.user_id,
                            canonical_name=phone,
                            phones=[phone],
                            platform_identities={"whatsapp": phone},
                        )
                        db.add(contact)
                        stats["contacts_created"] += 1

                # Create raw message
                raw_msg = RawMessage(
                    id=uuid4(),
                    connection_id=connection_id,
                    platform="WHATSAPP",
                    platform_message_id=msg.event_id,
                    raw_data={
                        "event_id": msg.event_id,
                        "room_id": msg.room_id,
                        "sender": msg.sender,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    },
                    processed=True,
                )
                db.add(raw_msg)

                # Create message with sender info
                normalized_msg = Message(
                    id=uuid4(),
                    connection_id=connection_id,
                    raw_message_id=raw_msg.id,
                    platform="WHATSAPP",
                    platform_message_id=msg.event_id,
                    thread_id=msg.room_id,
                    content={
                        "text": msg.content,
                        "format": "plain",
                    },
                    message_metadata={
                        "matrix_room_id": msg.room_id,
                        "sender_phone": phone,
                        "sender_name": sender_name,
                        "has_media": msg.media_url is not None,
                    },
                    timestamp=msg.timestamp,
                    collected_at=datetime.utcnow(),
                    cleaned_at=datetime.utcnow(),
                )
                db.add(normalized_msg)
                stats["messages_collected"] += 1

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                stats["errors"] += 1

        await db.commit()

        # Update last_sync_at
        connection.last_sync_at = datetime.utcnow()
        await db.commit()

        await connector.disconnect()

    except Exception as e:
        logger.error(f"Failed to collect from connection {connection_id}: {e}")
        stats["error"] = str(e)

    return stats


async def run_collection_cycle():
    """
    Run a collection cycle for all active connections.

    Should be called periodically (e.g., every 30 seconds).
    """
    logger.info("Starting message collection cycle")

    async with get_session() as db:
        try:
            # Get all active WhatsApp connections
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.platform == "WHATSAPP",
                    PlatformConnection.status == ConnectionStatus.ACTIVE,
                )
            )
            connections = result.scalars().all()

            logger.info(f"Found {len(connections)} active WhatsApp connections")

            total_stats = {
                "connections_processed": 0,
                "messages_collected": 0,
                "contacts_created": 0,
                "errors": 0,
            }

            for connection in connections:
                stats = await collect_whatsapp_messages(connection.id, db)
                total_stats["connections_processed"] += 1
                total_stats["messages_collected"] += stats.get("messages_collected", 0)
                total_stats["contacts_created"] += stats.get("contacts_created", 0)
                total_stats["errors"] += stats.get("errors", 0)

            logger.info(f"Collection cycle complete: {total_stats}")
            return total_stats

        except Exception as e:
            logger.error(f"Collection cycle failed: {e}")
            raise


# =============================================================================
# Background Worker
# =============================================================================

_collection_task: Optional[asyncio.Task] = None
_running = False


async def _collection_worker(interval_seconds: int = 30):
    """Background worker that runs collection periodically."""
    global _running
    _running = True

    logger.info(f"Message collection worker started (interval: {interval_seconds}s)")

    while _running:
        try:
            await run_collection_cycle()
        except Exception as e:
            logger.error(f"Collection worker error: {e}")

        await asyncio.sleep(interval_seconds)

    logger.info("Message collection worker stopped")


def start_collection_worker(interval_seconds: int = 30):
    """Start the background collection worker."""
    global _collection_task

    if _collection_task and not _collection_task.done():
        logger.warning("Collection worker already running")
        return

    _collection_task = asyncio.create_task(_collection_worker(interval_seconds))
    logger.info("Collection worker task created")


def stop_collection_worker():
    """Stop the background collection worker."""
    global _running, _collection_task

    _running = False

    if _collection_task:
        _collection_task.cancel()
        _collection_task = None

    logger.info("Collection worker stopped")


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "collect_whatsapp_messages",
    "run_collection_cycle",
    "start_collection_worker",
    "stop_collection_worker",
]
