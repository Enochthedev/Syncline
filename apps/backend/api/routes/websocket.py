"""
WebSocket API Endpoint

Provides real-time WebSocket connectivity:
- WebSocket connection endpoint
- Subscription management
- Real-time event streaming
- Heartbeat/ping-pong
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from services.realtime.websocket_manager import (
    get_websocket_manager,
    ConnectionSubscription,
)

logger = logging.getLogger(__name__)

router = APIRouter()

__all__ = ["router"]


# =============================================================================
# Message Types
# =============================================================================


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""

    type: str
    data: dict
    timestamp: str = datetime.utcnow().isoformat()


class SubscribeMessage(BaseModel):
    """Subscribe message."""

    platforms: Optional[list[str]] = None
    contact_ids: Optional[list[str]] = None
    thread_ids: Optional[list[str]] = None
    message_types: Optional[list[str]] = None


class PingMessage(BaseModel):
    """Ping message for heartbeat."""

    pass


class PongMessage(BaseModel):
    """Pong response for heartbeat."""

    timestamp: str = datetime.utcnow().isoformat()


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None, description="User ID (for future multi-tenant support)"),
):
    """
    WebSocket endpoint for real-time updates.

    Supports:
    - Subscription filtering by platform, contact, thread, message type
    - Real-time message notifications
    - Heartbeat/ping-pong for connection health
    - Automatic cleanup on disconnect

    Message Types (client -> server):
    - subscribe: Update subscription filters
    - ping: Heartbeat check

    Message Types (server -> client):
    - connected: Initial connection confirmation
    - pong: Heartbeat response
    - message: New message notification
    - collection: Collection event
    - ai: AI processing event
    - error: Error notification

    Example subscription message:
    ```json
    {
        "type": "subscribe",
        "data": {
            "platforms": ["gmail", "slack"],
            "contact_ids": ["contact-uuid"],
            "thread_ids": ["thread-123"],
            "message_types": ["message", "ai"]
        }
    }
    ```

    Example ping message:
    ```json
    {
        "type": "ping",
        "data": {}
    }
    ```
    """
    connection_id = str(uuid4())
    user_uuid = UUID(user_id) if user_id else None

    logger.info(f"WebSocket connection attempt: {connection_id}")

    manager = get_websocket_manager()

    try:
        # Accept connection
        connection = await manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_uuid,
        )

        # Send connection confirmation
        await connection.send_json({
            "type": "connected",
            "data": {
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        })

        # Message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                message_type = data.get("type")
                message_data = data.get("data", {})

                logger.debug(
                    f"Received WebSocket message: {message_type} "
                    f"from {connection_id}"
                )

                # Handle different message types
                if message_type == "subscribe":
                    # Update subscription filters
                    await handle_subscribe(connection_id, message_data, manager)

                elif message_type == "ping":
                    # Respond to heartbeat
                    await handle_ping(connection_id, manager)

                elif message_type == "unsubscribe":
                    # Clear subscription filters
                    await handle_unsubscribe(connection_id, manager)

                else:
                    # Unknown message type
                    await connection.send_json({
                        "type": "error",
                        "data": {
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    })

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break

            except Exception as e:
                logger.error(
                    f"Error processing WebSocket message from {connection_id}: {e}"
                )
                try:
                    await connection.send_json({
                        "type": "error",
                        "data": {
                            "message": str(e),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    })
                except Exception:
                    # Connection likely broken, exit loop
                    break

    except Exception as e:
        logger.error(f"WebSocket connection error for {connection_id}: {e}")

    finally:
        # Clean up connection
        await manager.disconnect(connection_id)
        logger.info(f"WebSocket connection closed: {connection_id}")


async def handle_subscribe(
    connection_id: str,
    data: dict,
    manager,
) -> None:
    """
    Handle subscription message.

    Args:
        connection_id: Connection ID
        data: Subscription data
        manager: WebSocket manager
    """
    try:
        # Parse subscription data
        platforms = data.get("platforms")
        contact_ids_raw = data.get("contact_ids")
        thread_ids = data.get("thread_ids")
        message_types = data.get("message_types")

        # Convert contact IDs to UUIDs
        contact_ids = None
        if contact_ids_raw:
            try:
                contact_ids = {UUID(cid) for cid in contact_ids_raw}
            except ValueError as e:
                logger.error(f"Invalid contact ID format: {e}")
                contact_ids = None

        # Create subscription
        subscription = ConnectionSubscription(
            platforms=set(platforms) if platforms else None,
            contact_ids=contact_ids,
            thread_ids=set(thread_ids) if thread_ids else None,
            message_types=set(message_types) if message_types else None,
        )

        # Update subscription
        await manager.update_subscription(connection_id, subscription)

        # Send confirmation
        connection = await manager.get_connection(connection_id)
        if connection:
            await connection.send_json({
                "type": "subscribed",
                "data": {
                    "platforms": list(subscription.platforms) if subscription.platforms else None,
                    "contact_ids": [str(cid) for cid in subscription.contact_ids] if subscription.contact_ids else None,
                    "thread_ids": list(subscription.thread_ids) if subscription.thread_ids else None,
                    "message_types": list(subscription.message_types) if subscription.message_types else None,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            })

        logger.info(f"Updated subscription for {connection_id}")

    except Exception as e:
        logger.error(f"Error handling subscribe message: {e}")
        raise


async def handle_unsubscribe(
    connection_id: str,
    manager,
) -> None:
    """
    Handle unsubscribe message.

    Args:
        connection_id: Connection ID
        manager: WebSocket manager
    """
    try:
        # Clear subscription (empty subscription matches everything)
        subscription = ConnectionSubscription()

        await manager.update_subscription(connection_id, subscription)

        # Send confirmation
        connection = await manager.get_connection(connection_id)
        if connection:
            await connection.send_json({
                "type": "unsubscribed",
                "data": {
                    "timestamp": datetime.utcnow().isoformat(),
                }
            })

        logger.info(f"Cleared subscription for {connection_id}")

    except Exception as e:
        logger.error(f"Error handling unsubscribe message: {e}")
        raise


async def handle_ping(connection_id: str, manager) -> None:
    """
    Handle ping message.

    Args:
        connection_id: Connection ID
        manager: WebSocket manager
    """
    try:
        # Update heartbeat
        await manager.heartbeat(connection_id)

        # Send pong response
        connection = await manager.get_connection(connection_id)
        if connection:
            await connection.send_json({
                "type": "pong",
                "data": {
                    "timestamp": datetime.utcnow().isoformat(),
                }
            })

    except Exception as e:
        logger.error(f"Error handling ping message: {e}")
        raise
