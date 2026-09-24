#!/usr/bin/env python3
"""
WhatsApp Session Cleanup Script

Cleans up WhatsApp sessions, messages, and connection data to start fresh.
This helps resolve login/logout issues by clearing stale session data.
"""

import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.contact import Contact
from db.models.message import Message
from db.models.participant import Participant
from db.models.platform_connection import PlatformConnection, PlatformType
from db.models.raw_message import RawMessage
from db.session import get_db

logger = logging.getLogger(__name__)


async def cleanup_whatsapp_data(db: AsyncSession, connection_id: UUID = None) -> dict:
    """
    Clean up WhatsApp data for fresh start.

    Args:
        db: Database session
        connection_id: Specific connection to clean (optional)

    Returns:
        Cleanup statistics
    """
    stats = {
        "messages_deleted": 0,
        "raw_messages_deleted": 0,
        "participants_deleted": 0,
        "contacts_updated": 0,
        "connections_reset": 0,
    }

    try:
        # Build base query for WhatsApp platform
        if connection_id:
            # Clean specific connection
            connection_filter = PlatformConnection.id == connection_id
        else:
            # Clean all WhatsApp connections
            connection_filter = PlatformConnection.platform == PlatformType.WHATSAPP

        # Get WhatsApp connections
        conn_result = await db.execute(
            select(PlatformConnection).where(connection_filter)
        )
        connections = conn_result.scalars().all()

        for conn in connections:
            print(f"Cleaning connection {conn.id} for user {conn.user_id}")

            # Delete messages
            msg_result = await db.execute(
                delete(Message).where(Message.connection_id == conn.id)
            )
            stats["messages_deleted"] += msg_result.rowcount

            # Delete raw messages
            raw_result = await db.execute(
                delete(RawMessage).where(RawMessage.connection_id == conn.id)
            )
            stats["raw_messages_deleted"] += raw_result.rowcount

            # Delete WhatsApp participants
            part_result = await db.execute(
                delete(Participant).where(Participant.platform == "WHATSAPP")
            )
            stats["participants_deleted"] += part_result.rowcount

            # Reset connection credentials (clear session data)
            conn.credentials = {
                "matrix_homeserver_url": settings.MATRIX_HOMESERVER_URL,
                "matrix_access_token": settings.MATRIX_ACCESS_TOKEN,
                "matrix_user_id": settings.MATRIX_USER_ID,
                "bridge_bot_id": settings.WHATSAPP_BRIDGE_BOT_ID,
            }
            conn.is_active = False
            conn.last_sync_at = None
            stats["connections_reset"] += 1

        await db.commit()
        print(f"✅ Cleanup completed: {stats}")
        return stats

    except Exception as e:
        await db.rollback()
        print(f"❌ Cleanup failed: {e}")
        raise


async def reset_whatsapp_bridge_session():
    """
    Reset WhatsApp bridge session by sending logout command.
    This clears any stale bridge-side session data.
    """
    try:
        from integrations.whatsapp_connector import WhatsAppConnector

        # Create temporary connector with default credentials
        connector = WhatsAppConnector(
            connection_id=UUID("00000000-0000-0000-0000-000000000001"),
            credentials={
                "matrix_homeserver_url": settings.MATRIX_HOMESERVER_URL,
                "matrix_access_token": settings.MATRIX_ACCESS_TOKEN,
                "matrix_user_id": settings.MATRIX_USER_ID,
                "bridge_bot_id": settings.WHATSAPP_BRIDGE_BOT_ID,
            },
        )

        await connector.connect()

        # Send logout to clear any existing session
        print("🔄 Sending logout command to bridge...")
        logout_result = await connector.logout()
        print(f"Bridge logout result: {logout_result}")

        # Check status after logout
        status = await connector.get_bridge_status()
        print(f"Bridge status after logout: {status}")

        await connector.disconnect()

        return True

    except Exception as e:
        print(f"⚠️ Bridge reset failed (this is often normal): {e}")
        return False


async def main():
    """Main cleanup function."""
    print("🧹 Starting WhatsApp session cleanup...")

    # Clean database
    async for db in get_db():
        stats = await cleanup_whatsapp_data(db)
        break

    # Reset bridge session
    await reset_whatsapp_bridge_session()

    print("\n✅ WhatsApp cleanup completed!")
    print("You can now set up fresh WhatsApp login.")

    return 0


if __name__ == "__main__":
    asyncio.run(main())
