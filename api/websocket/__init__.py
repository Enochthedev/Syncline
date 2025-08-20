"""
WebSocket API module for real-time notifications and updates.

This module provides WebSocket endpoints for:
- Real-time search result streaming
- Live conversation updates
- Proactive nudge delivery
- Connection management with authentication
"""

from .manager import WebSocketManager
from .handlers import WebSocketHandlers
from .types import (
    WebSocketMessage,
    WebSocketMessageType,
    ConnectionInfo,
    SearchStreamRequest,
    NudgeDelivery,
    ConversationUpdate
)

__all__ = [
    "WebSocketManager",
    "WebSocketHandlers",
    "WebSocketMessage",
    "WebSocketMessageType",
    "ConnectionInfo",
    "SearchStreamRequest",
    "NudgeDelivery",
    "ConversationUpdate"
]
