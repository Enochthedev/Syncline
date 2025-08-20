"""
WebSocket API types and data structures.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from services.ai.search.types import SearchResult, SearchQuery
from services.ai.memory.types import Nudge


class WebSocketMessageType(str, Enum):
    """WebSocket message types."""
    # Connection management
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Authentication
    AUTH_REQUEST = "auth_request"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"

    # Search streaming
    SEARCH_START = "search_start"
    SEARCH_RESULT = "search_result"
    SEARCH_COMPLETE = "search_complete"
    SEARCH_ERROR = "search_error"

    # Conversation updates
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_UPDATED = "message_updated"
    THREAD_UPDATED = "thread_updated"
    PARTICIPANT_UPDATED = "participant_updated"

    # Proactive nudges
    NUDGE_DELIVERY = "nudge_delivery"
    NUDGE_ACKNOWLEDGED = "nudge_acknowledged"

    # System notifications
    SYSTEM_NOTIFICATION = "system_notification"
    STATUS_UPDATE = "status_update"


class ConnectionStatus(str, Enum):
    """WebSocket connection status."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: WebSocketMessageType
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuthRequest(BaseModel):
    """Authentication request data."""
    token: str
    user_id: Optional[str] = None
    client_info: Dict[str, Any] = Field(default_factory=dict)


class SearchStreamRequest(BaseModel):
    """Search streaming request data."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 50
    stream_results: bool = True
    include_suggestions: bool = False


class SearchStreamResult(BaseModel):
    """Individual search result for streaming."""
    result: SearchResult
    batch_index: int
    total_batches: Optional[int] = None
    is_final: bool = False


class ConversationUpdate(BaseModel):
    """Conversation update notification."""
    update_type: str  # message_received, message_updated, thread_updated
    thread_id: str
    message_id: Optional[str] = None
    participant_id: Optional[str] = None
    platform: str
    content_preview: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NudgeDelivery(BaseModel):
    """Proactive nudge delivery."""
    nudge: Nudge
    delivery_context: Dict[str, Any] = Field(default_factory=dict)
    requires_acknowledgment: bool = True
    expires_at: Optional[datetime] = None


class SystemNotification(BaseModel):
    """System notification message."""
    level: str  # info, warning, error, success
    title: str
    message: str
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    auto_dismiss: bool = True
    dismiss_after: int = 5000  # milliseconds


class StatusUpdate(BaseModel):
    """System status update."""
    component: str
    status: str  # healthy, degraded, unhealthy
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class ConnectionInfo:
    """WebSocket connection information."""
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    client_info: Dict[str, Any] = field(default_factory=dict)
    subscriptions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def add_subscription(self, subscription: str) -> None:
        """Add a subscription."""
        if subscription not in self.subscriptions:
            self.subscriptions.append(subscription)

    def remove_subscription(self, subscription: str) -> None:
        """Remove a subscription."""
        if subscription in self.subscriptions:
            self.subscriptions.remove(subscription)


class WebSocketError(Exception):
    """WebSocket-specific error."""

    def __init__(self, message: str, error_code: str = "WEBSOCKET_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class AuthenticationError(WebSocketError):
    """Authentication-related WebSocket error."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTH_ERROR", details)


class SubscriptionError(WebSocketError):
    """Subscription-related WebSocket error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SUBSCRIPTION_ERROR", details)


class StreamingError(WebSocketError):
    """Streaming-related WebSocket error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "STREAMING_ERROR", details)
