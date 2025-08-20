"""
WebSocket connection manager for handling real-time connections.

This module manages WebSocket connections, authentication, subscriptions,
and message broadcasting for the real-time API.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from .types import (
    WebSocketMessage,
    WebSocketMessageType,
    ConnectionInfo,
    ConnectionStatus,
    WebSocketError,
    AuthenticationError
)

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections, authentication, and message broadcasting.

    Provides connection lifecycle management, user authentication,
    subscription handling, and efficient message delivery.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        # Active connections by connection ID
        self._connections: Dict[str, WebSocket] = {}

        # Connection information by connection ID
        self._connection_info: Dict[str, ConnectionInfo] = {}

        # User ID to connection IDs mapping
        self._user_connections: Dict[str, Set[str]] = {}

        # Subscription to connection IDs mapping
        self._subscriptions: Dict[str, Set[str]] = {}

        # Message handlers by message type
        self._message_handlers: Dict[WebSocketMessageType, Callable] = {}

        # Connection statistics
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "authenticated_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "connection_errors": 0,
            "authentication_failures": 0
        }

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5 minutes
        self._connection_timeout = 3600  # 1 hour

        logger.info("WebSocketManager initialized")

    async def start(self) -> None:
        """Start the WebSocket manager."""
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("WebSocketManager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Disconnect all connections
        await self._disconnect_all()
        logger.info("WebSocketManager stopped")

    async def connect(self, websocket: WebSocket, connection_id: Optional[str] = None) -> str:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            connection_id: Optional custom connection ID

        Returns:
            Connection ID for the new connection
        """
        await websocket.accept()

        # Create connection info
        conn_info = ConnectionInfo(
            connection_id=connection_id or ConnectionInfo().connection_id,
            status=ConnectionStatus.CONNECTED
        )

        # Store connection
        self._connections[conn_info.connection_id] = websocket
        self._connection_info[conn_info.connection_id] = conn_info

        # Update statistics
        self._stats["total_connections"] += 1
        self._stats["active_connections"] += 1

        logger.info(
            f"WebSocket connection established: {conn_info.connection_id}")

        # Send connection confirmation
        await self._send_to_connection(
            conn_info.connection_id,
            WebSocketMessage(
                type=WebSocketMessageType.CONNECT,
                data={
                    "connection_id": conn_info.connection_id,
                    "status": "connected",
                    "server_time": datetime.utcnow().isoformat()
                }
            )
        )

        return conn_info.connection_id

    async def disconnect(self, connection_id: str, reason: str = "client_disconnect") -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            connection_id: Connection ID to disconnect
            reason: Reason for disconnection
        """
        if connection_id not in self._connections:
            return

        conn_info = self._connection_info.get(connection_id)
        if conn_info:
            conn_info.status = ConnectionStatus.DISCONNECTING

        try:
            # Send disconnect message if connection is still open
            websocket = self._connections[connection_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps({
                    "type": WebSocketMessageType.DISCONNECT.value,
                    "data": {"reason": reason},
                    "timestamp": datetime.utcnow().isoformat()
                }))
                await websocket.close()

        except Exception as e:
            logger.warning(f"Error during disconnect for {connection_id}: {e}")

        # Clean up connection data
        await self._cleanup_connection(connection_id)

        logger.info(
            f"WebSocket connection disconnected: {connection_id} (reason: {reason})")

    async def authenticate(self, connection_id: str, user_id: str, token: str) -> bool:
        """
        Authenticate a WebSocket connection.

        Args:
            connection_id: Connection ID to authenticate
            user_id: User ID for authentication
            token: Authentication token

        Returns:
            True if authentication successful, False otherwise
        """
        if connection_id not in self._connections:
            return False

        try:
            # TODO: Implement actual token validation
            # For now, accept any non-empty token
            if not token or not user_id:
                raise AuthenticationError("Invalid credentials")

            # Update connection info
            conn_info = self._connection_info[connection_id]
            conn_info.user_id = user_id
            conn_info.status = ConnectionStatus.AUTHENTICATED
            conn_info.update_activity()

            # Add to user connections mapping
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

            # Update statistics
            self._stats["authenticated_connections"] += 1

            # Send authentication success
            await self._send_to_connection(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.AUTH_SUCCESS,
                    data={
                        "user_id": user_id,
                        "authenticated_at": datetime.utcnow().isoformat()
                    },
                    user_id=user_id
                )
            )

            logger.info(
                f"WebSocket connection authenticated: {connection_id} (user: {user_id})")
            return True

        except Exception as e:
            logger.error(f"Authentication failed for {connection_id}: {e}")

            # Update statistics
            self._stats["authentication_failures"] += 1

            # Send authentication failure
            await self._send_to_connection(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.AUTH_FAILURE,
                    data={
                        "error": str(e),
                        "error_code": getattr(e, 'error_code', 'AUTH_ERROR')
                    }
                )
            )

            return False

    async def subscribe(self, connection_id: str, subscription: str) -> bool:
        """
        Subscribe a connection to a topic.

        Args:
            connection_id: Connection ID to subscribe
            subscription: Subscription topic

        Returns:
            True if subscription successful, False otherwise
        """
        if connection_id not in self._connections:
            return False

        conn_info = self._connection_info.get(connection_id)
        if not conn_info or conn_info.status != ConnectionStatus.AUTHENTICATED:
            return False

        # Add subscription
        conn_info.add_subscription(subscription)

        # Add to subscription mapping
        if subscription not in self._subscriptions:
            self._subscriptions[subscription] = set()
        self._subscriptions[subscription].add(connection_id)

        logger.debug(
            f"Connection {connection_id} subscribed to {subscription}")
        return True

    async def unsubscribe(self, connection_id: str, subscription: str) -> bool:
        """
        Unsubscribe a connection from a topic.

        Args:
            connection_id: Connection ID to unsubscribe
            subscription: Subscription topic

        Returns:
            True if unsubscription successful, False otherwise
        """
        if connection_id not in self._connections:
            return False

        conn_info = self._connection_info.get(connection_id)
        if conn_info:
            conn_info.remove_subscription(subscription)

        # Remove from subscription mapping
        if subscription in self._subscriptions:
            self._subscriptions[subscription].discard(connection_id)
            if not self._subscriptions[subscription]:
                del self._subscriptions[subscription]

        logger.debug(
            f"Connection {connection_id} unsubscribed from {subscription}")
        return True

    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> int:
        """
        Send a message to all connections for a specific user.

        Args:
            user_id: User ID to send message to
            message: Message to send

        Returns:
            Number of connections the message was sent to
        """
        if user_id not in self._user_connections:
            return 0

        message.user_id = user_id
        sent_count = 0

        for connection_id in list(self._user_connections[user_id]):
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def send_to_subscription(self, subscription: str, message: WebSocketMessage) -> int:
        """
        Send a message to all connections subscribed to a topic.

        Args:
            subscription: Subscription topic
            message: Message to send

        Returns:
            Number of connections the message was sent to
        """
        if subscription not in self._subscriptions:
            return 0

        sent_count = 0

        for connection_id in list(self._subscriptions[subscription]):
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast(self, message: WebSocketMessage, authenticated_only: bool = True) -> int:
        """
        Broadcast a message to all connections.

        Args:
            message: Message to broadcast
            authenticated_only: Only send to authenticated connections

        Returns:
            Number of connections the message was sent to
        """
        sent_count = 0

        for connection_id in list(self._connections.keys()):
            conn_info = self._connection_info.get(connection_id)

            if authenticated_only and (not conn_info or conn_info.status != ConnectionStatus.AUTHENTICATED):
                continue

            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def _send_to_connection(self, connection_id: str, message: WebSocketMessage) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Connection ID to send to
            message: Message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        if connection_id not in self._connections:
            return False

        try:
            websocket = self._connections[connection_id]

            # Check if connection is still open
            if websocket.client_state != WebSocketState.CONNECTED:
                await self._cleanup_connection(connection_id)
                return False

            # Send message
            message_json = message.model_dump_json()
            await websocket.send_text(message_json)

            # Update activity and statistics
            conn_info = self._connection_info.get(connection_id)
            if conn_info:
                conn_info.update_activity()

            self._stats["total_messages_sent"] += 1
            return True

        except WebSocketDisconnect:
            await self._cleanup_connection(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            self._stats["connection_errors"] += 1
            await self._cleanup_connection(connection_id)
            return False

    async def handle_message(self, connection_id: str, message_data: str) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            connection_id: Connection ID that sent the message
            message_data: Raw message data
        """
        try:
            # Parse message
            message_dict = json.loads(message_data)
            message = WebSocketMessage(**message_dict)

            # Update activity
            conn_info = self._connection_info.get(connection_id)
            if conn_info:
                conn_info.update_activity()

            # Update statistics
            self._stats["total_messages_received"] += 1

            # Handle message based on type
            handler = self._message_handlers.get(message.type)
            if handler:
                await handler(connection_id, message)
            else:
                logger.warning(f"No handler for message type: {message.type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {connection_id}: {e}")
            await self._send_error(connection_id, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            await self._send_error(connection_id, f"Message handling error: {str(e)}")

    def register_handler(self, message_type: WebSocketMessageType, handler: Callable) -> None:
        """
        Register a message handler for a specific message type.

        Args:
            message_type: Message type to handle
            handler: Async handler function
        """
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")

    async def _send_error(self, connection_id: str, error_message: str, error_code: str = "GENERAL_ERROR") -> None:
        """Send an error message to a connection."""
        await self._send_to_connection(
            connection_id,
            WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                data={
                    "error": error_message,
                    "error_code": error_code
                }
            )
        )

    async def _cleanup_connection(self, connection_id: str) -> None:
        """Clean up all data for a connection."""
        # Remove from connections
        if connection_id in self._connections:
            del self._connections[connection_id]

        # Get connection info
        conn_info = self._connection_info.get(connection_id)
        if not conn_info:
            return

        # Remove from user connections
        if conn_info.user_id and conn_info.user_id in self._user_connections:
            self._user_connections[conn_info.user_id].discard(connection_id)
            if not self._user_connections[conn_info.user_id]:
                del self._user_connections[conn_info.user_id]

        # Remove from subscriptions
        for subscription in conn_info.subscriptions:
            if subscription in self._subscriptions:
                self._subscriptions[subscription].discard(connection_id)
                if not self._subscriptions[subscription]:
                    del self._subscriptions[subscription]

        # Remove connection info
        del self._connection_info[connection_id]

        # Update statistics
        self._stats["active_connections"] = max(
            0, self._stats["active_connections"] - 1)
        if conn_info.status == ConnectionStatus.AUTHENTICATED:
            self._stats["authenticated_connections"] = max(
                0, self._stats["authenticated_connections"] - 1)

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale connections."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_connections(self) -> None:
        """Clean up stale connections that have timed out."""
        now = datetime.utcnow()
        timeout_threshold = now - timedelta(seconds=self._connection_timeout)

        stale_connections = []

        for connection_id, conn_info in self._connection_info.items():
            if conn_info.last_activity < timeout_threshold:
                stale_connections.append(connection_id)

        for connection_id in stale_connections:
            logger.info(f"Cleaning up stale connection: {connection_id}")
            await self.disconnect(connection_id, "timeout")

    async def _disconnect_all(self) -> None:
        """Disconnect all active connections."""
        connection_ids = list(self._connections.keys())

        for connection_id in connection_ids:
            await self.disconnect(connection_id, "server_shutdown")

    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self._connection_info.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user."""
        return list(self._user_connections.get(user_id, set()))

    def get_subscription_connections(self, subscription: str) -> List[str]:
        """Get all connection IDs for a subscription."""
        return list(self._subscriptions.get(subscription, set()))

    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            **self._stats,
            "subscriptions": {
                "total_subscriptions": len(self._subscriptions),
                "subscription_topics": list(self._subscriptions.keys())
            },
            "users": {
                "total_users": len(self._user_connections),
                "users_with_connections": [
                    {"user_id": user_id, "connection_count": len(connections)}
                    for user_id, connections in self._user_connections.items()
                ]
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on WebSocket manager."""
        try:
            # Check for stale connections
            now = datetime.utcnow()
            timeout_threshold = now - \
                timedelta(seconds=self._connection_timeout)

            stale_count = sum(
                1 for conn_info in self._connection_info.values()
                if conn_info.last_activity < timeout_threshold
            )

            return {
                "status": "healthy",
                "active_connections": self._stats["active_connections"],
                "authenticated_connections": self._stats["authenticated_connections"],
                "stale_connections": stale_count,
                "total_subscriptions": len(self._subscriptions),
                "cleanup_task_running": self._cleanup_task and not self._cleanup_task.done(),
                "last_check": now.isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


@asynccontextmanager
async def websocket_manager_context():
    """Context manager for WebSocket manager lifecycle."""
    try:
        await websocket_manager.start()
        yield websocket_manager
    finally:
        await websocket_manager.stop()
