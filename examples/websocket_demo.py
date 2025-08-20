"""
WebSocket API demonstration script.

This script demonstrates the WebSocket API functionality including:
- Connection management
- Authentication
- Search streaming
- Nudge delivery
- System notifications
"""

from services.ai.memory.types import Nudge, NudgeType, NudgePriority
from api.websocket.types import (
    WebSocketMessage,
    WebSocketMessageType,
    SearchStreamRequest,
    ConversationUpdate,
    NudgeDelivery,
    SystemNotification
)
from api.websocket.handlers import WebSocketHandlers
from api.websocket.manager import WebSocketManager
import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for demonstration."""

    def __init__(self, name: str):
        self.name = name
        self.messages: List[str] = []
        self.is_connected = True
        # Add client_state attribute to match FastAPI WebSocket interface
        from fastapi.websockets import WebSocketState
        self.client_state = WebSocketState.CONNECTED

    async def accept(self):
        """Mock accept method."""
        logger.info(f"[{self.name}] WebSocket connection accepted")

    async def send_text(self, data: str):
        """Mock send_text method."""
        if not self.is_connected:
            raise Exception("WebSocket is closed")

        self.messages.append(data)

        # Parse and log the message
        try:
            message_data = json.loads(data)
            msg_type = message_data.get("type", "unknown")
            logger.info(f"[{self.name}] Received: {msg_type}")

            # Log specific message types with details
            if msg_type == "search_result":
                result_data = message_data.get("data", {})
                logger.info(
                    f"[{self.name}] Search result: {result_data.get('result', {}).get('title', 'No title')}")
            elif msg_type == "nudge_delivery":
                nudge_data = message_data.get("data", {}).get("nudge", {})
                logger.info(
                    f"[{self.name}] Nudge: {nudge_data.get('title', 'No title')}")
            elif msg_type == "system_notification":
                notification_data = message_data.get("data", {})
                logger.info(
                    f"[{self.name}] Notification: {notification_data.get('title', 'No title')}")

        except json.JSONDecodeError:
            logger.info(f"[{self.name}] Received raw data: {data[:100]}...")

    async def close(self):
        """Mock close method."""
        self.is_connected = False
        from fastapi.websockets import WebSocketState
        self.client_state = WebSocketState.DISCONNECTED
        logger.info(f"[{self.name}] WebSocket connection closed")


async def demonstrate_websocket_api():
    """Demonstrate WebSocket API functionality."""
    logger.info("🚀 Starting WebSocket API Demonstration")

    # Initialize WebSocket manager and handlers
    manager = WebSocketManager()
    handlers = WebSocketHandlers(manager)

    try:
        # Start the manager
        await manager.start()
        logger.info("✅ WebSocket manager started")

        # Create mock WebSocket connections
        user1_ws = MockWebSocket("User1")
        user2_ws = MockWebSocket("User2")

        # 1. Demonstrate connection establishment
        logger.info("\n📡 Demonstrating Connection Establishment")

        user1_conn = await manager.connect(user1_ws)
        user2_conn = await manager.connect(user2_ws)

        logger.info(f"User1 connected with ID: {user1_conn}")
        logger.info(f"User2 connected with ID: {user2_conn}")

        # 2. Demonstrate authentication
        logger.info("\n🔐 Demonstrating Authentication")

        auth1_success = await manager.authenticate(user1_conn, "user1", "token123")
        auth2_success = await manager.authenticate(user2_conn, "user2", "token456")

        logger.info(
            f"User1 authentication: {'✅ Success' if auth1_success else '❌ Failed'}")
        logger.info(
            f"User2 authentication: {'✅ Success' if auth2_success else '❌ Failed'}")

        # 3. Demonstrate subscriptions
        logger.info("\n📢 Demonstrating Subscriptions")

        await manager.subscribe(user1_conn, "thread:demo_thread")
        await manager.subscribe(user1_conn, "platform:gmail")
        await manager.subscribe(user2_conn, "thread:demo_thread")

        logger.info("Users subscribed to demo topics")

        # 4. Demonstrate conversation updates
        logger.info("\n💬 Demonstrating Conversation Updates")

        conversation_update = ConversationUpdate(
            update_type="message_received",
            thread_id="demo_thread",
            message_id="msg_123",
            platform="gmail",
            content_preview="Hello from the WebSocket demo!",
            metadata={"sender": "demo_user"}
        )

        sent_count = await handlers.send_conversation_update(conversation_update)
        logger.info(f"Conversation update sent to {sent_count} connections")

        # 5. Demonstrate nudge delivery
        logger.info("\n🔔 Demonstrating Nudge Delivery")

        demo_nudge = Nudge(
            type=NudgeType.DEADLINE_REMINDER,
            priority=NudgePriority.HIGH,
            title="Demo Deadline Reminder",
            message="Don't forget about the WebSocket demo deadline!",
            confidence_score=0.9
        )

        nudge_delivery = NudgeDelivery(
            nudge=demo_nudge,
            delivery_context={"source": "demo"},
            requires_acknowledgment=True
        )

        nudge_sent = await handlers.send_nudge_to_user("user1", nudge_delivery)
        logger.info(f"Nudge sent to {nudge_sent} connections")

        # 6. Demonstrate system notifications
        logger.info("\n📢 Demonstrating System Notifications")

        system_notification = SystemNotification(
            level="info",
            title="WebSocket Demo Complete",
            message="The WebSocket API demonstration has completed successfully!",
            auto_dismiss=True,
            dismiss_after=5000
        )

        notification_sent = await handlers.send_system_notification(
            system_notification,
            target_users=["user1", "user2"]
        )
        logger.info(
            f"System notification sent to {notification_sent} connections")

        # 7. Demonstrate broadcasting
        logger.info("\n📡 Demonstrating Broadcasting")

        broadcast_message = WebSocketMessage(
            type=WebSocketMessageType.SYSTEM_NOTIFICATION,
            data={
                "level": "success",
                "title": "Broadcast Test",
                "message": "This message was broadcast to all authenticated users"
            }
        )

        broadcast_count = await manager.broadcast(broadcast_message, authenticated_only=True)
        logger.info(f"Broadcast message sent to {broadcast_count} connections")

        # 8. Show statistics
        logger.info("\n📊 WebSocket Statistics")

        stats = manager.get_statistics()
        logger.info(f"Active connections: {stats['active_connections']}")
        logger.info(
            f"Authenticated connections: {stats['authenticated_connections']}")
        logger.info(f"Total messages sent: {stats['total_messages_sent']}")
        logger.info(
            f"Total subscriptions: {stats['subscriptions']['total_subscriptions']}")

        # 9. Health check
        logger.info("\n🏥 Health Check")

        manager_health = await manager.health_check()
        handlers_health = await handlers.health_check()

        logger.info(f"Manager health: {manager_health['status']}")
        logger.info(f"Handlers health: {handlers_health['status']}")

        # 10. Show received messages
        logger.info("\n📨 Messages Received by Clients")

        logger.info(f"User1 received {len(user1_ws.messages)} messages")
        logger.info(f"User2 received {len(user2_ws.messages)} messages")

        # Wait a moment for any async operations to complete
        await asyncio.sleep(0.5)

        # 11. Demonstrate disconnection
        logger.info("\n🔌 Demonstrating Disconnection")

        await manager.disconnect(user1_conn, "demo_complete")
        await manager.disconnect(user2_conn, "demo_complete")

        logger.info("All connections disconnected")

    except Exception as e:
        logger.error(f"❌ Demo error: {e}")
        raise

    finally:
        # Clean up
        await manager.stop()
        logger.info("✅ WebSocket manager stopped")

    logger.info("\n🎉 WebSocket API Demonstration Complete!")
    logger.info("The WebSocket API supports:")
    logger.info("  ✅ Real-time connection management")
    logger.info("  ✅ User authentication and authorization")
    logger.info("  ✅ Topic-based subscriptions")
    logger.info("  ✅ Conversation updates")
    logger.info("  ✅ Proactive nudge delivery")
    logger.info("  ✅ System notifications")
    logger.info("  ✅ Broadcasting and targeted messaging")
    logger.info("  ✅ Health monitoring and statistics")


async def demonstrate_search_streaming():
    """Demonstrate search result streaming."""
    logger.info("\n🔍 Demonstrating Search Streaming")

    manager = WebSocketManager()
    handlers = WebSocketHandlers(manager)

    try:
        await manager.start()

        # Create connection
        user_ws = MockWebSocket("SearchUser")
        conn_id = await manager.connect(user_ws)
        await manager.authenticate(conn_id, "search_user", "search_token")

        # Simulate search request message
        search_message = WebSocketMessage(
            type=WebSocketMessageType.SEARCH_START,
            data={
                "query": "test search query",
                "limit": 20,
                "stream_results": True,
                "include_suggestions": True
            },
            correlation_id="search_demo"
        )

        logger.info("Starting search stream...")

        # Note: This would normally trigger actual search results
        # For demo purposes, we'll just show the message handling
        try:
            await handlers._handle_search_start(conn_id, search_message)
            logger.info(
                "Search stream initiated (would stream results in real implementation)")
        except Exception as e:
            logger.info(
                f"Search stream demo completed (expected in demo environment): {e}")

        await manager.disconnect(conn_id, "search_demo_complete")

    finally:
        await manager.stop()


if __name__ == "__main__":
    # Run the demonstrations
    asyncio.run(demonstrate_websocket_api())
    asyncio.run(demonstrate_search_streaming())
