"""
LinkedIn Connector

Implements LinkedIn integration with:
- OAuth 2.0 authentication
- LinkedIn Messaging API for DMs
- Connections API for contact sync
- Profile API for contact enrichment

LinkedIn API Documentation:
- Marketing API: https://docs.microsoft.com/en-us/linkedin/marketing/
- Consumer API (deprecated for new apps): Most messaging features require partnership
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from integrations.base_connector import (
    BaseConnector,
    ConnectionError,
    AuthenticationError,
    RateLimitError,
)


logger = logging.getLogger(__name__)


# =============================================================================
# LinkedIn API Constants
# =============================================================================

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"

# OAuth Scopes
# Note: Messaging API requires LinkedIn partnership approval
LINKEDIN_SCOPES = [
    "r_liteprofile",      # Basic profile read
    "r_emailaddress",     # Email address read
    "w_member_social",    # Post updates
    # Partnership required:
    # "r_1st_connections_size",  # Connection count
    # "r_messaging",             # Read messages
    # "w_messaging",             # Send messages
]


# =============================================================================
# LinkedIn Connector
# =============================================================================

class LinkedInConnector(BaseConnector):
    """
    LinkedIn platform connector.
    
    Provides:
    - OAuth 2.0 authentication with LinkedIn
    - Profile information retrieval
    - Connection sync (limited without partnership)
    - Message access (requires LinkedIn partnership)
    
    Note: Full messaging API access requires LinkedIn partnership program approval.
    This implementation provides the foundation for when partnership is obtained.
    """
    
    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 100,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize LinkedIn connector.
        
        Args:
            connection_id: Unique identifier for this connection
            credentials: OAuth credentials from LinkedIn
            rate_limit_per_minute: LinkedIn API rate limit (default: 100)
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_timeout: Seconds before circuit resets
        """
        super().__init__(
            connection_id=connection_id,
            credentials=credentials,
            rate_limit_per_minute=rate_limit_per_minute,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )
        self._http_client: Optional[httpx.AsyncClient] = None
        self._profile: Optional[Dict[str, Any]] = None
        self._token_expires_at: Optional[datetime] = None
    
    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "linkedin"
    
    async def _connect(self) -> None:
        """
        Establish connection to LinkedIn API.
        
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
                base_url=LINKEDIN_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.credentials['access_token']}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                    "LinkedIn-Version": "202312",  # Use dated version
                },
                timeout=30.0,
            )
            
            # Set token expiration if provided
            if self.credentials.get("expires_in"):
                self._token_expires_at = datetime.utcnow() + timedelta(
                    seconds=self.credentials["expires_in"]
                )
            
            # Validate connection by fetching profile
            await self._test_connection()
            
            logger.info(f"LinkedIn connector {self.connection_id} connected successfully")
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"LinkedIn connection failed: {e}")
            raise ConnectionError(f"Failed to connect to LinkedIn: {e}")
    
    async def _disconnect(self) -> None:
        """
        Disconnect from LinkedIn API.
        
        Cleans up HTTP client.
        """
        try:
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None
            
            self._profile = None
            logger.info(f"LinkedIn connector {self.connection_id} disconnected")
            
        except Exception as e:
            logger.warning(f"Error during LinkedIn disconnect: {e}")
    
    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth token.
        
        LinkedIn access tokens are typically long-lived (60 days) but 
        can be refreshed using the refresh_token.
        
        Returns:
            Updated credentials dictionary
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        try:
            refresh_token = self.credentials.get("refresh_token")
            if not refresh_token:
                raise AuthenticationError("No refresh token available")
            
            client_id = self.credentials.get("client_id")
            client_secret = self.credentials.get("client_secret")
            
            if not client_id or not client_secret:
                raise AuthenticationError("Missing client credentials for refresh")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    LINKEDIN_TOKEN_URL,
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
            self.credentials["expires_in"] = token_data.get("expires_in", 5184000)  # 60 days default
            
            # Update expiration
            self._token_expires_at = datetime.utcnow() + timedelta(
                seconds=self.credentials["expires_in"]
            )
            
            # Update HTTP client headers
            if self._http_client:
                self._http_client.headers["Authorization"] = f"Bearer {token_data['access_token']}"
            
            logger.info(f"LinkedIn connector {self.connection_id} token refreshed")
            return self.credentials
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn token refresh failed: {e.response.text}")
            raise AuthenticationError(f"Token refresh failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LinkedIn token refresh error: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")
    
    async def _check_health(self) -> Dict[str, Any]:
        """
        Perform health check on LinkedIn connection.
        
        Returns:
            Health metadata including profile info and token status
            
        Raises:
            Exception: If health check fails
        """
        health_data = {
            "token_valid": False,
            "token_expires_at": None,
            "profile": None,
        }
        
        try:
            # Check if token is still valid
            if self._token_expires_at:
                health_data["token_expires_at"] = self._token_expires_at.isoformat()
                health_data["token_valid"] = datetime.utcnow() < self._token_expires_at
            
            # Fetch profile to verify connection
            profile = await self.get_profile()
            health_data["profile"] = {
                "id": profile.get("id"),
                "name": f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}".strip(),
            }
            health_data["token_valid"] = True
            
        except Exception as e:
            logger.warning(f"LinkedIn health check failed: {e}")
            health_data["error"] = str(e)
        
        return health_data
    
    async def _test_connection(self) -> None:
        """
        Test LinkedIn API connection with a simple request.
        
        Raises:
            ConnectionError: If test fails
        """
        try:
            profile = await self.get_profile()
            self._profile = profile
            logger.debug(f"LinkedIn connection test passed for {profile.get('id')}")
        except Exception as e:
            raise ConnectionError(f"LinkedIn connection test failed: {e}")
    
    # =========================================================================
    # Profile API
    # =========================================================================
    
    async def get_profile(self) -> Dict[str, Any]:
        """
        Get the authenticated user's LinkedIn profile.
        
        Returns:
            Profile data dictionary
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        if not await self._check_rate_limit():
            raise RateLimitError("LinkedIn rate limit exceeded")
        
        try:
            response = await self._http_client.get("/me")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("LinkedIn rate limit exceeded")
            elif e.response.status_code == 401:
                raise AuthenticationError("Invalid or expired token")
            raise ConnectionError(f"Failed to get profile: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get profile: {e}")
    
    async def get_email(self) -> Optional[str]:
        """
        Get the authenticated user's primary email address.
        
        Returns:
            Email address or None
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        if not await self._check_rate_limit():
            raise RateLimitError("LinkedIn rate limit exceeded")
        
        try:
            response = await self._http_client.get(
                "/emailAddress",
                params={"q": "members", "projection": "(elements*(handle~))"},
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract email from response
            elements = data.get("elements", [])
            if elements:
                handle = elements[0].get("handle~", {})
                return handle.get("emailAddress")
            return None
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("LinkedIn rate limit exceeded")
            logger.warning(f"Failed to get email: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get email: {e}")
            return None
    
    # =========================================================================
    # Connections API (Limited without partnership)
    # =========================================================================
    
    async def get_connections_count(self) -> int:
        """
        Get the count of first-degree connections.
        
        Note: Requires r_1st_connections_size scope (partnership).
        
        Returns:
            Number of connections
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        if not await self._check_rate_limit():
            raise RateLimitError("LinkedIn rate limit exceeded")
        
        try:
            response = await self._http_client.get("/connections?q=viewer&count=0")
            response.raise_for_status()
            data = response.json()
            return data.get("paging", {}).get("total", 0)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("Connections API requires partnership approval")
                return 0
            elif e.response.status_code == 429:
                raise RateLimitError("LinkedIn rate limit exceeded")
            raise ConnectionError(f"Failed to get connections count: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get connections count: {e}")
    
    # =========================================================================
    # Messaging API (Requires LinkedIn Partnership)
    # =========================================================================
    
    async def list_conversations(
        self,
        count: int = 20,
        start: int = 0,
    ) -> Dict[str, Any]:
        """
        List messaging conversations.
        
        Note: Requires r_messaging scope (LinkedIn partnership).
        
        Args:
            count: Number of conversations to retrieve
            start: Pagination start
            
        Returns:
            Conversations data
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
            AuthenticationError: If messaging scope not granted
        """
        if not await self._check_rate_limit():
            raise RateLimitError("LinkedIn rate limit exceeded")
        
        try:
            response = await self._http_client.get(
                "/messaging/conversations",
                params={"start": start, "count": count},
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise AuthenticationError(
                    "Messaging API requires LinkedIn partnership. "
                    "Apply at: https://docs.microsoft.com/en-us/linkedin/marketing/apply-for-marketing-api-access"
                )
            elif e.response.status_code == 429:
                raise RateLimitError("LinkedIn rate limit exceeded")
            raise ConnectionError(f"Failed to list conversations: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to list conversations: {e}")
    
    async def get_messages(
        self,
        conversation_id: str,
        count: int = 50,
        start: int = 0,
    ) -> Dict[str, Any]:
        """
        Get messages from a specific conversation.
        
        Note: Requires r_messaging scope (LinkedIn partnership).
        
        Args:
            conversation_id: LinkedIn conversation ID
            count: Number of messages to retrieve
            start: Pagination start
            
        Returns:
            Messages data
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        if not await self._check_rate_limit():
            raise RateLimitError("LinkedIn rate limit exceeded")
        
        try:
            response = await self._http_client.get(
                f"/messaging/conversations/{conversation_id}/events",
                params={"start": start, "count": count},
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise AuthenticationError("Messaging API requires LinkedIn partnership")
            elif e.response.status_code == 429:
                raise RateLimitError("LinkedIn rate limit exceeded")
            raise ConnectionError(f"Failed to get messages: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get messages: {e}")
    
    async def send_message(
        self,
        conversation_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Send a message to a conversation.
        
        Note: Requires w_messaging scope (LinkedIn partnership).
        
        Args:
            conversation_id: LinkedIn conversation ID
            message: Message text
            
        Returns:
            Sent message data
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        if not await self._check_rate_limit():
            raise RateLimitError("LinkedIn rate limit exceeded")
        
        try:
            response = await self._http_client.post(
                f"/messaging/conversations/{conversation_id}/events",
                json={
                    "eventCreate": {
                        "value": {
                            "com.linkedin.voyager.messaging.create.MessageCreate": {
                                "body": message,
                                "attachments": [],
                            }
                        }
                    }
                },
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise AuthenticationError("Messaging API requires LinkedIn partnership")
            elif e.response.status_code == 429:
                raise RateLimitError("LinkedIn rate limit exceeded")
            raise ConnectionError(f"Failed to send message: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {e}")
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self._token_expires_at:
            return False
        return datetime.utcnow() >= self._token_expires_at
    
    def token_expires_in_seconds(self) -> Optional[int]:
        """Get seconds until token expiration."""
        if not self._token_expires_at:
            return None
        delta = self._token_expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


# =============================================================================
# OAuth Helper Functions
# =============================================================================

def get_linkedin_auth_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: Optional[List[str]] = None,
) -> str:
    """
    Generate LinkedIn OAuth authorization URL.
    
    Args:
        client_id: LinkedIn app client ID
        redirect_uri: OAuth callback URL
        state: CSRF protection state
        scopes: Optional custom scopes (defaults to LINKEDIN_SCOPES)
        
    Returns:
        Authorization URL
    """
    if scopes is None:
        scopes = LINKEDIN_SCOPES
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(scopes),
    }
    
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{LINKEDIN_AUTH_URL}?{query}"


async def exchange_linkedin_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from callback
        client_id: LinkedIn app client ID
        client_secret: LinkedIn app client secret
        redirect_uri: OAuth callback URL
        
    Returns:
        Token response with access_token, expires_in, etc.
        
    Raises:
        AuthenticationError: If exchange fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                LINKEDIN_TOKEN_URL,
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
        logger.error(f"LinkedIn token exchange failed: {e.response.text}")
        raise AuthenticationError(f"Token exchange failed: {e.response.status_code}")
    except Exception as e:
        logger.error(f"LinkedIn token exchange error: {e}")
        raise AuthenticationError(f"Token exchange failed: {e}")


def get_linkedin_config() -> Dict[str, Any]:
    """
    Get LinkedIn OAuth configuration from environment variables.
    
    Returns:
        Dictionary with LinkedIn OAuth config:
        - client_id: LinkedIn app client ID
        - client_secret: LinkedIn app client secret
        - redirect_uri: OAuth callback URL
        - scopes: List of OAuth scopes
        
    Raises:
        ValueError: If required environment variables are missing
    """
    import os
    
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "LINKEDIN_REDIRECT_URI",
        "http://localhost:8000/api/v1/connections/callback/linkedin"
    )
    scopes_str = os.getenv(
        "LINKEDIN_SCOPES",
        "r_liteprofile,r_emailaddress,w_member_social"
    )
    
    if not client_id or not client_secret:
        raise ValueError(
            "LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID and "
            "LINKEDIN_CLIENT_SECRET environment variables."
        )
    
    # Parse scopes (comma or space separated)
    scopes = [s.strip() for s in scopes_str.replace(",", " ").split() if s.strip()]
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
    }


def is_linkedin_configured() -> bool:
    """
    Check if LinkedIn OAuth is properly configured.
    
    Returns:
        True if LinkedIn credentials are set and valid
    """
    import os
    
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    
    # Check for placeholder values
    placeholders = ["your-", "your_", "placeholder", "xxx"]
    
    if not client_id or not client_secret:
        return False
    
    for placeholder in placeholders:
        if placeholder in client_id.lower() or placeholder in client_secret.lower():
            return False
    
    return True

