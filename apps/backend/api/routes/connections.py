"""
Connection Management API

Endpoints for managing platform connections:
- Initiate OAuth flow
- Handle OAuth callbacks
- List active connections
- Disconnect platforms
- Check connection health
"""

import logging
import os
from typing import List
from urllib.parse import urlencode
from uuid import UUID, uuid4

# Ensure .env is loaded for OAuth credentials
from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session, validate_uuid
from db.models.platform_connection import (
    ConnectionStatus,
    PlatformConnection,
    PlatformType,
)
from db.models.user import User
from integrations.base_connector import ConnectorHealth, ConnectorStatus
from integrations.discord_connector import DiscordConnector
from integrations.gmail_connector import GmailConnector
from integrations.google_chat_connector import GoogleChatConnector
from integrations.linkedin_connector import LinkedInConnector
from integrations.slack_connector import SlackConnector
from integrations.telegram_connector import TelegramConnector
from integrations.twitter_connector import TwitterConnector
from integrations.whatsapp_connector import WhatsAppConnector
from services.event_bus import get_event_bus
from services.events.types import ConnectionEvent, EventType

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class InitiateConnectionRequest(BaseModel):
    """Request to initiate platform connection."""

    user_id: UUID = Field(description="User ID initiating the connection")
    redirect_uri: str | None = Field(
        default=None, description="Optional redirect URI after OAuth"
    )


class InitiateConnectionResponse(BaseModel):
    """Response with OAuth URL."""

    connection_id: UUID = Field(description="Connection ID for tracking")
    authorization_url: str = Field(description="OAuth authorization URL")
    state: str = Field(description="OAuth state parameter for security")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters."""

    code: str = Field(description="Authorization code from OAuth provider")
    state: str = Field(description="State parameter for verification")


class ConnectionResponse(BaseModel):
    """Platform connection details."""

    id: UUID = Field(description="Connection ID")
    user_id: UUID = Field(description="User ID")
    platform: str = Field(description="Platform name")
    status: str = Field(description="Connection status")
    last_sync_at: str | None = Field(default=None, description="Last sync timestamp")
    platform_metadata: dict = Field(
        default_factory=dict, description="Platform-specific metadata"
    )
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")


class ConnectionListResponse(BaseModel):
    """List of connections."""

    connections: List[ConnectionResponse] = Field(description="List of connections")
    total: int = Field(description="Total number of connections")


class ConnectionHealthResponse(BaseModel):
    """Connection health status."""

    connection_id: UUID = Field(description="Connection ID")
    platform: str = Field(description="Platform name")
    health_status: str = Field(description="Overall health status")
    connector_status: str = Field(description="Connector operational status")
    last_check_at: str = Field(description="Last health check timestamp")
    last_success_at: str | None = Field(
        default=None, description="Last successful operation"
    )
    last_error_at: str | None = Field(default=None, description="Last error timestamp")
    last_error: str | None = Field(default=None, description="Last error message")
    consecutive_failures: int = Field(description="Consecutive failure count")
    circuit_breaker_open: bool = Field(description="Circuit breaker status")
    metadata: dict = Field(
        default_factory=dict, description="Platform-specific health data"
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _get_connector_class(platform: PlatformType):
    """Get connector class for platform."""
    connector_map = {
        PlatformType.GMAIL: GmailConnector,
        PlatformType.SLACK: SlackConnector,
        PlatformType.DISCORD: DiscordConnector,
        PlatformType.WHATSAPP: WhatsAppConnector,
        PlatformType.TWITTER: TwitterConnector,
        PlatformType.TELEGRAM: TelegramConnector,
        PlatformType.LINKEDIN: LinkedInConnector,
        PlatformType.GOOGLE_CHAT: GoogleChatConnector,
    }
    return connector_map.get(platform)


def _generate_oauth_url(platform: PlatformType, state: str) -> str:
    """
    Generate OAuth authorization URL for a platform.

    Args:
        platform: The platform to generate URL for
        state: OAuth state parameter for CSRF protection

    Returns:
        Authorization URL string
    """
    if platform == PlatformType.GMAIL:
        # Gmail OAuth 2.0
        client_id = os.getenv("GMAIL_CLIENT_ID", "")
        redirect_uri = os.getenv(
            "GMAIL_REDIRECT_URI",
            "http://localhost:8000/api/v1/connections/callback/gmail",
        )
        scopes = os.getenv(
            "GMAIL_SCOPES",
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/userinfo.email",
        )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    elif platform == PlatformType.LINKEDIN:
        # LinkedIn OAuth 2.0
        client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
        redirect_uri = os.getenv(
            "LINKEDIN_REDIRECT_URI",
            "http://localhost:8000/api/v1/connections/callback/linkedin",
        )
        scopes = os.getenv(
            "LINKEDIN_SCOPES", "r_liteprofile r_emailaddress w_member_social"
        )
        # LinkedIn uses space-separated scopes
        scopes = scopes.replace(",", " ")

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

    elif platform == PlatformType.GOOGLE_CHAT:
        # Google Chat OAuth 2.0 (uses same credentials as Gmail, different scopes)
        client_id = os.getenv("GMAIL_CLIENT_ID", "")
        redirect_uri = os.getenv(
            "GOOGLE_CHAT_REDIRECT_URI",
            "http://localhost:8000/api/v1/connections/callback/google_chat",
        )
        # Google Chat scopes
        scopes = (
            "https://www.googleapis.com/auth/chat.spaces.readonly "
            "https://www.googleapis.com/auth/chat.messages.readonly "
            "https://www.googleapis.com/auth/chat.messages.create "
            "https://www.googleapis.com/auth/chat.memberships.readonly"
        )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    else:
        # Placeholder for other platforms
        return f"https://oauth.{platform.value}.com/authorize?state={state}"


async def _emit_connection_event(
    event_type: EventType,
    connection_id: UUID,
    platform: str,
    user_id: UUID,
    error: str | None = None,
) -> None:
    """Emit connection lifecycle event."""
    try:
        event_bus = get_event_bus()
        event = ConnectionEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            source="connection_api",
            payload={
                "connection_id": str(connection_id),
                "platform": platform,
                "user_id": str(user_id),
                "error": error,
            },
        )
        await event_bus.publish(event)
        logger.debug(f"Emitted {event_type.value} event for connection {connection_id}")
    except Exception as e:
        logger.error(f"Failed to emit connection event: {e}")


def _connection_to_response(conn: PlatformConnection) -> ConnectionResponse:
    """Convert database model to response model."""
    return ConnectionResponse(
        id=conn.id,
        user_id=conn.user_id,
        platform=conn.platform.value,
        status=conn.status.value,
        last_sync_at=conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        platform_metadata=conn.platform_metadata or {},
        created_at=conn.created_at.isoformat(),
        updated_at=conn.updated_at.isoformat(),
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "/initiate/{platform}",
    response_model=InitiateConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate platform connection",
    description="Start OAuth flow for connecting to a platform",
)
async def initiate_connection(
    platform: PlatformType,
    request: InitiateConnectionRequest,
    db: AsyncSession = Depends(get_database_session),
) -> InitiateConnectionResponse:
    """
    Initiate OAuth flow for platform connection.

    This endpoint starts the OAuth authentication process by:
    1. Creating a pending connection record
    2. Generating OAuth authorization URL
    3. Returning URL for user to complete authentication

    Args:
        platform: Platform to connect (gmail, slack, discord, etc.)
        request: Connection initiation request
        db: Database session

    Returns:
        Authorization URL and connection tracking ID

    Raises:
        HTTPException: If platform not supported or user not found
    """
    try:
        # Verify user exists
        user_result = await db.execute(select(User).where(User.id == request.user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found",
            )

        # Get connector class
        connector_class = _get_connector_class(platform)
        if not connector_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {platform.value} not supported",
            )

        # Create pending connection record
        # Store the client's redirect_uri so we can redirect back to the app after OAuth
        oauth_state = str(uuid4())
        connection = PlatformConnection(
            id=uuid4(),
            user_id=request.user_id,
            platform=platform,
            credentials={},  # Will be populated after OAuth
            status=ConnectionStatus.INACTIVE,
            platform_metadata={
                "oauth_state": oauth_state,
                "client_redirect_uri": request.redirect_uri,  # Store for callback
            },
        )

        db.add(connection)
        await db.commit()
        await db.refresh(connection)

        # Generate OAuth URL based on platform
        oauth_state = connection.platform_metadata.get("oauth_state", "")
        authorization_url = _generate_oauth_url(platform, oauth_state)

        logger.info(
            f"Initiated {platform.value} connection for user {request.user_id}, "
            f"connection_id={connection.id}"
        )

        return InitiateConnectionResponse(
            connection_id=connection.id,
            authorization_url=authorization_url,
            state=oauth_state,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate connection: {str(e)}",
        )


@router.get(
    "/callback/{platform}",
    status_code=status.HTTP_302_FOUND,
    summary="OAuth callback handler",
    description="Handle OAuth callback, exchange code for tokens, and redirect to app",
)
async def oauth_callback(
    platform: PlatformType,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: str | None = Query(None, description="OAuth error"),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Handle OAuth callback and complete platform connection.

    This endpoint:
    1. Validates OAuth state parameter
    2. Exchanges authorization code for access token
    3. Updates connection with credentials
    4. Redirects back to mobile app with deep link
    """
    from datetime import datetime, timedelta

    import httpx
    from fastapi.responses import HTMLResponse, RedirectResponse

    # App deep link scheme
    APP_SCHEME = os.getenv("APP_DEEP_LINK_SCHEME", "syncline")

    def create_html_response(
        success: bool, platform: str, message: str, connection_id: str | None = None
    ):
        """Create HTML page for web browsers with deep link and fallback."""
        status_color = "#4CAF50" if success else "#F44336"
        status_icon = "✓" if success else "✗"
        status_text = "Connected!" if success else "Connection Failed"

        deep_link = f"{APP_SCHEME}://connection/{'success' if success else 'error'}?platform={platform}"
        if connection_id:
            deep_link += f"&connection_id={connection_id}"
        if not success:
            deep_link += f"&error={message}"

        return HTMLResponse(
            content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{status_text}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }}
                .container {{
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    max-width: 400px;
                }}
                .icon {{
                    font-size: 64px;
                    color: {status_color};
                    margin-bottom: 20px;
                }}
                h1 {{
                    margin: 0 0 12px;
                    color: #1a1a1a;
                }}
                p {{
                    color: #666;
                    margin: 0 0 24px;
                }}
                .btn {{
                    display: inline-block;
                    background: #6366F1;
                    color: white;
                    padding: 14px 32px;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: 600;
                    margin-top: 16px;
                }}
                .btn:hover {{
                    background: #4F46E5;
                }}
                .note {{
                    margin-top: 24px;
                    font-size: 14px;
                    color: #999;
                }}
            </style>
            <script>
                // Try to redirect to app immediately
                window.location.href = "{deep_link}";
            </script>
        </head>
        <body>
            <div class="container">
                <div class="icon">{status_icon}</div>
                <h1>{status_text}</h1>
                <p>{message}</p>
                <a href="{deep_link}" class="btn">Open in Syncline App</a>
                <p class="note">If the app doesn't open automatically, tap the button above.</p>
            </div>
        </body>
        </html>
        """,
            status_code=200,
        )

    # Handle OAuth errors
    if error:
        logger.error(f"OAuth error for {platform.value}: {error}")
        return create_html_response(
            success=False, platform=platform.value, message=f"OAuth error: {error}"
        )

    connection = None
    try:
        # Find connection by state
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == platform,
                PlatformConnection.platform_metadata["oauth_state"].astext == state,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            logger.error(f"OAuth callback: Invalid state {state} for {platform.value}")
            return create_html_response(
                success=False,
                platform=platform.value,
                message="Invalid OAuth state or connection expired. Please try again.",
            )

        # Exchange code for tokens based on platform
        tokens = None

        if platform in [PlatformType.GMAIL, PlatformType.GOOGLE_CHAT]:
            # Google OAuth token exchange
            client_id = os.getenv("GMAIL_CLIENT_ID")
            client_secret = os.getenv("GMAIL_CLIENT_SECRET")

            if platform == PlatformType.GMAIL:
                redirect_uri = os.getenv(
                    "GMAIL_REDIRECT_URI",
                    "http://localhost:8000/api/v1/connections/callback/gmail",
                )
            else:
                redirect_uri = os.getenv(
                    "GOOGLE_CHAT_REDIRECT_URI",
                    "http://localhost:8000/api/v1/connections/callback/google_chat",
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Google token exchange failed: {response.text}")
                    return create_html_response(
                        success=False,
                        platform=platform.value,
                        message="Failed to exchange authorization code. Please try again.",
                    )

                tokens = response.json()

        elif platform == PlatformType.LINKEDIN:
            # LinkedIn OAuth token exchange
            client_id = os.getenv("LINKEDIN_CLIENT_ID")
            client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
            redirect_uri = os.getenv(
                "LINKEDIN_REDIRECT_URI",
                "http://localhost:8000/api/v1/connections/callback/linkedin",
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"LinkedIn token exchange failed: {response.text}")
                    return create_html_response(
                        success=False,
                        platform=platform.value,
                        message="Failed to exchange authorization code. Please try again.",
                    )

                tokens = response.json()

        else:
            # For other platforms, store placeholder (needs implementation)
            tokens = {
                "access_token": f"token_{code[:10]}",
                "token_type": "Bearer",
            }

        # Calculate expiration
        expires_in = tokens.get("expires_in", 3600)
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        # Update connection with real credentials
        connection.credentials = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_in": expires_in,
            "expires_at": expires_at,
            "scope": tokens.get("scope"),
            "client_id": os.getenv(f"{platform.value.upper()}_CLIENT_ID")
            or os.getenv("GMAIL_CLIENT_ID"),
            "client_secret": os.getenv(f"{platform.value.upper()}_CLIENT_SECRET")
            or os.getenv("GMAIL_CLIENT_SECRET"),
        }
        connection.status = ConnectionStatus.ACTIVE
        connection.platform_metadata = {
            **connection.platform_metadata,
            "oauth_completed_at": datetime.utcnow().isoformat(),
        }

        await db.commit()
        await db.refresh(connection)

        # Emit CONNECTION_ESTABLISHED event
        await _emit_connection_event(
            EventType.CONNECTION_ESTABLISHED,
            connection.id,
            platform.value,
            connection.user_id,
        )

        logger.info(
            f"Completed {platform.value} connection for user {connection.user_id}, "
            f"connection_id={connection.id}"
        )

        # Check if client provided a redirect URI (for mobile apps)
        client_redirect_uri = connection.platform_metadata.get("client_redirect_uri")

        if client_redirect_uri:
            # Use HTTP redirect for mobile app (works with WebBrowser.openAuthSessionAsync)
            from urllib.parse import urlencode

            params = urlencode(
                {
                    "platform": platform.value,
                    "connection_id": str(connection.id),
                    "status": "success",
                }
            )
            redirect_url = f"{client_redirect_uri}?{params}"
            logger.info(f"Redirecting to client: {redirect_url}")
            return RedirectResponse(url=redirect_url, status_code=302)
        else:
            # Fallback to HTML page for web browsers
            return create_html_response(
                success=True,
                platform=platform.value,
                message=f"Successfully connected to {platform.value.replace('_', ' ').title()}!",
                connection_id=str(connection.id),
            )

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")

        # Emit CONNECTION_FAILED event if connection exists
        if connection:
            await _emit_connection_event(
                EventType.CONNECTION_FAILED,
                connection.id,
                platform.value,
                connection.user_id,
                error=str(e),
            )

            # Check for client redirect URI
            client_redirect_uri = connection.platform_metadata.get(
                "client_redirect_uri"
            )
            if client_redirect_uri:
                from urllib.parse import urlencode

                params = urlencode(
                    {
                        "platform": platform.value,
                        "status": "error",
                        "error": str(e)[:100],
                    }
                )
                return RedirectResponse(
                    url=f"{client_redirect_uri}?{params}", status_code=302
                )

        return create_html_response(
            success=False,
            platform=platform.value,
            message=f"Connection failed: {str(e)[:100]}",
        )


@router.get(
    "",
    response_model=ConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List connections",
    description="List all platform connections for a user",
)
async def list_connections(
    user_id: UUID = Query(..., description="User ID to filter connections"),
    platform: PlatformType | None = Query(
        default=None, description="Optional platform filter"
    ),
    status_filter: ConnectionStatus | None = Query(
        default=None, alias="status", description="Optional status filter"
    ),
    db: AsyncSession = Depends(get_database_session),
) -> ConnectionListResponse:
    """
    List platform connections.

    Returns all connections for a user, optionally filtered by platform and status.

    Args:
        user_id: User ID to filter connections
        platform: Optional platform filter
        status_filter: Optional status filter
        db: Database session

    Returns:
        List of connections
    """
    try:
        # Build query
        query = select(PlatformConnection).where(PlatformConnection.user_id == user_id)

        if platform:
            query = query.where(PlatformConnection.platform == platform)

        if status_filter:
            query = query.where(PlatformConnection.status == status_filter)

        # Execute query
        result = await db.execute(query)
        connections = result.scalars().all()

        return ConnectionListResponse(
            connections=[_connection_to_response(conn) for conn in connections],
            total=len(connections),
        )

    except Exception as e:
        logger.error(f"Failed to list connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}",
        )


@router.patch(
    "/{connection_id}/status",
    response_model=ConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update connection status",
    description="Update the status of a connection (used after WhatsApp bridge login)",
)
async def update_connection_status(
    connection_id: UUID,
    new_status: ConnectionStatus = Query(..., description="New connection status"),
    db: AsyncSession = Depends(get_database_session),
) -> ConnectionResponse:
    """
    Update connection status.

    Used to mark a connection as ACTIVE after successful login (e.g., WhatsApp bridge).

    Args:
        connection_id: Connection ID to update
        new_status: New status value
        db: Database session

    Returns:
        Updated connection details
    """
    try:
        result = await db.execute(
            select(PlatformConnection).where(PlatformConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        connection.status = new_status
        await db.commit()
        await db.refresh(connection)

        # Emit appropriate event
        if new_status == ConnectionStatus.ACTIVE:
            await _emit_connection_event(
                EventType.CONNECTION_ESTABLISHED,
                connection.id,
                connection.platform.value,
                connection.user_id,
            )

        logger.info(f"Updated connection {connection_id} status to {new_status.value}")

        return _connection_to_response(connection)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update connection status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}",
        )


@router.delete(
    "/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect platform",
    description="Disconnect and remove a platform connection",
)
async def disconnect_platform(
    connection_id: str, db: AsyncSession = Depends(get_database_session)
) -> None:
    """
    Disconnect from a platform.

    This endpoint:
    1. Disconnects the connector
    2. Revokes credentials
    3. Updates connection status
    4. Emits CONNECTION_REVOKED event

    Args:
        connection_id: Connection ID to disconnect
        db: Database session

    Raises:
        HTTPException: If connection not found
    """
    try:
        # Find connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == UUID(connection_id)
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        # Get connector and disconnect
        connector_class = _get_connector_class(connection.platform)
        if connector_class and connection.credentials:
            try:
                connector = connector_class(
                    connection_id=connection.id, credentials=connection.credentials
                )
                await connector.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect connector: {e}")

        # Update connection status
        connection.status = ConnectionStatus.REVOKED
        await db.commit()

        # Emit CONNECTION_REVOKED event
        await _emit_connection_event(
            EventType.CONNECTION_REVOKED,
            connection.id,
            connection.platform.value,
            connection.user_id,
        )

        logger.info(
            f"Disconnected {connection.platform.value} connection {connection_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}",
        )


@router.get(
    "/{connection_id}/health",
    response_model=ConnectionHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check connection health",
    description="Perform health check on a platform connection",
)
async def check_connection_health(
    connection_id: str = Depends(validate_uuid),
    db: AsyncSession = Depends(get_database_session),
) -> ConnectionHealthResponse:
    """
    Check health of a platform connection.

    Performs a health check on the connector and returns detailed status.

    Args:
        connection_id: Connection ID to check
        db: Database session

    Returns:
        Health status details

    Raises:
        HTTPException: If connection not found
    """
    try:
        # Find connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == UUID(connection_id)
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        # Get connector class
        connector_class = _get_connector_class(connection.platform)
        if not connector_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {connection.platform.value} not supported",
            )

        # Create connector and perform health check
        connector = connector_class(
            connection_id=connection.id, credentials=connection.credentials
        )

        # Connect if not already connected
        if not connector.is_connected:
            await connector.connect()

        # Perform health check
        health = await connector.health_check()

        return ConnectionHealthResponse(
            connection_id=connection.id,
            platform=connection.platform.value,
            health_status=health.status.value,
            connector_status=health.connector_status.value,
            last_check_at=health.last_check_at.isoformat(),
            last_success_at=(
                health.last_success_at.isoformat() if health.last_success_at else None
            ),
            last_error_at=(
                health.last_error_at.isoformat() if health.last_error_at else None
            ),
            last_error=health.last_error,
            consecutive_failures=health.consecutive_failures,
            circuit_breaker_open=health.circuit_breaker_open,
            metadata=health.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )
