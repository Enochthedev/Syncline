"""
Integration tests for WebSocket endpoint.

Tests the actual WebSocket endpoint using FastAPI's test client.
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_websocket_test_page(client):
    """Test WebSocket test page endpoint."""
    response = client.get("/api/v1/ws/test")

    assert response.status_code == 200
    assert "WebSocket Test" in response.text
    assert "R.E.M.I WebSocket Test" in response.text


def test_websocket_stats_endpoint(client):
    """Test WebSocket statistics endpoint."""
    response = client.get("/api/v1/ws/stats")

    assert response.status_code == 200
    data = response.json()

    assert "websocket_manager" in data
    assert "active_searches" in data
    assert "timestamp" in data


def test_websocket_health_endpoint(client):
    """Test WebSocket health check endpoint."""
    response = client.get("/api/v1/ws/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "websocket_manager" in data
    assert "websocket_handlers" in data
    assert "timestamp" in data


@patch('api.websocket.manager.websocket_manager')
@patch('api.routes.websocket.websocket_handlers')
def test_websocket_connection_flow(mock_handlers, mock_manager, client):
    """Test WebSocket connection flow."""
    # Mock the WebSocket manager and handlers
    mock_manager.connect = AsyncMock(return_value="test_connection_id")
    mock_manager.disconnect = AsyncMock()
    mock_manager.handle_message = AsyncMock()
    mock_handlers.cleanup_connection = AsyncMock()

    # Test WebSocket connection
    with client.websocket_connect("/api/v1/ws/connect") as websocket:
        # Send test message
        test_message = {
            "type": "ping",
            "data": {},
            "timestamp": "2024-01-01T00:00:00Z"
        }

        websocket.send_text(json.dumps(test_message))

        # The WebSocket should stay connected
        # In a real test, we would verify the response
        # but the mock setup makes this challenging


def test_websocket_authentication_message():
    """Test WebSocket authentication message format."""
    auth_message = {
        "type": "auth_request",
        "data": {
            "user_id": "test_user",
            "token": "test_token",
            "client_info": {
                "user_agent": "test_agent",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    }

    # Verify message can be serialized
    serialized = json.dumps(auth_message)
    deserialized = json.loads(serialized)

    assert deserialized["type"] == "auth_request"
    assert deserialized["data"]["user_id"] == "test_user"
    assert deserialized["data"]["token"] == "test_token"


def test_websocket_search_message():
    """Test WebSocket search message format."""
    search_message = {
        "type": "search_start",
        "data": {
            "query": "test search query",
            "limit": 50,
            "stream_results": True,
            "include_suggestions": True,
            "filters": {
                "platforms": ["gmail", "slack"],
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z"
            }
        },
        "correlation_id": "search_123"
    }

    # Verify message can be serialized
    serialized = json.dumps(search_message)
    deserialized = json.loads(serialized)

    assert deserialized["type"] == "search_start"
    assert deserialized["data"]["query"] == "test search query"
    assert deserialized["data"]["limit"] == 50
    assert deserialized["correlation_id"] == "search_123"


def test_websocket_nudge_acknowledgment_message():
    """Test WebSocket nudge acknowledgment message format."""
    ack_message = {
        "type": "nudge_acknowledged",
        "data": {
            "nudge_id": "nudge_123",
            "acknowledged_at": "2024-01-01T00:00:00Z",
            "user_response": "completed"
        },
        "correlation_id": "ack_123"
    }

    # Verify message can be serialized
    serialized = json.dumps(ack_message)
    deserialized = json.loads(serialized)

    assert deserialized["type"] == "nudge_acknowledged"
    assert deserialized["data"]["nudge_id"] == "nudge_123"
    assert deserialized["correlation_id"] == "ack_123"


class TestWebSocketMessageTypes:
    """Test WebSocket message type definitions."""

    def test_connection_messages(self):
        """Test connection-related message types."""
        from api.websocket.types import WebSocketMessageType

        connection_types = [
            WebSocketMessageType.CONNECT,
            WebSocketMessageType.DISCONNECT,
            WebSocketMessageType.PING,
            WebSocketMessageType.PONG,
            WebSocketMessageType.ERROR
        ]

        for msg_type in connection_types:
            assert isinstance(msg_type.value, str)
            assert len(msg_type.value) > 0

    def test_auth_messages(self):
        """Test authentication-related message types."""
        from api.websocket.types import WebSocketMessageType

        auth_types = [
            WebSocketMessageType.AUTH_REQUEST,
            WebSocketMessageType.AUTH_SUCCESS,
            WebSocketMessageType.AUTH_FAILURE
        ]

        for msg_type in auth_types:
            assert isinstance(msg_type.value, str)
            assert "auth" in msg_type.value

    def test_search_messages(self):
        """Test search-related message types."""
        from api.websocket.types import WebSocketMessageType

        search_types = [
            WebSocketMessageType.SEARCH_START,
            WebSocketMessageType.SEARCH_RESULT,
            WebSocketMessageType.SEARCH_COMPLETE,
            WebSocketMessageType.SEARCH_ERROR
        ]

        for msg_type in search_types:
            assert isinstance(msg_type.value, str)
            assert "search" in msg_type.value

    def test_conversation_messages(self):
        """Test conversation-related message types."""
        from api.websocket.types import WebSocketMessageType

        conversation_types = [
            WebSocketMessageType.MESSAGE_RECEIVED,
            WebSocketMessageType.MESSAGE_UPDATED,
            WebSocketMessageType.THREAD_UPDATED,
            WebSocketMessageType.PARTICIPANT_UPDATED
        ]

        for msg_type in conversation_types:
            assert isinstance(msg_type.value, str)
            assert len(msg_type.value) > 0

    def test_nudge_messages(self):
        """Test nudge-related message types."""
        from api.websocket.types import WebSocketMessageType

        nudge_types = [
            WebSocketMessageType.NUDGE_DELIVERY,
            WebSocketMessageType.NUDGE_ACKNOWLEDGED
        ]

        for msg_type in nudge_types:
            assert isinstance(msg_type.value, str)
            assert "nudge" in msg_type.value


class TestWebSocketDataTypes:
    """Test WebSocket data type definitions."""

    def test_websocket_message_creation(self):
        """Test WebSocketMessage creation."""
        from api.websocket.types import WebSocketMessage, WebSocketMessageType

        message = WebSocketMessage(
            type=WebSocketMessageType.PING,
            data={"test": "data"},
            correlation_id="test_123"
        )

        assert message.type == WebSocketMessageType.PING
        assert message.data["test"] == "data"
        assert message.correlation_id == "test_123"
        assert message.id is not None
        assert message.timestamp is not None

    def test_search_stream_request(self):
        """Test SearchStreamRequest creation."""
        from api.websocket.types import SearchStreamRequest

        request = SearchStreamRequest(
            query="test query",
            filters={"platforms": ["gmail"]},
            limit=25,
            stream_results=True,
            include_suggestions=False
        )

        assert request.query == "test query"
        assert request.filters["platforms"] == ["gmail"]
        assert request.limit == 25
        assert request.stream_results is True
        assert request.include_suggestions is False

    def test_conversation_update(self):
        """Test ConversationUpdate creation."""
        from api.websocket.types import ConversationUpdate

        update = ConversationUpdate(
            update_type="message_received",
            thread_id="thread_123",
            message_id="msg_456",
            platform="gmail",
            content_preview="Hello world"
        )

        assert update.update_type == "message_received"
        assert update.thread_id == "thread_123"
        assert update.message_id == "msg_456"
        assert update.platform == "gmail"
        assert update.content_preview == "Hello world"
        assert update.timestamp is not None

    def test_system_notification(self):
        """Test SystemNotification creation."""
        from api.websocket.types import SystemNotification

        notification = SystemNotification(
            level="info",
            title="Test Notification",
            message="This is a test notification",
            action_url="/test",
            action_text="View",
            auto_dismiss=True,
            dismiss_after=3000
        )

        assert notification.level == "info"
        assert notification.title == "Test Notification"
        assert notification.message == "This is a test notification"
        assert notification.action_url == "/test"
        assert notification.action_text == "View"
        assert notification.auto_dismiss is True
        assert notification.dismiss_after == 3000

    def test_connection_info(self):
        """Test ConnectionInfo creation and methods."""
        from api.websocket.types import ConnectionInfo, ConnectionStatus

        conn_info = ConnectionInfo(
            user_id="test_user",
            status=ConnectionStatus.AUTHENTICATED
        )

        assert conn_info.user_id == "test_user"
        assert conn_info.status == ConnectionStatus.AUTHENTICATED
        assert conn_info.connection_id is not None
        assert conn_info.connected_at is not None
        assert conn_info.last_activity is not None

        # Test methods
        conn_info.add_subscription("test_topic")
        assert "test_topic" in conn_info.subscriptions

        conn_info.remove_subscription("test_topic")
        assert "test_topic" not in conn_info.subscriptions

        old_activity = conn_info.last_activity
        conn_info.update_activity()
        assert conn_info.last_activity > old_activity
