"""
Google Chat Connector

Implements Google Chat (Workspace) integration with:
- OAuth 2.0 authentication
- Chat Spaces API for rooms/DMs
- Messages API for sending/receiving

Note: Google Chat API requires:
1. Google Workspace account (not personal Gmail)
2. Chat API enabled in Google Cloud Console
3. OAuth 2.0 Client credentials

API Documentation:
- https://developers.google.com/chat/api/reference/rest
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from integrations.base_connector import (
    AuthenticationError,
    BaseConnector,
    ConnectionError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Google Chat API Constants
# =============================================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CHAT_API_BASE = "https://chat.googleapis.com/v1"

# OAuth Scopes for Google Chat
GOOGLE_CHAT_SCOPES = [
    "https://www.googleapis.com/auth/chat.spaces.readonly",  # Read spaces
    "https://www.googleapis.com/auth/chat.messages.readonly",  # Read messages
    "https://www.googleapis.com/auth/chat.messages.create",  # Send messages
    "https://www.googleapis.com/auth/chat.memberships.readonly",  # Read members
]


# =============================================================================
# Google Chat Connector
# =============================================================================


class GoogleChatConnector(BaseConnector):
    """
    Google Chat platform connector.

    Provides:
    - OAuth 2.0 authentication with Google
    - Chat Spaces listing (rooms, DMs, group chats)
    - Message retrieval and sending
    - Member information

    Requirements:
    - Google Workspace account (not personal Gmail)
    - Chat API enabled in Cloud Console
    """

    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 180,  # Google Chat: 180 requests/minute
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize Google Chat connector.

        Args:
            connection_id: Unique identifier for this connection
            credentials: OAuth credentials from Google
            rate_limit_per_minute: API rate limit (default: 180)
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_timeout: Seconds before recovery
        """
        super().__init__(
            connection_id=connection_id,
            credentials=credentials,
            rate_limit_per_minute=rate_limit_per_minute,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )
        self._http_client: Optional[httpx.AsyncClient] = None
        self._user_info: Optional[Dict[str, Any]] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "google_chat"

    async def _connect(self) -> None:
        """
        Establish connection to Google Chat API.

        Validates credentials and creates HTTP client.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If credentials are invalid
        """
        try:
            # Validate credentials
            if not self.credentials.get("access_token"):
                raise AuthenticationError("No access token provided")

            # Create HTTP client with auth headers
            self._http_client = httpx.AsyncClient(
                base_url=GOOGLE_CHAT_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.credentials['access_token']}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            # Set token expiration if provided
            if self.credentials.get("expires_in"):
                self._token_expires_at = datetime.utcnow() + timedelta(
                    seconds=self.credentials["expires_in"]
                )

            # Validate connection by listing spaces
            await self._test_connection()

            logger.info(
                f"Google Chat connector {self.connection_id} connected successfully"
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Google Chat connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Google Chat: {e}")

    async def _disconnect(self) -> None:
        """Disconnect from Google Chat API."""
        try:
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None

            self._user_info = None
            logger.info(f"Google Chat connector {self.connection_id} disconnected")

        except Exception as e:
            logger.warning(f"Error during Google Chat disconnect: {e}")

    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth token.

        Returns:
            Updated credentials dictionary

        Raises:
            AuthenticationError: If token refresh fails
        """
        try:
            refresh_token = self.credentials.get("refresh_token")
            if not refresh_token:
                raise AuthenticationError("No refresh token available")

            client_id = self.credentials.get("client_id") or os.getenv(
                "GMAIL_CLIENT_ID"
            )
            client_secret = self.credentials.get("client_secret") or os.getenv(
                "GMAIL_CLIENT_SECRET"
            )

            if not client_id or not client_secret:
                raise AuthenticationError("Missing client credentials for refresh")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )
                response.raise_for_status()
                token_data = response.json()

            # Update credentials
            self.credentials["access_token"] = token_data["access_token"]
            if "refresh_token" in token_data:
                self.credentials["refresh_token"] = token_data["refresh_token"]
            self.credentials["expires_in"] = token_data.get("expires_in", 3600)

            # Update expiration
            self._token_expires_at = datetime.utcnow() + timedelta(
                seconds=self.credentials["expires_in"]
            )

            # Update HTTP client headers
            if self._http_client:
                self._http_client.headers["Authorization"] = (
                    f"Bearer {token_data['access_token']}"
                )

            logger.info(f"Google Chat connector {self.connection_id} token refreshed")
            return self.credentials

        except httpx.HTTPStatusError as e:
            logger.error(f"Google Chat token refresh failed: {e.response.text}")
            raise AuthenticationError(f"Token refresh failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Google Chat token refresh error: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")

    async def _check_health(self) -> Dict[str, Any]:
        """Perform health check on Google Chat connection."""
        health_data = {
            "token_valid": False,
            "token_expires_at": None,
            "spaces_count": 0,
        }

        try:
            if self._token_expires_at:
                health_data["token_expires_at"] = self._token_expires_at.isoformat()
                health_data["token_valid"] = datetime.utcnow() < self._token_expires_at

            # Fetch spaces to verify connection
            spaces = await self.list_spaces()
            health_data["spaces_count"] = len(spaces.get("spaces", []))
            health_data["token_valid"] = True

        except Exception as e:
            logger.warning(f"Google Chat health check failed: {e}")
            health_data["error"] = str(e)

        return health_data

    async def _test_connection(self) -> None:
        """Test Google Chat API connection."""
        try:
            await self.list_spaces(page_size=1)
            logger.debug("Google Chat connection test passed")
        except Exception as e:
            raise ConnectionError(f"Google Chat connection test failed: {e}")

    # =========================================================================
    # Spaces API (Rooms, DMs, Group Chats)
    # =========================================================================

    async def list_spaces(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List chat spaces (rooms, DMs, group chats).

        Args:
            page_size: Max spaces per page (1-1000)
            page_token: Pagination token
            filter: Filter string (e.g., "spaceType = 'DIRECT_MESSAGE'")

        Returns:
            Spaces data with pagination

        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        if not await self._check_rate_limit():
            raise RateLimitError("Google Chat rate limit exceeded")

        try:
            params = {"pageSize": min(page_size, 1000)}
            if page_token:
                params["pageToken"] = page_token
            if filter:
                params["filter"] = filter

            response = await self._http_client.get("/spaces", params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("Google Chat rate limit exceeded")
            elif e.response.status_code == 401:
                raise AuthenticationError("Invalid or expired token")
            raise ConnectionError(f"Failed to list spaces: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to list spaces: {e}")

    async def get_space(self, space_name: str) -> Dict[str, Any]:
        """
        Get details of a specific space.

        Args:
            space_name: Space resource name (e.g., "spaces/AAAA...")

        Returns:
            Space details
        """
        if not await self._check_rate_limit():
            raise RateLimitError("Google Chat rate limit exceeded")

        try:
            # space_name should be like "spaces/AAABBB..."
            if not space_name.startswith("spaces/"):
                space_name = f"spaces/{space_name}"

            response = await self._http_client.get(f"/{space_name}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConnectionError(f"Space not found: {space_name}")
            raise ConnectionError(f"Failed to get space: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get space: {e}")

    # =========================================================================
    # Messages API
    # =========================================================================

    async def list_messages(
        self,
        space_name: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
        order_by: str = "createTime desc",
        show_deleted: bool = False,
    ) -> Dict[str, Any]:
        """
        List messages in a space.

        Args:
            space_name: Space resource name
            page_size: Max messages per page
            page_token: Pagination token
            order_by: Sort order (default: newest first)
            show_deleted: Include deleted messages

        Returns:
            Messages data with pagination
        """
        if not await self._check_rate_limit():
            raise RateLimitError("Google Chat rate limit exceeded")

        try:
            if not space_name.startswith("spaces/"):
                space_name = f"spaces/{space_name}"

            params = {
                "pageSize": min(page_size, 1000),
                "orderBy": order_by,
                "showDeleted": str(show_deleted).lower(),
            }
            if page_token:
                params["pageToken"] = page_token

            response = await self._http_client.get(
                f"/{space_name}/messages", params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("Google Chat rate limit exceeded")
            raise ConnectionError(f"Failed to list messages: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to list messages: {e}")

    async def get_message(self, message_name: str) -> Dict[str, Any]:
        """
        Get a specific message.

        Args:
            message_name: Message resource name (e.g., "spaces/AAAA/messages/BBBB")

        Returns:
            Message details
        """
        if not await self._check_rate_limit():
            raise RateLimitError("Google Chat rate limit exceeded")

        try:
            response = await self._http_client.get(f"/{message_name}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConnectionError(f"Message not found: {message_name}")
            raise ConnectionError(f"Failed to get message: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get message: {e}")

    async def send_message(
        self,
        space_name: str,
        text: str,
        thread_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a space.

        Args:
            space_name: Space resource name
            text: Message text
            thread_key: Optional thread key for threaded replies

        Returns:
            Created message data
        """
        if not await self._check_rate_limit():
            raise RateLimitError("Google Chat rate limit exceeded")

        try:
            if not space_name.startswith("spaces/"):
                space_name = f"spaces/{space_name}"

            body = {"text": text}

            params = {}
            if thread_key:
                params["threadKey"] = thread_key
                params["messageReplyOption"] = "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"

            response = await self._http_client.post(
                f"/{space_name}/messages", json=body, params=params if params else None
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("Google Chat rate limit exceeded")
            raise ConnectionError(f"Failed to send message: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {e}")

    # =========================================================================
    # Members API
    # =========================================================================

    async def list_members(
        self,
        space_name: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List members in a space.

        Args:
            space_name: Space resource name
            page_size: Max members per page
            page_token: Pagination token

        Returns:
            Members data with pagination
        """
        if not await self._check_rate_limit():
            raise RateLimitError("Google Chat rate limit exceeded")

        try:
            if not space_name.startswith("spaces/"):
                space_name = f"spaces/{space_name}"

            params = {"pageSize": min(page_size, 1000)}
            if page_token:
                params["pageToken"] = page_token

            response = await self._http_client.get(
                f"/{space_name}/members", params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"Failed to list members: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to list members: {e}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self._token_expires_at:
            return False
        return datetime.utcnow() >= self._token_expires_at


# =============================================================================
# OAuth Helper Functions
# =============================================================================


def get_google_chat_auth_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: Optional[List[str]] = None,
) -> str:
    """
    Generate Google Chat OAuth authorization URL.

    Args:
        client_id: Google app client ID
        redirect_uri: OAuth callback URL
        state: CSRF protection state
        scopes: Optional custom scopes (defaults to GOOGLE_CHAT_SCOPES)

    Returns:
        Authorization URL
    """
    if scopes is None:
        scopes = GOOGLE_CHAT_SCOPES

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    from urllib.parse import urlencode

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_chat_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.

    Args:
        code: Authorization code from callback
        client_id: Google app client ID
        client_secret: Google app client secret
        redirect_uri: OAuth callback URL

    Returns:
        Token response with access_token, expires_in, etc.

    Raises:
        AuthenticationError: If exchange fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Google Chat token exchange failed: {e.response.text}")
        raise AuthenticationError(f"Token exchange failed: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Google Chat token exchange error: {e}")
        raise AuthenticationError(f"Token exchange failed: {e}")


def get_google_chat_config() -> Dict[str, Any]:
    """
    Get Google Chat OAuth config from environment variables.

    Note: Uses same credentials as Gmail (same Google Cloud project).

    Returns:
        Dictionary with Google Chat OAuth config

    Raises:
        ValueError: If required environment variables are missing
    """
    # Uses same Google OAuth credentials as Gmail
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_CHAT_REDIRECT_URI",
        "http://localhost:8000/api/v1/connections/callback/google_chat",
    )

    if not client_id or not client_secret:
        raise ValueError(
            "Google Chat OAuth not configured. Set GMAIL_CLIENT_ID and "
            "GMAIL_CLIENT_SECRET environment variables."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": GOOGLE_CHAT_SCOPES,
    }


def is_google_chat_configured() -> bool:
    """Check if Google Chat OAuth is properly configured."""
    # Uses same credentials as Gmail
    from integrations.gmail_connector import is_gmail_configured

    return is_gmail_configured()
