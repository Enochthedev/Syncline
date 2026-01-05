"""
Gmail Connector

Implements Gmail integration with:
- OAuth 2.0 authentication
- Gmail API client wrapper
- Webhook registration for push notifications
- Automatic token refresh
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from integrations.base_connector import (
    BaseConnector,
    AuthenticationError,
    ConnectionError,
    RateLimitError,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Gmail Connector
# =============================================================================

class GmailConnector(BaseConnector):
    """
    Gmail platform connector.
    
    Provides:
    - OAuth 2.0 authentication with Google
    - Gmail API access for reading messages
    - Push notification support via webhooks
    - Automatic token refresh
    """
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.metadata',
    ]
    
    # Gmail API endpoints
    GMAIL_API_VERSION = 'v1'
    
    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 250,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize Gmail connector.
        
        Args:
            connection_id: Unique identifier for this connection
            credentials: OAuth credentials from Google
            rate_limit_per_minute: Gmail API rate limit (default: 250)
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds before attempting recovery
        """
        super().__init__(
            connection_id=connection_id,
            credentials=credentials,
            rate_limit_per_minute=rate_limit_per_minute,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )
        
        self._service = None
        self._watch_expiration: Optional[datetime] = None
    
    # =========================================================================
    # BaseConnector Implementation
    # =========================================================================
    
    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "gmail"
    
    async def _connect(self) -> None:
        """
        Establish connection to Gmail API.
        
        Validates credentials and creates Gmail service client.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If credentials are invalid
        """
        try:
            # Create Google OAuth credentials
            creds = self._create_credentials()
            
            # Validate credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Token expired but can be refreshed
                    logger.info("Gmail credentials expired, refreshing...")
                    await self._refresh_token()
                    creds = self._create_credentials()
                else:
                    raise AuthenticationError(
                        "Invalid Gmail credentials - no refresh token available"
                    )
            
            # Build Gmail service
            self._service = build(
                'gmail',
                self.GMAIL_API_VERSION,
                credentials=creds,
                cache_discovery=False
            )
            
            # Test connection with a simple API call
            await self._test_connection()
            
            logger.info(f"Gmail connector {self.connection_id} connected successfully")
            
        except HttpError as e:
            error_msg = f"Gmail API error: {e.resp.status} - {e.error_details}"
            logger.error(error_msg)
            
            if e.resp.status == 401:
                raise AuthenticationError(error_msg)
            elif e.resp.status == 429:
                raise RateLimitError(error_msg)
            else:
                raise ConnectionError(error_msg)
                
        except Exception as e:
            error_msg = f"Failed to connect to Gmail: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    async def _disconnect(self) -> None:
        """
        Disconnect from Gmail API.
        
        Cleans up service client and stops push notifications.
        """
        try:
            # Stop watching for push notifications if active
            if self._watch_expiration:
                await self.stop_watch()
            
            # Clear service client
            self._service = None
            
            logger.info(f"Gmail connector {self.connection_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting Gmail: {e}")
            raise
    
    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth token.
        
        Returns:
            Updated credentials dictionary
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        try:
            # Create credentials object
            creds = self._create_credentials()
            
            if not creds.refresh_token:
                raise AuthenticationError("No refresh token available")
            
            # Refresh the token
            creds.refresh(Request())
            
            # Update credentials dictionary
            new_credentials = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }
            
            if creds.expiry:
                new_credentials["expires_at"] = creds.expiry.isoformat()
            
            logger.info(f"Gmail token refreshed for connection {self.connection_id}")
            
            return new_credentials
            
        except Exception as e:
            error_msg = f"Failed to refresh Gmail token: {str(e)}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)
    
    async def _check_health(self) -> Dict[str, Any]:
        """
        Perform health check on Gmail connection.
        
        Returns:
            Health metadata including profile info and watch status
            
        Raises:
            Exception: If health check fails
        """
        try:
            # Get user profile to verify connection
            profile = self._service.users().getProfile(userId='me').execute()
            
            # Check watch status
            watch_active = self._watch_expiration is not None
            watch_expires_at = None
            if self._watch_expiration:
                watch_expires_at = self._watch_expiration.isoformat()
            
            return {
                "email_address": profile.get("emailAddress"),
                "messages_total": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId"),
                "watch_active": watch_active,
                "watch_expires_at": watch_expires_at,
            }
            
        except HttpError as e:
            if e.resp.status == 429:
                raise RateLimitError(f"Gmail API rate limit exceeded: {e}")
            raise Exception(f"Gmail health check failed: {e}")
        except Exception as e:
            raise Exception(f"Gmail health check failed: {e}")
    
    # =========================================================================
    # Gmail-Specific Methods
    # =========================================================================
    
    def _create_credentials(self) -> Credentials:
        """
        Create Google OAuth credentials from stored credentials.
        
        Returns:
            Google Credentials object
        """
        return Credentials(
            token=self.credentials.get("access_token"),
            refresh_token=self.credentials.get("refresh_token"),
            token_uri=self.credentials.get(
                "token_uri",
                "https://oauth2.googleapis.com/token"
            ),
            client_id=self.credentials.get("client_id"),
            client_secret=self.credentials.get("client_secret"),
            scopes=self.credentials.get("scopes", self.SCOPES),
        )
    
    async def _test_connection(self) -> None:
        """
        Test Gmail API connection with a simple request.
        
        Raises:
            ConnectionError: If test fails
        """
        try:
            # Simple API call to verify connection
            self._service.users().getProfile(userId='me').execute()
        except Exception as e:
            raise ConnectionError(f"Gmail connection test failed: {e}")
    
    # =========================================================================
    # Message Operations
    # =========================================================================
    
    async def list_messages(
        self,
        max_results: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List messages from Gmail.
        
        Args:
            max_results: Maximum number of messages to return
            page_token: Token for pagination
            query: Gmail search query (optional)
            
        Returns:
            Dictionary with messages and next page token
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        try:
            # Check rate limit
            if not await self.check_rate_limit():
                raise RateLimitError("Gmail rate limit exceeded")
            
            # Build request parameters
            params = {
                'userId': 'me',
                'maxResults': max_results,
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            if query:
                params['q'] = query
            
            # Execute request
            result = self._service.users().messages().list(**params).execute()
            
            return {
                "messages": result.get("messages", []),
                "next_page_token": result.get("nextPageToken"),
                "result_size_estimate": result.get("resultSizeEstimate", 0),
            }
            
        except HttpError as e:
            if e.resp.status == 429:
                raise RateLimitError(f"Gmail API rate limit: {e}")
            raise ConnectionError(f"Failed to list messages: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to list messages: {e}")
    
    async def get_message(
        self,
        message_id: str,
        format: str = "full",
    ) -> Dict[str, Any]:
        """
        Get a specific message by ID.
        
        Args:
            message_id: Gmail message ID
            format: Message format (minimal, full, raw, metadata)
            
        Returns:
            Message data dictionary
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        try:
            # Check rate limit
            if not await self.check_rate_limit():
                raise RateLimitError("Gmail rate limit exceeded")
            
            # Execute request
            message = self._service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
            
            return message
            
        except HttpError as e:
            if e.resp.status == 429:
                raise RateLimitError(f"Gmail API rate limit: {e}")
            raise ConnectionError(f"Failed to get message: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get message: {e}")
    
    # =========================================================================
    # Push Notification Support
    # =========================================================================
    
    async def start_watch(
        self,
        topic_name: str,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Start watching for Gmail push notifications.
        
        Args:
            topic_name: Google Cloud Pub/Sub topic name
            label_ids: Optional list of label IDs to watch
            
        Returns:
            Watch response with history ID and expiration
            
        Raises:
            ConnectionError: If watch setup fails
        """
        try:
            # Build watch request
            request_body = {
                'topicName': topic_name,
            }
            
            if label_ids:
                request_body['labelIds'] = label_ids
            
            # Execute watch request
            watch_response = self._service.users().watch(
                userId='me',
                body=request_body
            ).execute()
            
            # Store expiration time
            expiration_ms = int(watch_response.get('expiration', 0))
            self._watch_expiration = datetime.fromtimestamp(expiration_ms / 1000)
            
            logger.info(
                f"Gmail watch started for connection {self.connection_id}, "
                f"expires at {self._watch_expiration}"
            )
            
            return watch_response
            
        except HttpError as e:
            raise ConnectionError(f"Failed to start Gmail watch: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to start Gmail watch: {e}")
    
    async def stop_watch(self) -> None:
        """
        Stop watching for Gmail push notifications.
        
        Raises:
            ConnectionError: If stop fails
        """
        try:
            # Execute stop request
            self._service.users().stop(userId='me').execute()
            
            self._watch_expiration = None
            
            logger.info(f"Gmail watch stopped for connection {self.connection_id}")
            
        except HttpError as e:
            logger.warning(f"Failed to stop Gmail watch: {e}")
            # Don't raise - watch may have already expired
        except Exception as e:
            logger.warning(f"Failed to stop Gmail watch: {e}")
    
    async def get_history(
        self,
        start_history_id: str,
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get message history since a specific history ID.
        
        Used for processing push notifications efficiently.
        
        Args:
            start_history_id: History ID to start from
            max_results: Maximum number of history records
            page_token: Token for pagination
            
        Returns:
            History data with messages and next page token
            
        Raises:
            RateLimitError: If rate limit exceeded
            ConnectionError: If request fails
        """
        try:
            # Check rate limit
            if not await self.check_rate_limit():
                raise RateLimitError("Gmail rate limit exceeded")
            
            # Build request parameters
            params = {
                'userId': 'me',
                'startHistoryId': start_history_id,
                'maxResults': max_results,
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            # Execute request
            result = self._service.users().history().list(**params).execute()
            
            return {
                "history": result.get("history", []),
                "next_page_token": result.get("nextPageToken"),
                "history_id": result.get("historyId"),
            }
            
        except HttpError as e:
            if e.resp.status == 429:
                raise RateLimitError(f"Gmail API rate limit: {e}")
            elif e.resp.status == 404:
                # History ID too old or invalid
                logger.warning(f"Invalid history ID {start_history_id}")
                return {"history": [], "next_page_token": None, "history_id": None}
            raise ConnectionError(f"Failed to get history: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to get history: {e}")
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    @property
    def is_watch_active(self) -> bool:
        """Check if push notifications are active."""
        if not self._watch_expiration:
            return False
        return datetime.utcnow() < self._watch_expiration
    
    @property
    def watch_expires_in_seconds(self) -> Optional[int]:
        """Get seconds until watch expiration."""
        if not self._watch_expiration:
            return None
        delta = self._watch_expiration - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


# =============================================================================
# Gmail OAuth Helper Functions
# =============================================================================

def get_gmail_config() -> Dict[str, Any]:
    """
    Get Gmail OAuth configuration from environment variables.
    
    Returns:
        Dictionary with Gmail OAuth config:
        - client_id: Google app client ID
        - client_secret: Google app client secret
        - redirect_uri: OAuth callback URL
        - scopes: List of OAuth scopes
        
    Raises:
        ValueError: If required environment variables are missing
    """
    import os
    
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GMAIL_REDIRECT_URI",
        "http://localhost:8000/api/v1/connections/callback/gmail"
    )
    scopes_str = os.getenv(
        "GMAIL_SCOPES",
        "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify"
    )
    
    if not client_id or not client_secret:
        raise ValueError(
            "Gmail OAuth not configured. Set GMAIL_CLIENT_ID and "
            "GMAIL_CLIENT_SECRET environment variables."
        )
    
    # Parse scopes (comma or space separated)
    scopes = [s.strip() for s in scopes_str.replace(",", " ").split() if s.strip()]
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
    }


def is_gmail_configured() -> bool:
    """
    Check if Gmail OAuth is properly configured.
    
    Returns:
        True if Gmail credentials are set and valid
    """
    import os
    
    client_id = os.getenv("GMAIL_CLIENT_ID", "")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")
    
    # Check for placeholder values
    placeholders = ["your-", "your_", "placeholder", "xxx"]
    
    if not client_id or not client_secret:
        return False
    
    for placeholder in placeholders:
        if placeholder in client_id.lower() or placeholder in client_secret.lower():
            return False
    
    # Validate Gmail client ID format
    if not client_id.endswith(".apps.googleusercontent.com"):
        return False
    
    return True

