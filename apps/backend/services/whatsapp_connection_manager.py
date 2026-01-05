"""
WhatsApp Connection Manager

Manages WhatsApp connections and prevents duplicate connections.
Handles connection detection and reuse for mobile app.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from db.models.platform_connection import PlatformConnection, PlatformType, ConnectionStatus
from integrations.whatsapp_connector import WhatsAppConnector
from services.connector_cache import get_connector_cache

logger = logging.getLogger(__name__)


class WhatsAppConnectionManager:
    """Manages WhatsApp connections and prevents duplicates."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def _batch_test_connections(
        self,
        connections: List[PlatformConnection]
    ) -> Dict[UUID, Dict[str, Any]]:
        """
        Test multiple connections in parallel to avoid N+1 query pattern.

        Args:
            connections: List of connections to test

        Returns:
            Dictionary mapping connection_id to status info
        """
        async def test_single(conn: PlatformConnection) -> Tuple[UUID, Dict[str, Any]]:
            """Test a single connection and return (connection_id, status)."""
            status = await self._test_connection(conn)
            return (conn.id, status)

        # Run all tests in parallel using asyncio.gather
        results = await asyncio.gather(
            *[test_single(conn) for conn in connections],
            return_exceptions=True
        )

        # Build result dictionary, handling any exceptions
        status_map = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # If test failed, mark as not logged in
                self.logger.warning(f"Batch test failed for connection {connections[i].id}: {result}")
                status_map[connections[i].id] = {
                    "is_logged_in": False,
                    "phone": None,
                    "connected": False
                }
            else:
                conn_id, status = result
                status_map[conn_id] = status

        return status_map

    async def get_or_create_connection(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get existing active WhatsApp connection or create new one.

        This prevents the mobile app from creating multiple connections.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Connection info with status
        """
        try:
            # First, check for existing active connections
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == PlatformType.WHATSAPP,
                    PlatformConnection.status == ConnectionStatus.ACTIVE
                )
            )
            active_connections = result.scalars().all()

            # Filter connections with valid credentials
            valid_active_connections = [
                conn for conn in active_connections
                if self._has_valid_credentials(conn)
            ]

            # Batch test all valid active connections in parallel (fixes N+1 problem)
            if valid_active_connections:
                status_map = await self._batch_test_connections(valid_active_connections)

                # Check if any connection is actually logged in
                for conn in valid_active_connections:
                    status = status_map.get(conn.id, {})

                    if status.get("is_logged_in"):
                        self.logger.info(f"Found existing active connection: {conn.id}")
                        return {
                            "connection_id": str(conn.id),
                            "is_existing": True,
                            "is_logged_in": True,
                            "phone": status.get("phone"),
                            "message": "Using existing WhatsApp connection"
                        }
                    else:
                        # Connection exists but not logged in - mark as inactive
                        await self._update_connection_status(db, conn.id, ConnectionStatus.INACTIVE)
            
            # Check for recent inactive connections with credentials (can be reactivated)
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == PlatformType.WHATSAPP,
                    PlatformConnection.status == ConnectionStatus.INACTIVE
                ).order_by(PlatformConnection.created_at.desc())
            )
            inactive_connections = result.scalars().all()
            
            # Try to reuse a recent connection with credentials
            for conn in inactive_connections[:3]:  # Check last 3 inactive connections
                if self._has_valid_credentials(conn):
                    self.logger.info(f"Reusing inactive connection with credentials: {conn.id}")
                    return {
                        "connection_id": str(conn.id),
                        "is_existing": True,
                        "is_logged_in": False,
                        "message": "Reusing existing WhatsApp connection"
                    }
            
            # No suitable existing connection found - need to create new one
            # But first, clean up old connections without credentials
            await self._cleanup_old_connections(db, user_id)
            
            return {
                "connection_id": None,
                "is_existing": False,
                "is_logged_in": False,
                "message": "Need to create new WhatsApp connection"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get/create connection: {e}")
            return {
                "connection_id": None,
                "is_existing": False,
                "is_logged_in": False,
                "error": str(e)
            }
    
    async def _test_connection(self, connection: PlatformConnection) -> Dict[str, Any]:
        """
        Test if a connection is actually working.

        Uses connector cache to avoid creating new connector instances repeatedly.
        """
        try:
            # Get or create cached connector (avoids resource exhaustion)
            cache = get_connector_cache()
            connector = await cache.get_or_create(
                connection_id=connection.id,
                connector_class=WhatsAppConnector,
                credentials=connection.credentials
            )

            # Ensure connection is established
            if not hasattr(connector, '_client') or connector._client is None:
                await connector.connect()

            try:
                status = await connector.get_bridge_status()
                return {
                    "is_logged_in": status.logged_in,
                    "phone": status.phone,
                    "connected": status.connected
                }
            except Exception as e:
                # If status check fails, invalidate cache and retry
                self.logger.warning(f"Status check failed, invalidating cache: {e}")
                await cache.invalidate(connection.id)
                raise

        except Exception as e:
            self.logger.warning(f"Connection test failed for {connection.id}: {e}")
            return {
                "is_logged_in": False,
                "phone": None,
                "connected": False
            }
    
    def _has_valid_credentials(self, connection: PlatformConnection) -> bool:
        """Check if connection has valid Matrix credentials."""
        if not connection.credentials:
            return False
        
        required_keys = [
            "matrix_homeserver_url",
            "matrix_access_token", 
            "matrix_user_id"
        ]
        
        return all(
            key in connection.credentials and connection.credentials[key]
            for key in required_keys
        )
    
    async def _update_connection_status(
        self,
        db: AsyncSession,
        connection_id: UUID,
        status: ConnectionStatus
    ) -> None:
        """Update connection status."""
        await db.execute(
            update(PlatformConnection)
            .where(PlatformConnection.id == connection_id)
            .values(
                status=status,
                last_sync_at=datetime.utcnow() if status == ConnectionStatus.ACTIVE else None
            )
        )
        await db.commit()
    
    async def _cleanup_old_connections(
        self,
        db: AsyncSession,
        user_id: UUID,
        keep_recent: int = 2
    ) -> None:
        """Clean up old connections without credentials."""
        try:
            # Get all user's WhatsApp connections
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == PlatformType.WHATSAPP
                ).order_by(PlatformConnection.created_at.desc())
            )
            connections = result.scalars().all()
            
            # Keep recent connections with credentials and active connections
            to_delete = []
            kept_count = 0
            
            for conn in connections:
                # Always keep active connections
                if conn.status == ConnectionStatus.ACTIVE:
                    continue
                
                # Keep recent connections with credentials
                if self._has_valid_credentials(conn) and kept_count < keep_recent:
                    kept_count += 1
                    continue
                
                # Mark for deletion
                to_delete.append(conn)
            
            # Delete old connections
            for conn in to_delete:
                await db.delete(conn)
            
            if to_delete:
                await db.commit()
                self.logger.info(f"Cleaned up {len(to_delete)} old WhatsApp connections for user {user_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old connections: {e}")
    
    async def list_user_connections(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """List all WhatsApp connections for a user."""
        try:
            result = await db.execute(
                select(PlatformConnection).where(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == PlatformType.WHATSAPP
                ).order_by(PlatformConnection.created_at.desc())
            )
            connections = result.scalars().all()
            
            connection_list = []
            for conn in connections:
                connection_list.append({
                    "connection_id": str(conn.id),
                    "status": conn.status.value,
                    "created_at": conn.created_at.isoformat(),
                    "has_credentials": self._has_valid_credentials(conn),
                    "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None
                })
            
            return connection_list
            
        except Exception as e:
            self.logger.error(f"Failed to list connections: {e}")
            return []


# Global manager instance
_connection_manager = None

def get_whatsapp_connection_manager() -> WhatsAppConnectionManager:
    """Get WhatsApp connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = WhatsAppConnectionManager()
    return _connection_manager