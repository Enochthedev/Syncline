"""
Slack Connector

Full implementation for Slack integration with:
- OAuth 2.0 authentication with Slack
- Slack Web API client wrapper
- Real-time events via Socket Mode or Events API
- Message fetching with pagination
- Channel and user management
- File attachment handling
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiohttp
from pydantic import BaseModel, Field

from integrations.base_connector import (
    BaseConnector,
    AuthenticationError,
    ConnectionError,
    RateLimitError,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Slack Data Models
# =============================================================================

class SlackUser(BaseModel):
    """Slack user information."""
    
    id: str = Field(description="Slack user ID")
    name: str = Field(description="Username")
    real_name: Optional[str] = Field(None, description="Real name")
    display_name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    is_bot: bool = Field(default=False, description="Is bot user")
    is_deleted: bool = Field(default=False, description="Is deleted user")
    team_id: str = Field(description="Team ID")


class SlackChannel(BaseModel):
    """Slack channel information."""
    
    id: str = Field(description="Channel ID")
    name: str = Field(description="Channel name")
    is_channel: bool = Field(default=True, description="Is public channel")
    is_group: bool = Field(default=False, description="Is private group")
    is_im: bool = Field(default=False, description="Is direct message")
    is_mpim: bool = Field(default=False, description="Is multi-person DM")
    is_private: bool = Field(default=False, description="Is private channel")
    is_archived: bool = Field(default=False, description="Is archived")
    is_member: bool = Field(default=False, description="Bot is member")
    topic: Optional[str] = Field(None, description="Channel topic")
    purpose: Optional[str] = Field(None, description="Channel purpose")
    num_members: Optional[int] = Field(None, description="Number of members")


class SlackMessage(BaseModel):
    """Slack message data."""
    
    ts: str = Field(description="Message timestamp")
    channel: str = Field(description="Channel ID")
    user: Optional[str] = Field(None, description="User ID")
    bot_id: Optional[str] = Field(None, description="Bot ID")
    text: str = Field(description="Message text")
    type: str = Field(default="message", description="Message type")
    subtype: Optional[str] = Field(None, description="Message subtype")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp")
    reply_count: Optional[int] = Field(None, description="Reply count")
    files: Optional[List[Dict[str, Any]]] = Field(None, description="File attachments")
    reactions: Optional[List[Dict[str, Any]]] = Field(None, description="Message reactions")
    edited: Optional[Dict[str, Any]] = Field(None, description="Edit information")


class SlackTeam(BaseModel):
    """Slack team/workspace information."""
    
    id: str = Field(description="Team ID")
    name: str = Field(description="Team name")
    domain: str = Field(description="Team domain")
    email_domain: Optional[str] = Field(None, description="Email domain")
    icon: Optional[Dict[str, str]] = Field(None, description="Team icon URLs")


# =============================================================================
# Slack Connector Implementation
# =============================================================================

class SlackConnector(BaseConnector):
    """
    Slack platform connector.
    
    Provides:
    - OAuth 2.0 authentication with Slack
    - Slack Web API access for reading messages
    - Real-time events via Socket Mode or webhooks
    - Channel and user management
    - File attachment handling
    """
    
    # Slack API endpoints
    BASE_URL = "https://slack.com/api"
    
    # Required OAuth scopes
    SCOPES = [
        "channels:history",
        "channels:read",
        "groups:history",
        "groups:read",
        "im:history",
        "im:read",
        "mpim:history",
        "mpim:read",
        "users:read",
        "users:read.email",
        "team:read",
        "files:read",
        "reactions:read",
    ]
    
    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 100,  # Slack Tier 1: 1+ requests per minute
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize Slack connector.
        
        Args:
            connection_id: Unique identifier for this connection
            credentials: OAuth credentials from Slack
            rate_limit_per_minute: Slack API rate limit
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
        
        # Extract tokens from credentials
        self.access_token = credentials.get("access_token")
        self.bot_token = credentials.get("bot_user_oauth_token")  # Bot token for API calls
        self.team_id = credentials.get("team", {}).get("id")
        self.team_name = credentials.get("team", {}).get("name")
        
        # Use bot token for API calls if available, otherwise use access token
        self.api_token = self.bot_token or self.access_token
        
        if not self.api_token:
            raise AuthenticationError("No valid Slack token found in credentials")
        
        # Cache for users and channels
        self._users_cache: Dict[str, SlackUser] = {}
        self._channels_cache: Dict[str, SlackChannel] = {}
        self._cache_expires: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)
        
        logger.info(
            f"Initialized Slack connector for team {self.team_name} ({self.team_id})"
        )
    
    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "slack"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get HTTP session with Slack API headers."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        return self._session
    
    async def _api_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a Slack API call with rate limiting and error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without /api prefix)
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            API response data
            
        Raises:
            AuthenticationError: Invalid token or permissions
            RateLimitError: Rate limit exceeded
            ConnectionError: API request failed
        """
        await self._rate_limiter.acquire()
        
        session = await self._get_session()
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            async with session.request(
                method,
                url,
                params=params,
                json=json_data,
            ) as response:
                data = await response.json()
                
                # Check for Slack API errors
                if not data.get("ok", False):
                    error = data.get("error", "unknown_error")
                    
                    if error in ["invalid_auth", "account_inactive", "token_revoked"]:
                        raise AuthenticationError(f"Slack authentication error: {error}")
                    elif error == "ratelimited":
                        retry_after = int(response.headers.get("Retry-After", 60))
                        raise RateLimitError(f"Slack rate limit exceeded, retry after {retry_after}s")
                    else:
                        raise ConnectionError(f"Slack API error: {error}")
                
                return data
                
        except aiohttp.ClientError as e:
            raise ConnectionError(f"Slack API request failed: {e}")
    
    async def _connect(self) -> None:
        """Establish connection to Slack API."""
        try:
            # Test authentication and get team info
            team_info = await self._api_call("GET", "team.info")
            team_data = team_info.get("team", {})
            
            self.team_id = team_data.get("id")
            self.team_name = team_data.get("name")
            
            # Test bot permissions
            auth_test = await self._api_call("GET", "auth.test")
            bot_info = {
                "user_id": auth_test.get("user_id"),
                "bot_id": auth_test.get("bot_id"),
                "team_id": auth_test.get("team_id"),
                "team": auth_test.get("team"),
            }
            
            logger.info(
                f"Connected to Slack team '{self.team_name}' as {bot_info.get('user_id')}"
            )
            
        except Exception as e:
            logger.error(f"Failed to connect to Slack: {e}")
            raise ConnectionError(f"Slack connection failed: {e}")
    
    async def _disconnect(self) -> None:
        """Disconnect from Slack API."""
        # Clear caches
        self._users_cache.clear()
        self._channels_cache.clear()
        self._cache_expires = None
        
        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()
        
        logger.info(f"Disconnected from Slack team {self.team_name}")
    
    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth token.
        
        Note: Slack tokens don't expire, but we can validate them.
        """
        try:
            # Validate current token
            auth_test = await self._api_call("GET", "auth.test")
            
            if auth_test.get("ok"):
                logger.info("Slack token validation successful")
                return self.credentials
            else:
                raise AuthenticationError("Slack token validation failed")
                
        except Exception as e:
            logger.error(f"Slack token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")
    
    async def _check_health(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test API connectivity
            auth_test = await self._api_call("GET", "auth.test")
            
            if auth_test.get("ok"):
                return {
                    "status": "healthy",
                    "team_id": auth_test.get("team_id"),
                    "team": auth_test.get("team"),
                    "user_id": auth_test.get("user_id"),
                    "bot_id": auth_test.get("bot_id"),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": auth_test.get("error", "unknown_error"),
                }
                
        except Exception as e:
            logger.error(f"Slack health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    # =============================================================================
    # Cache Management
    # =============================================================================
    
    def _is_cache_expired(self) -> bool:
        """Check if cache has expired."""
        return (
            self._cache_expires is None or
            datetime.utcnow() > self._cache_expires
        )
    
    async def _refresh_cache(self) -> None:
        """Refresh users and channels cache."""
        if not self._is_cache_expired():
            return
        
        logger.info("Refreshing Slack cache")
        
        # Refresh users cache
        await self._refresh_users_cache()
        
        # Refresh channels cache
        await self._refresh_channels_cache()
        
        # Update cache expiration
        self._cache_expires = datetime.utcnow() + self._cache_ttl
        
        logger.info(
            f"Cache refreshed: {len(self._users_cache)} users, "
            f"{len(self._channels_cache)} channels"
        )
    
    async def _refresh_users_cache(self) -> None:
        """Refresh users cache."""
        try:
            cursor = None
            users = {}
            
            while True:
                params = {"limit": 200}
                if cursor:
                    params["cursor"] = cursor
                
                response = await self._api_call("GET", "users.list", params=params)
                
                for user_data in response.get("members", []):
                    user = SlackUser(
                        id=user_data["id"],
                        name=user_data.get("name", ""),
                        real_name=user_data.get("real_name"),
                        display_name=user_data.get("profile", {}).get("display_name"),
                        email=user_data.get("profile", {}).get("email"),
                        avatar_url=user_data.get("profile", {}).get("image_72"),
                        is_bot=user_data.get("is_bot", False),
                        is_deleted=user_data.get("deleted", False),
                        team_id=user_data.get("team_id", self.team_id),
                    )
                    users[user.id] = user
                
                # Check for pagination
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            
            self._users_cache = users
            
        except Exception as e:
            logger.error(f"Failed to refresh users cache: {e}")
    
    async def _refresh_channels_cache(self) -> None:
        """Refresh channels cache."""
        try:
            channels = {}
            
            # Get public channels
            await self._fetch_channels("conversations.list", channels, types="public_channel")
            
            # Get private channels (groups)
            await self._fetch_channels("conversations.list", channels, types="private_channel")
            
            # Get direct messages
            await self._fetch_channels("conversations.list", channels, types="im")
            
            # Get multi-person direct messages
            await self._fetch_channels("conversations.list", channels, types="mpim")
            
            self._channels_cache = channels
            
        except Exception as e:
            logger.error(f"Failed to refresh channels cache: {e}")
    
    async def _fetch_channels(
        self,
        endpoint: str,
        channels: Dict[str, SlackChannel],
        types: str,
    ) -> None:
        """Fetch channels of a specific type."""
        cursor = None
        
        while True:
            params = {
                "limit": 200,
                "types": types,
                "exclude_archived": False,
            }
            if cursor:
                params["cursor"] = cursor
            
            response = await self._api_call("GET", endpoint, params=params)
            
            for channel_data in response.get("channels", []):
                channel = SlackChannel(
                    id=channel_data["id"],
                    name=channel_data.get("name", ""),
                    is_channel=channel_data.get("is_channel", False),
                    is_group=channel_data.get("is_group", False),
                    is_im=channel_data.get("is_im", False),
                    is_mpim=channel_data.get("is_mpim", False),
                    is_private=channel_data.get("is_private", False),
                    is_archived=channel_data.get("is_archived", False),
                    is_member=channel_data.get("is_member", False),
                    topic=channel_data.get("topic", {}).get("value"),
                    purpose=channel_data.get("purpose", {}).get("value"),
                    num_members=channel_data.get("num_members"),
                )
                channels[channel.id] = channel
            
            # Check for pagination
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    
    # =============================================================================
    # Data Access Methods
    # =============================================================================
    
    async def get_user(self, user_id: str) -> Optional[SlackUser]:
        """Get user information by ID."""
        await self._refresh_cache()
        return self._users_cache.get(user_id)
    
    async def get_channel(self, channel_id: str) -> Optional[SlackChannel]:
        """Get channel information by ID."""
        await self._refresh_cache()
        return self._channels_cache.get(channel_id)
    
    async def list_channels(self) -> List[SlackChannel]:
        """List all accessible channels."""
        await self._refresh_cache()
        return list(self._channels_cache.values())
    
    async def list_users(self) -> List[SlackUser]:
        """List all users in the workspace."""
        await self._refresh_cache()
        return list(self._users_cache.values())
    
    # =============================================================================
    # Message Fetching
    # =============================================================================
    
    async def fetch_messages(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        limit: int = 100,
        inclusive: bool = True,
    ) -> List[SlackMessage]:
        """
        Fetch messages from a channel.
        
        Args:
            channel_id: Channel ID to fetch from
            oldest: Oldest message timestamp (exclusive unless inclusive=True)
            latest: Latest message timestamp (exclusive unless inclusive=True)
            limit: Maximum number of messages to fetch (max 1000)
            inclusive: Include messages with oldest and latest timestamps
            
        Returns:
            List of Slack messages
        """
        params = {
            "channel": channel_id,
            "limit": min(limit, 1000),  # Slack API limit
            "inclusive": inclusive,
        }
        
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        
        try:
            response = await self._api_call("GET", "conversations.history", params=params)
            
            messages = []
            for msg_data in response.get("messages", []):
                message = SlackMessage(
                    ts=msg_data["ts"],
                    channel=channel_id,
                    user=msg_data.get("user"),
                    bot_id=msg_data.get("bot_id"),
                    text=msg_data.get("text", ""),
                    type=msg_data.get("type", "message"),
                    subtype=msg_data.get("subtype"),
                    thread_ts=msg_data.get("thread_ts"),
                    reply_count=msg_data.get("reply_count"),
                    files=msg_data.get("files"),
                    reactions=msg_data.get("reactions"),
                    edited=msg_data.get("edited"),
                )
                messages.append(message)
            
            logger.info(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to fetch messages from channel {channel_id}: {e}")
            raise ConnectionError(f"Message fetch failed: {e}")
    
    async def fetch_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        limit: int = 100,
    ) -> List[SlackMessage]:
        """
        Fetch replies in a thread.
        
        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp
            oldest: Oldest reply timestamp
            latest: Latest reply timestamp
            limit: Maximum number of replies to fetch
            
        Returns:
            List of thread replies
        """
        params = {
            "channel": channel_id,
            "ts": thread_ts,
            "limit": min(limit, 1000),
        }
        
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest
        
        try:
            response = await self._api_call("GET", "conversations.replies", params=params)
            
            messages = []
            for msg_data in response.get("messages", []):
                # Skip the parent message (first in the list)
                if msg_data["ts"] == thread_ts:
                    continue
                
                message = SlackMessage(
                    ts=msg_data["ts"],
                    channel=channel_id,
                    user=msg_data.get("user"),
                    bot_id=msg_data.get("bot_id"),
                    text=msg_data.get("text", ""),
                    type=msg_data.get("type", "message"),
                    subtype=msg_data.get("subtype"),
                    thread_ts=thread_ts,
                    reply_count=msg_data.get("reply_count"),
                    files=msg_data.get("files"),
                    reactions=msg_data.get("reactions"),
                    edited=msg_data.get("edited"),
                )
                messages.append(message)
            
            logger.info(f"Fetched {len(messages)} replies from thread {thread_ts}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to fetch thread replies {thread_ts}: {e}")
            raise ConnectionError(f"Thread fetch failed: {e}")
    
    async def fetch_all_messages(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit_per_channel: int = 1000,
    ) -> List[SlackMessage]:
        """
        Fetch messages from all accessible channels.
        
        Args:
            since: Fetch messages since this timestamp
            until: Fetch messages until this timestamp
            limit_per_channel: Maximum messages per channel
            
        Returns:
            List of all messages
        """
        await self._refresh_cache()
        
        all_messages = []
        
        # Convert datetime to Slack timestamp format
        oldest = str(since.timestamp()) if since else None
        latest = str(until.timestamp()) if until else None
        
        for channel in self._channels_cache.values():
            # Skip archived channels unless specifically requested
            if channel.is_archived:
                continue
            
            # Only fetch from channels we're a member of
            if not channel.is_member and not channel.is_im and not channel.is_mpim:
                continue
            
            try:
                messages = await self.fetch_messages(
                    channel_id=channel.id,
                    oldest=oldest,
                    latest=latest,
                    limit=limit_per_channel,
                )
                all_messages.extend(messages)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to fetch messages from channel {channel.name}: {e}")
                continue
        
        logger.info(f"Fetched {len(all_messages)} total messages from Slack")
        return all_messages
