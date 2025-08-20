"""
Integration tests for WebSocket API functionality.

Tests WebSocket connectivity, authentication, search streaming,
and real-time message delivery.
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketState

from api.websocket.manager import WebSocketManager
from api.websocket.handlers import WebSocketHandlers
from api.websocket.types import (
    WebSocketMessage,
    WebSocketMessageType,
    ConnectionInfo,
    ConnectionStatus,
    SearchStreamRequest,
    ConversationUpdate,
    NudgeDelivery,
    SystemNotification
)
from services.ai.memory.types import Nudge, NudgeType, NudgePriority


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.client_state = WebSocketState.CONNECTED
        self.sent_messages = []
        self.received_messages = []
        self._closed = False

    async def accept(self):
        """Mock accept method."""
        pass

    async def send_text(self, data: str):
        """Mock send_text method."""
        if self._closed:
            raise Exception("WebSocket is closed")
        self.sent_messages.append(data)

    async def receive_text(self) -> str:
        """Mock receive_text method."""
        if self.received_messages:
            return self.received_messages.pop(0)
        await asyncio.sleep(0.1)  # Simulate waiting
        return '{"type": "ping", "data": {}}'

    async def close(self):
        """Mock close method."""
        self._closed = True
        self.client_state = WebSocketState.DISCONNECTED

    def add_received_message(self, message: str):
        """Add a message to be received."""
        self.received_messages.append(message)


@pytest.fixture
async def websocket_manager():
    """Create WebSocket manager for testing."""
    manager = WebSocketManager()
    await manager.start()
    try:
        yield manager
    finally:
        await manager.stop()


@pytest.fixture
def websocket_handlers(websocket_manager):
    """Create WebSocket handlers for testing."""
    return WebSocketHandlers(websocket_manager)


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    return MockWebSocket()


@pytest.mark.asyncio
class TestWebSocketManager:
    """Test WebSocket manager functionality."""

    async def test_connect_websocket(self, websocket_manager, mock_websocket):
        """Test WebSocket connection establishment."""
        # Connect WebSocket
        connection_id = await websocket_manager.connect(mock_websocket)

        # Verify connection
        assert connection_id is not None
        assert connection_id in websocket_manager._connections
        assert websocket_manager._stats["active_connections"] == 1

        # Verify connection message was sent
        assert len(mock_websocket.sent_messages) == 1
        message_data = json.loads(mock_websocket.sent_messages[0])
        assert message_data["type"] == "connect"
        assert message_data["data"]["connection_id"] == connection_id

    async def test_authenticate_connection(self, websocket_manager, mock_websocket):
        """Test WebSocket authentication."""
        # Connect WebSocket
        connection_id = await websocket_manager.connect(mock_websocket)

        # Authenticate
        success = await websocket_manager.authenticate(
            connection_id, "test_user", "test_token"
        )

        # Verify authentication
        assert success is True
        conn_info = websocket_manager.get_connection_info(connection_id)
        assert conn_info.user_id == "test_user"
        assert conn_info.status == ConnectionStatus.AUTHENTICATED
        assert websocket_manager._stats["authenticated_connections"] == 1

    async def test_authenticate_invalid_credentials(self, websocket_manager, mock_websocket):
        """Test WebSocket authentication with invalid credentials."""
        # Connect WebSocket
        connection_id = await websocket_manager.connect(mock_websocket)

        # Authenticate with empty token
        success = await websocket_manager.authenticate(
            connection_id, "test_user", ""
        )

        # Verify authentication failed
        assert success is False
        conn_info = websocket_manager.get_connection_info(connection_id)
        assert conn_info.status != ConnectionStatus.AUTHENTICATED
        assert websocket_manager._stats["authenticated_connections"] == 0

    async def test_subscribe_to_topic(self, websocket_manager, mock_websocket):
        """Test subscribing to topics."""
        # Connect and authenticate
        connection_id = await websocket_manager.connect(mock_websocket)
        await websocket_manager.authenticate(connection_id, "test_user", "test_token")

        # Subscribe to topic
        success = await websocket_manager.subscribe(connection_id, "test_topic")

        # Verify subscription
        assert success is True
        conn_info = websocket_manager.get_connection_info(connection_id)
        assert "test_topic" in conn_info.subscriptions
        assert connection_id in websocket_manager._subscriptions["test_topic"]

    async def test_send_to_user(self, websocket_manager, mock_websocket):
        """Test sending messages to specific users."""
        # Connect and authenticate
        connection_id = await websocket_manager.connect(mock_websocket)
        await websocket_manager.authenticate(connection_id, "test_user", "test_token")

        # Send message to user
        message = WebSocketMessage(
            type=WebSocketMessageType.SYSTEM_NOTIFICATION,
            data={"message": "Test notification"}
        )

        sent_count = await websocket_manager.send_to_user("test_user", message)

        # Verify message was sent
        assert sent_count == 1
        assert len(mock_websocket.sent_messages) >= 2  # Connect + notification

        # Check the notification message
        notification_message = json.loads(mock_websocket.sent_messages[-1])
        assert notification_message["type"] == "system_notification"
        assert notification_message["data"]["message"] == "Test notification"

    async def test_send_to_subscription(self, websocket_manager, mock_websocket):
        """Test sending messages to subscription topics."""
        # Connect, authenticate, and subscribe
        connection_id = await websocket_manager.connect(mock_websocket)
        await websocket_manager.authenticate(connection_id, "test_user", "test_token")
        await websocket_manager.subscribe(connection_id, "test_topic")

        # Send message to subscription
        message = WebSocketMessage(
            type=WebSocketMessageType.MESSAGE_RECEIVED,
            data={"content": "New message"}
        )

        sent_count = await websocket_manager.send_to_subscription("test_topic", message)

        # Verify message was sent
        assert sent_count == 1

        # Check the message
        received_message = json.loads(mock_websocket.sent_messages[-1])
        assert received_message["type"] == "message_received"
        assert received_message["data"]["content"] == "New message"

    async def test_disconnect_websocket(self, websocket_manager, mock_websocket):
        """Test WebSocket disconnection."""
        # Connect WebSocket
        connection_id = await websocket_manager.connect(mock_websocket)
        await websocket_manager.authenticate(connection_id, "test_user", "test_token")

        # Disconnect
        await websocket_manager.disconnect(connection_id, "test_disconnect")

        # Verify disconnection
        assert connection_id not in websocket_manager._connections
        assert connection_id not in websocket_manager._connection_info
        assert websocket_manager._stats["active_connections"] == 0
        assert websocket_manager._stats["authenticated_connections"] == 0

    async def test_cleanup_stale_connections(self, websocket_manager, mock_websocket):
        """Test cleanup of stale connections."""
        # Connect WebSocket
        connection_id = await websocket_manager.connect(mock_websocket)

        # Manually set old activity time
        conn_info = websocket_manager.get_connection_info(connection_id)
        conn_info.last_activity = datetime.utcnow().replace(year=2020)  # Very old

        # Run cleanup
        await websocket_manager._cleanup_stale_connections()

        # Verify connection was cleaned up
        assert connection_id not in websocket_manager._connections


@pytest.mark.asyncio
class TestWebSocketHandlers:
    """Test WebSocket handlers functionality."""

    async def test_handle_ping_message(self, websocket_handlers, mock_websocket):
        """Test ping message handling."""
        # Connect WebSocket
        connection_id = await websocket_handlers.manager.connect(mock_websocket)

        # Handle ping message
        ping_message = WebSocketMessage(
            type=WebSocketMessageType.PING,
            correlation_id="test_correlation"
        )

        await websocket_handlers._handle_ping(connection_id, ping_message)

        # Verify pong response
        pong_message = json.loads(mock_websocket.sent_messages[-1])
        assert pong_message["type"] == "pong"
        assert pong_message["correlation_id"] == "test_correlation"

    async def test_handle_auth_request(self, websocket_handlers, mock_websocket):
        """Test authentication request handling."""
        # Connect WebSocket
        connection_id = await websocket_handlers.manager.connect(mock_websocket)

        # Handle auth request
        auth_message = WebSocketMessage(
            type=WebSocketMessageType.AUTH_REQUEST,
            data={
                "user_id": "test_user",
                "token": "test_token",
                "client_info": {"browser": "test"}
            }
        )

        await websocket_handlers._handle_auth_request(connection_id, auth_message)

        # Verify authentication success
        conn_info = websocket_handlers.manager.get_connection_info(
            connection_id)
        assert conn_info.user_id == "test_user"
        assert conn_info.status == ConnectionStatus.AUTHENTICATED

    @patch('api.websocket.handlers.HybridSearchAgent')
    async def test_handle_search_start(self, mock_search_agent, websocket_handlers, mock_websocket):
        """Test search streaming request handling."""
        # Setup mock search agent
        mock_agent_instance = AsyncMock()
        mock_search_agent.return_value = mock_agent_instance
        mock_agent_instance._initialized = True

        # Mock search response
        from services.ai.search.types import SearchResponse, SearchStats, SearchResult, SearchResultType
        mock_result = SearchResult(
            id="test_result",
            type=SearchResultType.MESSAGE,
            title="Test Result",
            content="Test content",
            platform="test",
            timestamp=datetime.utcnow(),
            ranking=MagicMock()
        )

        mock_response = SearchResponse(
            results=[mock_result],
            stats=SearchStats(
                total_results=1,
                processing_time_ms=100
            ),
            query=MagicMock()
        )

        mock_agent_instance.search.return_value = mock_response

        # Connect and authenticate
        connection_id = await websocket_handlers.manager.connect(mock_websocket)
        await websocket_handlers.manager.authenticate(connection_id, "test_user", "test_token")

        # Handle search request
        search_message = WebSocketMessage(
            type=WebSocketMessageType.SEARCH_START,
            data={
                "query": "test search",
                "limit": 10,
                "stream_results": True
            },
            correlation_id="search_test"
        )

        await websocket_handlers._handle_search_start(connection_id, search_message)

        # Wait for search to complete
        await asyncio.sleep(0.2)

        # Verify search was called
        mock_agent_instance.search.assert_called_once()

    async def test_send_conversation_update(self, websocket_handlers, mock_websocket):
        """Test sending conversation updates."""
        # Connect and subscribe to thread
        connection_id = await websocket_handlers.manager.connect(mock_websocket)
        await websocket_handlers.manager.authenticate(connection_id, "test_user", "test_token")
        await websocket_handlers.manager.subscribe(connection_id, "thread:test_thread")

        # Send conversation update
        update = ConversationUpdate(
            update_type="message_received",
            thread_id="test_thread",
            message_id="test_message",
            platform="test_platform",
            content_preview="Test message content"
        )

        sent_count = await websocket_handlers.send_conversation_update(update)

        # Verify update was sent
        assert sent_count > 0

        # Check message was received
        update_message = json.loads(mock_websocket.sent_messages[-1])
        assert update_message["type"] == "message_received"
        assert update_message["data"]["thread_id"] == "test_thread"

    async def test_send_nudge_to_user(self, websocket_handlers, mock_websocket):
        """Test sending nudges to users."""
        # Connect and authenticate
        connection_id = await websocket_handlers.manager.connect(mock_websocket)
        await websocket_handlers.manager.authenticate(connection_id, "test_user", "test_token")

        # Create test nudge
        nudge = Nudge(
            type=NudgeType.DEADLINE_REMINDER,
            priority=NudgePriority.HIGH,
            title="Test Nudge",
            message="This is a test nudge"
        )

        nudge_delivery = NudgeDelivery(
            nudge=nudge,
            requires_acknowledgment=True
        )

        # Send nudge
        sent_count = await websocket_handlers.send_nudge_to_user("test_user", nudge_delivery)

        # Verify nudge was sent
        assert sent_count == 1

        # Check nudge message
        nudge_message = json.loads(mock_websocket.sent_messages[-1])
        assert nudge_message["type"] == "nudge_delivery"
        assert nudge_message["data"]["nudge"]["title"] == "Test Nudge"

    async def test_send_system_notification(self, websocket_handlers, mock_websocket):
        """Test sending system notifications."""
        # Connect and authenticate
        connection_id = await websocket_handlers.manager.connect(mock_websocket)
        await websocket_handlers.manager.authenticate(connection_id, "test_user", "test_token")

        # Create system notification
        notification = SystemNotification(
            level="info",
            title="System Update",
            message="System has been updated successfully",
            auto_dismiss=True
        )

        # Send notification
        sent_count = await websocket_handlers.send_system_notification(
            notification, target_users=["test_user"]
        )

        # Verify notification was sent
        assert sent_count == 1

        # Check notification message
        notification_message = json.loads(mock_websocket.sent_messages[-1])
        assert notification_message["type"] == "system_notification"
        assert notification_message["data"]["title"] == "System Update"

    async def test_health_check(self, websocket_handlers):
        """Test WebSocket handlers health check."""
        health = await websocket_handlers.health_check()

        assert health["status"] == "healthy"
        assert "search_handler" in health
        assert "event_handler" in health


@pytest.mark.asyncio
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    async def test_full_websocket_flow(self, websocket_manager, websocket_handlers, mock_websocket):
        """Test complete WebSocket flow from connection to message delivery."""
        # 1. Connect
        connection_id = await websocket_manager.connect(mock_websocket)
        assert connection_id is not None

        # 2. Authenticate
        success = await websocket_manager.authenticate(connection_id, "test_user", "test_token")
        assert success is True

        # 3. Subscribe to topics
        await websocket_manager.subscribe(connection_id, "user:test_user")
        await websocket_manager.subscribe(connection_id, "thread:test_thread")

        # 4. Send various message types

        # System notification
        notification = SystemNotification(
            level="info",
            title="Welcome",
            message="Welcome to R.E.M.I!"
        )
        await websocket_handlers.send_system_notification(notification, ["test_user"])

        # Conversation update
        update = ConversationUpdate(
            update_type="message_received",
            thread_id="test_thread",
            platform="test",
            content_preview="Hello world"
        )
        await websocket_handlers.send_conversation_update(update)

        # 5. Verify messages were received
        # connect + auth_success + notification + update
        assert len(mock_websocket.sent_messages) >= 4

        # 6. Disconnect
        await websocket_manager.disconnect(connection_id)
        assert connection_id not in websocket_manager._connections

    async def test_multiple_connections_same_user(self, websocket_manager):
        """Test multiple connections for the same user."""
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()

        # Connect two WebSockets for same user
        conn_id1 = await websocket_manager.connect(mock_ws1)
        conn_id2 = await websocket_manager.connect(mock_ws2)

        await websocket_manager.authenticate(conn_id1, "test_user", "token1")
        await websocket_manager.authenticate(conn_id2, "test_user", "token2")

        # Send message to user
        message = WebSocketMessage(
            type=WebSocketMessageType.SYSTEM_NOTIFICATION,
            data={"message": "Broadcast test"}
        )

        sent_count = await websocket_manager.send_to_user("test_user", message)

        # Verify message was sent to both connections
        assert sent_count == 2
        assert len(mock_ws1.sent_messages) >= 2
        assert len(mock_ws2.sent_messages) >= 2

    async def test_connection_cleanup_on_error(self, websocket_manager):
        """Test connection cleanup when WebSocket errors occur."""
        mock_ws = MockWebSocket()

        # Connect WebSocket
        connection_id = await websocket_manager.connect(mock_ws)
        await websocket_manager.authenticate(connection_id, "test_user", "test_token")

        # Simulate WebSocket error by closing it
        mock_ws._closed = True
        mock_ws.client_state = WebSocketState.DISCONNECTED

        # Try to send message (should trigger cleanup)
        message = WebSocketMessage(
            type=WebSocketMessageType.PING,
            data={}
        )

        sent = await websocket_manager._send_to_connection(connection_id, message)

        # Verify connection was cleaned up
        assert sent is False
        assert connection_id not in websocket_manager._connections
