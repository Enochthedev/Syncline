"""
WebSocket Connection Manager

Manages WebSocket connections for real-time updates:
- Connection lifecycle management
- Message broadcasting
- Subscription filtering by platform/contact
- Connection health monitoring
- Automatic reconnection handling
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConnectionSubscription(BaseModel):
    """Subscription configuration for a WebSocket connection."""

    platforms: Optional[Set[str]] = None
    contact_ids: Optional[Set[UUID]] = None
    thread_ids: Optional[Set[str]] = None
    message_types: Optional[Set[str]] = None


class WebSocketConnection:
    """
    Represents a WebSocket connection with subscription filters.

    Attributes:
        websocket: FastAPI WebSocket instance
        connection_id: Unique connection ID
        user_id: User ID (for future multi-tenant support)
        subscription: Subscription filters
        connected_at: Connection timestamp
        last_heartbeat: Last heartbeat timestamp
    """

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[UUID] = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.subscription = ConnectionSubscription()
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()

    async def send_json(self, data: dict) -> None:
        """Send JSON data through the WebSocket."""
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send message to {self.connection_id}: {e}")
            raise

    async def send_text(self, message: str) -> None:
        """Send text message through the WebSocket."""
        try:
            await self.websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send text to {self.connection_id}: {e}")
            raise

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()

    def matches_filter(
        self,
        platform: Optional[str] = None,
        contact_id: Optional[UUID] = None,
        thread_id: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> bool:
        """
        Check if a message matches this connection's subscription filters.

        Args:
            platform: Message platform
            contact_id: Contact ID
            thread_id: Thread ID
            message_type: Message type

        Returns:
            True if message matches filters
        """
        # If no filters are set, match everything
        if not any(
            [
                self.subscription.platforms,
                self.subscription.contact_ids,
                self.subscription.thread_ids,
                self.subscription.message_types,
            ]
        ):
            return True

        # Check platform filter
        if self.subscription.platforms and platform:
            if platform not in self.subscription.platforms:
                return False

        # Check contact filter
        if self.subscription.contact_ids and contact_id:
            if contact_id not in self.subscription.contact_ids:
                return False

        # Check thread filter
        if self.subscription.thread_ids and thread_id:
            if thread_id not in self.subscription.thread_ids:
                return False

        # Check message type filter
        if self.subscription.message_types and message_type:
            if message_type not in self.subscription.message_types:
                return False

        return True


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Provides functionality for:
    - Connection management (add, remove, get)
    - Message broadcasting with filtering
    - Subscription management
    - Health monitoring
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: dict[str, WebSocketConnection] = {}
        self._lock = asyncio.Lock()
        logger.info("Initialized WebSocketManager")

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[UUID] = None,
    ) -> WebSocketConnection:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            connection_id: Unique connection ID
            user_id: Optional user ID

        Returns:
            WebSocketConnection instance
        """
        await websocket.accept()

        async with self._lock:
            connection = WebSocketConnection(websocket, connection_id, user_id)
            self.active_connections[connection_id] = connection

        logger.info(
            f"WebSocket connected: {connection_id} "
            f"(total connections: {len(self.active_connections)})"
        )

        return connection

    async def disconnect(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            connection_id: Connection ID to remove
        """
        async with self._lock:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

        logger.info(
            f"WebSocket disconnected: {connection_id} "
            f"(total connections: {len(self.active_connections)})"
        )

    async def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        Get a connection by ID.

        Args:
            connection_id: Connection ID

        Returns:
            WebSocketConnection or None
        """
        return self.active_connections.get(connection_id)

    async def update_subscription(
        self,
        connection_id: str,
        subscription: ConnectionSubscription,
    ) -> None:
        """
        Update subscription filters for a connection.

        Args:
            connection_id: Connection ID
            subscription: New subscription filters
        """
        connection = await self.get_connection(connection_id)
        if connection:
            connection.subscription = subscription
            logger.info(f"Updated subscription for {connection_id}")

    async def broadcast(
        self,
        message: dict,
        platform: Optional[str] = None,
        contact_id: Optional[UUID] = None,
        thread_id: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> int:
        """
        Broadcast a message to all matching connections.

        Args:
            message: Message data to broadcast
            platform: Optional platform filter
            contact_id: Optional contact filter
            thread_id: Optional thread filter
            message_type: Optional message type filter

        Returns:
            Number of connections that received the message
        """
        sent_count = 0
        failed_connections = []

        for connection_id, connection in list(self.active_connections.items()):
            # Check if connection matches filters
            if not connection.matches_filter(
                platform=platform,
                contact_id=contact_id,
                thread_id=thread_id,
                message_type=message_type,
            ):
                continue

            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {connection_id}: {e}")
                failed_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        if sent_count > 0:
            logger.debug(f"Broadcast message to {sent_count} connections")

        return sent_count

    async def broadcast_to_user(self, user_id: UUID, message: dict) -> int:
        """
        Broadcast a message to all connections for a specific user.

        Args:
            user_id: User ID
            message: Message data to broadcast

        Returns:
            Number of connections that received the message
        """
        sent_count = 0
        failed_connections = []

        for connection_id, connection in list(self.active_connections.items()):
            if connection.user_id != user_id:
                continue

            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {connection_id}: {e}")
                failed_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        if sent_count > 0:
            logger.debug(
                f"Broadcast message to {sent_count} connections for user {user_id}"
            )

        return sent_count

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Connection ID
            message: Message data to send

        Returns:
            True if sent successfully, False otherwise
        """
        connection = await self.get_connection(connection_id)
        if not connection:
            return False

        try:
            await connection.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def heartbeat(self, connection_id: str) -> bool:
        """
        Update heartbeat for a connection.

        Args:
            connection_id: Connection ID

        Returns:
            True if connection exists, False otherwise
        """
        connection = await self.get_connection(connection_id)
        if connection:
            connection.update_heartbeat()
            return True
        return False

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)

    def get_connections_by_user(self, user_id: UUID) -> list[WebSocketConnection]:
        """Get all connections for a specific user."""
        return [
            conn for conn in self.active_connections.values() if conn.user_id == user_id
        ]

    async def close_all(self) -> None:
        """Close all active connections."""
        logger.info(f"Closing all {len(self.active_connections)} WebSocket connections")

        for connection_id in list(self.active_connections.keys()):
            try:
                connection = self.active_connections[connection_id]
                await connection.websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection {connection_id}: {e}")
            finally:
                await self.disconnect(connection_id)

        logger.info("All WebSocket connections closed")


# Global manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get the global WebSocket manager instance.

    Returns:
        WebSocket manager
    """
    global _websocket_manager

    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()

    return _websocket_manager


__all__ = [
    "WebSocketManager",
    "WebSocketConnection",
    "ConnectionSubscription",
    "get_websocket_manager",
]
