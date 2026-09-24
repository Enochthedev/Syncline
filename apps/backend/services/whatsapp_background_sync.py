"""
WhatsApp Background Sync Service

Provides background message synchronization for real-time updates.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.platform_connection import (
    ConnectionStatus,
    PlatformConnection,
    PlatformType,
)
from db.session import get_db
from services.event_bus import get_event_bus
from services.events.types import EventType
from services.whatsapp_message_sync import get_whatsapp_sync_service

logger = logging.getLogger(__name__)


class WhatsAppBackgroundSyncService:
    """Background sync service for WhatsApp messages."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._sync_tasks: Dict[UUID, asyncio.Task] = {}
        self._running = False

    async def start_background_sync(self, sync_interval: int = 300) -> None:
        """
        Start background sync for all active WhatsApp connections.

        Args:
            sync_interval: Sync interval in seconds (default: 5 minutes)
        """
        if self._running:
            self.logger.warning("Background sync already running")
            return

        self._running = True
        self.logger.info(
            f"Starting WhatsApp background sync (interval: {sync_interval}s)"
        )

        # Start the main sync loop
        asyncio.create_task(self._sync_loop(sync_interval))

    async def stop_background_sync(self) -> None:
        """Stop background sync and cleanup tasks."""
        self._running = False

        # Cancel all sync tasks
        for connection_id, task in self._sync_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._sync_tasks.clear()
        self.logger.info("Background sync stopped")

    async def _sync_loop(self, interval: int) -> None:
        """Main sync loop that runs periodically."""
        while self._running:
            try:
                await self._sync_all_active_connections()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"Background sync error: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    async def _sync_all_active_connections(self) -> None:
        """Sync messages for all active WhatsApp connections."""
        async for db in get_db():
            try:
                # Get all active WhatsApp connections
                result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.platform == PlatformType.WHATSAPP,
                        PlatformConnection.status == ConnectionStatus.ACTIVE,
                    )
                )
                connections = result.scalars().all()

                self.logger.info(
                    f"Found {len(connections)} active WhatsApp connections"
                )

                # Sync each connection
                for connection in connections:
                    if self._should_sync_connection(connection):
                        await self._sync_connection(db, connection)

            except Exception as e:
                self.logger.error(f"Failed to sync active connections: {e}")

            break  # Exit the async generator

    def _should_sync_connection(self, connection: PlatformConnection) -> bool:
        """Check if connection should be synced."""
        # Skip if no credentials
        if not connection.credentials:
            return False

        # Skip if synced recently (within last 2 minutes)
        if connection.last_sync_at:
            time_since_sync = datetime.utcnow() - connection.last_sync_at
            if time_since_sync < timedelta(minutes=2):
                return False

        return True

    async def _sync_connection(
        self, db: AsyncSession, connection: PlatformConnection
    ) -> None:
        """Sync messages for a specific connection."""
        try:
            sync_service = get_whatsapp_sync_service()

            # Sync messages (limit to recent messages for background sync)
            result = await sync_service.sync_messages_for_connection(
                db, connection.id, limit=20
            )

            if result["success"]:
                # Update last sync time
                connection.last_sync_at = datetime.utcnow()
                await db.commit()

                # Publish sync event if messages were synced
                if result["total_messages_synced"] > 0:
                    event_bus = get_event_bus()
                    await event_bus.publish_event(
                        EventType.MESSAGE_SYNC_COMPLETED,
                        {
                            "connection_id": str(connection.id),
                            "platform": "whatsapp",
                            "messages_synced": result["total_messages_synced"],
                            "rooms_synced": result["total_rooms"],
                        },
                    )

                    self.logger.info(
                        f"Synced {result['total_messages_synced']} messages "
                        f"for connection {connection.id}"
                    )
            else:
                self.logger.error(
                    f"Sync failed for connection {connection.id}: "
                    f"{result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Failed to sync connection {connection.id}: {e}")

    async def sync_connection_now(self, connection_id: UUID) -> Dict[str, any]:
        """Manually trigger sync for a specific connection."""
        async for db in get_db():
            try:
                # Get connection
                result = await db.execute(
                    select(PlatformConnection).where(
                        PlatformConnection.id == connection_id
                    )
                )
                connection = result.scalar_one_or_none()

                if not connection:
                    return {"success": False, "error": "Connection not found"}

                # Sync messages
                await self._sync_connection(db, connection)

                return {"success": True, "message": "Sync completed"}

            except Exception as e:
                self.logger.error(f"Manual sync failed: {e}")
                return {"success": False, "error": str(e)}

            break

    def get_sync_status(self) -> Dict[str, any]:
        """Get current sync status."""
        return {
            "running": self._running,
            "active_tasks": len(self._sync_tasks),
            "task_status": {
                str(conn_id): not task.done()
                for conn_id, task in self._sync_tasks.items()
            },
        }


# Global service instance
_background_sync_service = None


def get_whatsapp_background_sync_service() -> WhatsAppBackgroundSyncService:
    """Get WhatsApp background sync service instance."""
    global _background_sync_service
    if _background_sync_service is None:
        _background_sync_service = WhatsAppBackgroundSyncService()
    return _background_sync_service
