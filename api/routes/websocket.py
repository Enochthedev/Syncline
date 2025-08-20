"""
WebSocket API endpoints for real-time notifications and updates.

Provides WebSocket endpoints for:
- Real-time search result streaming
- Live conversation updates
- Proactive nudge delivery
- Connection management with authentication
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import HTMLResponse

from api.websocket.manager import websocket_manager
from api.websocket.handlers import WebSocketHandlers
from api.websocket.types import (
    SystemNotification,
    NudgeDelivery,
    ConversationUpdate
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Initialize handlers
websocket_handlers = WebSocketHandlers(websocket_manager)


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, connection_id: Optional[str] = None):
    """
    Main WebSocket endpoint for real-time communication.

    Supports:
    - Authentication
    - Search streaming
    - Conversation updates
    - Nudge delivery
    - System notifications
    """
    conn_id = None

    try:
        # Accept connection
        conn_id = await websocket_manager.connect(websocket, connection_id)
        logger.info(f"WebSocket connection established: {conn_id}")

        # Handle messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()

                # Handle message
                await websocket_handlers.manager.handle_message(conn_id, data)

            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {conn_id}")
                break
            except Exception as e:
                logger.error(
                    f"Error handling WebSocket message for {conn_id}: {e}")
                # Continue processing other messages

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    finally:
        # Clean up connection
        if conn_id:
            await websocket_manager.disconnect(conn_id, "connection_closed")
            await websocket_handlers.cleanup_connection(conn_id)


@router.get("/test")
async def websocket_test_page():
    """
    Simple test page for WebSocket functionality.

    Returns an HTML page with JavaScript WebSocket client for testing.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .messages { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; background: #f9f9f9; }
            .message { margin: 5px 0; padding: 5px; border-radius: 3px; }
            .sent { background: #e3f2fd; }
            .received { background: #f3e5f5; }
            .error { background: #ffebee; color: #c62828; }
            input, button { margin: 5px; padding: 8px; }
            button { background: #2196f3; color: white; border: none; border-radius: 3px; cursor: pointer; }
            button:hover { background: #1976d2; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .connected { background: #c8e6c9; color: #2e7d32; }
            .disconnected { background: #ffcdd2; color: #c62828; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>R.E.M.I WebSocket Test</h1>
            
            <div class="section">
                <h3>Connection Status</h3>
                <div id="status" class="status disconnected">Disconnected</div>
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
            </div>
            
            <div class="section">
                <h3>Authentication</h3>
                <input type="text" id="userId" placeholder="User ID" value="test_user">
                <input type="text" id="token" placeholder="Token" value="test_token">
                <button onclick="authenticate()">Authenticate</button>
            </div>
            
            <div class="section">
                <h3>Search</h3>
                <input type="text" id="searchQuery" placeholder="Search query" value="test search">
                <button onclick="startSearch()">Start Search</button>
            </div>
            
            <div class="section">
                <h3>Messages</h3>
                <div id="messages" class="messages"></div>
                <button onclick="clearMessages()">Clear Messages</button>
            </div>
        </div>

        <script>
            let ws = null;
            let connectionId = null;

            function addMessage(content, type = 'received') {
                const messages = document.getElementById('messages');
                const message = document.createElement('div');
                message.className = `message ${type}`;
                message.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong>: ${content}`;
                messages.appendChild(message);
                messages.scrollTop = messages.scrollHeight;
            }

            function updateStatus(status, connected = false) {
                const statusEl = document.getElementById('status');
                statusEl.textContent = status;
                statusEl.className = `status ${connected ? 'connected' : 'disconnected'}`;
            }

            function connect() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    addMessage('Already connected', 'error');
                    return;
                }

                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/connect`;
                
                ws = new WebSocket(wsUrl);

                ws.onopen = function(event) {
                    updateStatus('Connected', true);
                    addMessage('WebSocket connected');
                };

                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        addMessage(`Received: ${JSON.stringify(data, null, 2)}`);
                        
                        // Handle specific message types
                        if (data.type === 'connect') {
                            connectionId = data.data.connection_id;
                            addMessage(`Connection ID: ${connectionId}`);
                        } else if (data.type === 'auth_success') {
                            addMessage('Authentication successful!');
                        } else if (data.type === 'search_result') {
                            addMessage(`Search result: ${data.data.result.title || 'Result'}`);
                        } else if (data.type === 'search_complete') {
                            addMessage(`Search complete: ${data.data.total_results} results`);
                        }
                    } catch (e) {
                        addMessage(`Raw message: ${event.data}`);
                    }
                };

                ws.onclose = function(event) {
                    updateStatus('Disconnected', false);
                    addMessage(`WebSocket closed: ${event.code} ${event.reason}`);
                };

                ws.onerror = function(error) {
                    updateStatus('Error', false);
                    addMessage(`WebSocket error: ${error}`, 'error');
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                    connectionId = null;
                }
            }

            function sendMessage(message) {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    addMessage('Not connected', 'error');
                    return;
                }

                ws.send(JSON.stringify(message));
                addMessage(`Sent: ${JSON.stringify(message, null, 2)}`, 'sent');
            }

            function authenticate() {
                const userId = document.getElementById('userId').value;
                const token = document.getElementById('token').value;

                if (!userId || !token) {
                    addMessage('Please enter user ID and token', 'error');
                    return;
                }

                sendMessage({
                    type: 'auth_request',
                    data: {
                        user_id: userId,
                        token: token,
                        client_info: {
                            user_agent: navigator.userAgent,
                            timestamp: new Date().toISOString()
                        }
                    }
                });
            }

            function startSearch() {
                const query = document.getElementById('searchQuery').value;

                if (!query) {
                    addMessage('Please enter a search query', 'error');
                    return;
                }

                sendMessage({
                    type: 'search_start',
                    data: {
                        query: query,
                        limit: 20,
                        stream_results: true,
                        include_suggestions: true
                    }
                });
            }

            function clearMessages() {
                document.getElementById('messages').innerHTML = '';
            }

            // Auto-connect on page load
            window.onload = function() {
                connect();
            };
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns information about active connections, users, and subscriptions.
    """
    try:
        stats = websocket_manager.get_statistics()
        handler_stats = websocket_handlers.get_active_searches()

        return {
            "websocket_manager": stats,
            "active_searches": handler_stats,
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }

    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get WebSocket statistics: {str(e)}"
        )


@router.get("/health")
async def websocket_health_check():
    """
    Perform health check on WebSocket services.

    Returns health status of WebSocket manager and handlers.
    """
    try:
        manager_health = await websocket_manager.health_check()
        handler_health = await websocket_handlers.health_check()

        overall_status = "healthy"
        if (manager_health.get("status") != "healthy" or
                handler_health.get("status") != "healthy"):
            overall_status = "degraded"

        return {
            "status": overall_status,
            "websocket_manager": manager_health,
            "websocket_handlers": handler_health,
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }

    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WebSocket health check failed: {str(e)}"
        )


# Utility functions for other parts of the application to use

async def send_conversation_update_to_websocket(update: ConversationUpdate) -> int:
    """
    Send conversation update via WebSocket.

    Args:
        update: Conversation update to send

    Returns:
        Number of connections the update was sent to
    """
    return await websocket_handlers.send_conversation_update(update)


async def send_nudge_to_user_via_websocket(user_id: str, nudge_delivery: NudgeDelivery) -> int:
    """
    Send nudge to user via WebSocket.

    Args:
        user_id: User ID to send nudge to
        nudge_delivery: Nudge delivery data

    Returns:
        Number of connections the nudge was sent to
    """
    return await websocket_handlers.send_nudge_to_user(user_id, nudge_delivery)


async def send_system_notification_via_websocket(
    notification: SystemNotification,
    target_users: Optional[list] = None
) -> int:
    """
    Send system notification via WebSocket.

    Args:
        notification: System notification to send
        target_users: Optional list of user IDs to send to

    Returns:
        Number of connections the notification was sent to
    """
    return await websocket_handlers.send_system_notification(
        notification, target_users
    )
