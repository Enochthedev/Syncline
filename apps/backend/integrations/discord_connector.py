"""
Discord Connector

Full implementation for Discord integration with:
- Bot token authentication
- Discord API client wrapper
- Gateway connection for real-time events
- Message fetching with pagination
- Guild and channel management
- User and member information
- File attachment handling
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiohttp
from pydantic import BaseModel, Field

from integrations.base_connector import (
    AuthenticationError,
    BaseConnector,
    ConnectionError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Discord Data Models
# =============================================================================


class DiscordChannelType(int, Enum):
    """Discord channel types."""

    GUILD_TEXT = 0
    DM = 1
    GUILD_VOICE = 2
    GROUP_DM = 3
    GUILD_CATEGORY = 4
    GUILD_ANNOUNCEMENT = 5
    ANNOUNCEMENT_THREAD = 10
    PUBLIC_THREAD = 11
    PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13
    GUILD_DIRECTORY = 14
    GUILD_FORUM = 15


class DiscordUser(BaseModel):
    """Discord user information."""

    id: str = Field(description="User ID")
    username: str = Field(description="Username")
    discriminator: str = Field(description="User discriminator")
    global_name: Optional[str] = Field(None, description="Global display name")
    avatar: Optional[str] = Field(None, description="Avatar hash")
    bot: bool = Field(default=False, description="Is bot user")
    system: bool = Field(default=False, description="Is system user")
    verified: Optional[bool] = Field(None, description="Is verified")
    email: Optional[str] = Field(None, description="Email address")
    flags: Optional[int] = Field(None, description="User flags")
    premium_type: Optional[int] = Field(None, description="Nitro subscription type")
    public_flags: Optional[int] = Field(None, description="Public user flags")

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.global_name or self.username

    @property
    def avatar_url(self) -> Optional[str]:
        """Get avatar URL."""
        if self.avatar:
            return f"https://cdn.discordapp.com/avatars/{self.id}/{self.avatar}.png"
        return None


class DiscordGuild(BaseModel):
    """Discord guild (server) information."""

    id: str = Field(description="Guild ID")
    name: str = Field(description="Guild name")
    icon: Optional[str] = Field(None, description="Icon hash")
    description: Optional[str] = Field(None, description="Guild description")
    owner_id: str = Field(description="Owner user ID")
    permissions: Optional[str] = Field(None, description="Bot permissions")
    features: List[str] = Field(default_factory=list, description="Guild features")
    approximate_member_count: Optional[int] = Field(
        None, description="Approximate member count"
    )
    approximate_presence_count: Optional[int] = Field(
        None, description="Approximate presence count"
    )

    @property
    def icon_url(self) -> Optional[str]:
        """Get guild icon URL."""
        if self.icon:
            return f"https://cdn.discordapp.com/icons/{self.id}/{self.icon}.png"
        return None


class DiscordChannel(BaseModel):
    """Discord channel information."""

    id: str = Field(description="Channel ID")
    type: DiscordChannelType = Field(description="Channel type")
    guild_id: Optional[str] = Field(None, description="Guild ID")
    position: Optional[int] = Field(None, description="Channel position")
    name: Optional[str] = Field(None, description="Channel name")
    topic: Optional[str] = Field(None, description="Channel topic")
    nsfw: bool = Field(default=False, description="Is NSFW channel")
    last_message_id: Optional[str] = Field(None, description="Last message ID")
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    rate_limit_per_user: Optional[int] = Field(None, description="Rate limit per user")
    recipients: Optional[List[DiscordUser]] = Field(None, description="DM recipients")

    @property
    def is_text_channel(self) -> bool:
        """Check if channel supports text messages."""
        return self.type in [
            DiscordChannelType.GUILD_TEXT,
            DiscordChannelType.DM,
            DiscordChannelType.GROUP_DM,
            DiscordChannelType.GUILD_ANNOUNCEMENT,
            DiscordChannelType.ANNOUNCEMENT_THREAD,
            DiscordChannelType.PUBLIC_THREAD,
            DiscordChannelType.PRIVATE_THREAD,
        ]


class DiscordMessage(BaseModel):
    """Discord message data."""

    id: str = Field(description="Message ID")
    channel_id: str = Field(description="Channel ID")
    guild_id: Optional[str] = Field(None, description="Guild ID")
    author: DiscordUser = Field(description="Message author")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(description="Message timestamp")
    edited_timestamp: Optional[datetime] = Field(None, description="Edit timestamp")
    tts: bool = Field(default=False, description="Is TTS message")
    mention_everyone: bool = Field(default=False, description="Mentions everyone")
    mentions: List[DiscordUser] = Field(
        default_factory=list, description="User mentions"
    )
    mention_roles: List[str] = Field(default_factory=list, description="Role mentions")
    mention_channels: List[Dict[str, Any]] = Field(
        default_factory=list, description="Channel mentions"
    )
    attachments: List[Dict[str, Any]] = Field(
        default_factory=list, description="File attachments"
    )
    embeds: List[Dict[str, Any]] = Field(
        default_factory=list, description="Message embeds"
    )
    reactions: Optional[List[Dict[str, Any]]] = Field(
        None, description="Message reactions"
    )
    pinned: bool = Field(default=False, description="Is pinned message")
    webhook_id: Optional[str] = Field(None, description="Webhook ID")
    type: int = Field(default=0, description="Message type")
    flags: Optional[int] = Field(None, description="Message flags")
    referenced_message: Optional[Dict[str, Any]] = Field(
        None, description="Referenced message"
    )
    thread: Optional[Dict[str, Any]] = Field(None, description="Thread information")


# =============================================================================
# Discord Connector Implementation
# =============================================================================


class DiscordConnector(BaseConnector):
    """
    Discord platform connector.

    Provides:
    - Bot token authentication
    - Discord API access for reading messages
    - Gateway connection for real-time events
    - Guild and channel management
    - File attachment handling
    """

    # Discord API endpoints
    BASE_URL = "https://discord.com/api/v10"
    GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"

    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 50,  # Conservative Discord rate limit
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):
        """
        Initialize Discord connector.

        Args:
            connection_id: Unique identifier for this connection
            credentials: Bot token and configuration
            rate_limit_per_minute: Discord API rate limit
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

        # Extract bot token from credentials
        self.bot_token = credentials.get("bot_token")
        if not self.bot_token:
            raise AuthenticationError("Discord bot token is required")

        # Bot information
        self.bot_user: Optional[DiscordUser] = None
        self.application_id: Optional[str] = None

        # Cache for guilds, channels, and users
        self._guilds_cache: Dict[str, DiscordGuild] = {}
        self._channels_cache: Dict[str, DiscordChannel] = {}
        self._users_cache: Dict[str, DiscordUser] = {}
        self._cache_expires: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)

        # Gateway connection (for real-time events)
        self._gateway_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._sequence: Optional[int] = None
        self._session_id: Optional[str] = None

        logger.info(f"Initialized Discord connector {self.connection_id}")

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "discord"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get HTTP session with Discord API headers."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json",
                "User-Agent": "R.E.M.I Bot (https://github.com/your-org/remi, 1.0.0)",
            }
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self._session

    async def _api_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make a Discord API call with rate limiting and error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
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
                # Handle rate limiting
                if response.status == 429:
                    retry_after = float(response.headers.get("Retry-After", 1))
                    raise RateLimitError(
                        f"Discord rate limit exceeded, retry after {retry_after}s"
                    )

                # Handle authentication errors
                if response.status == 401:
                    raise AuthenticationError(
                        "Discord authentication failed - invalid token"
                    )

                # Handle permission errors
                if response.status == 403:
                    raise AuthenticationError("Discord permission denied")

                # Handle other client errors
                if response.status >= 400:
                    error_text = await response.text()
                    raise ConnectionError(
                        f"Discord API error {response.status}: {error_text}"
                    )

                # Parse JSON response
                if response.content_type == "application/json":
                    return await response.json()
                else:
                    return {"data": await response.text()}

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Discord API request failed: {e}")

    async def _connect(self) -> None:
        """Establish connection to Discord API."""
        try:
            # Get bot user information
            user_data = await self._api_call("GET", "/users/@me")
            self.bot_user = DiscordUser(**user_data)

            # Get application information
            app_data = await self._api_call("GET", "/oauth2/applications/@me")
            self.application_id = app_data.get("id")

            logger.info(
                f"Connected to Discord as {self.bot_user.username}#{self.bot_user.discriminator}"
            )

            # Refresh cache
            await self._refresh_cache()

        except Exception as e:
            logger.error(f"Failed to connect to Discord: {e}")
            raise ConnectionError(f"Discord connection failed: {e}")

    async def _disconnect(self) -> None:
        """Disconnect from Discord API."""
        # Close gateway connection
        if self._gateway_ws and not self._gateway_ws.closed:
            await self._gateway_ws.close()

        # Cancel heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        # Clear caches
        self._guilds_cache.clear()
        self._channels_cache.clear()
        self._users_cache.clear()
        self._cache_expires = None

        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()

        logger.info("Disconnected from Discord")

    async def _refresh_token(self) -> Dict[str, Any]:
        """
        Refresh token.

        Discord bot tokens don't expire, but we can validate them.
        """
        try:
            # Validate current token
            user_data = await self._api_call("GET", "/users/@me")

            if user_data.get("id"):
                logger.info("Discord token validation successful")
                return self.credentials
            else:
                raise AuthenticationError("Discord token validation failed")

        except Exception as e:
            logger.error(f"Discord token refresh failed: {e}")
            raise AuthenticationError(f"Token refresh failed: {e}")

    async def _check_health(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test API connectivity
            user_data = await self._api_call("GET", "/users/@me")

            if user_data.get("id"):
                return {
                    "status": "healthy",
                    "bot_id": user_data.get("id"),
                    "bot_username": user_data.get("username"),
                    "guilds_count": len(self._guilds_cache),
                    "channels_count": len(self._channels_cache),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Invalid API response",
                }

        except Exception as e:
            logger.error(f"Discord health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    # =============================================================================
    # Cache Management
    # =============================================================================

    def _is_cache_expired(self) -> bool:
        """Check if cache has expired."""
        return self._cache_expires is None or datetime.utcnow() > self._cache_expires

    async def _refresh_cache(self) -> None:
        """Refresh guilds and channels cache."""
        if not self._is_cache_expired():
            return

        logger.info("Refreshing Discord cache")

        # Refresh guilds cache
        await self._refresh_guilds_cache()

        # Refresh channels cache
        await self._refresh_channels_cache()

        # Update cache expiration
        self._cache_expires = datetime.utcnow() + self._cache_ttl

        logger.info(
            f"Cache refreshed: {len(self._guilds_cache)} guilds, "
            f"{len(self._channels_cache)} channels"
        )

    async def _refresh_guilds_cache(self) -> None:
        """Refresh guilds cache."""
        try:
            guilds_data = await self._api_call("GET", "/users/@me/guilds")

            guilds = {}
            for guild_data in guilds_data:
                guild = DiscordGuild(
                    id=guild_data["id"],
                    name=guild_data["name"],
                    icon=guild_data.get("icon"),
                    description=guild_data.get("description"),
                    owner_id=guild_data.get("owner_id", ""),
                    permissions=guild_data.get("permissions"),
                    features=guild_data.get("features", []),
                    approximate_member_count=guild_data.get("approximate_member_count"),
                    approximate_presence_count=guild_data.get(
                        "approximate_presence_count"
                    ),
                )
                guilds[guild.id] = guild

            self._guilds_cache = guilds

        except Exception as e:
            logger.error(f"Failed to refresh guilds cache: {e}")

    async def _refresh_channels_cache(self) -> None:
        """Refresh channels cache."""
        try:
            channels = {}

            # Get channels for each guild
            for guild_id in self._guilds_cache.keys():
                try:
                    channels_data = await self._api_call(
                        "GET", f"/guilds/{guild_id}/channels"
                    )

                    for channel_data in channels_data:
                        channel = DiscordChannel(
                            id=channel_data["id"],
                            type=DiscordChannelType(channel_data["type"]),
                            guild_id=guild_id,
                            position=channel_data.get("position"),
                            name=channel_data.get("name"),
                            topic=channel_data.get("topic"),
                            nsfw=channel_data.get("nsfw", False),
                            last_message_id=channel_data.get("last_message_id"),
                            parent_id=channel_data.get("parent_id"),
                            rate_limit_per_user=channel_data.get("rate_limit_per_user"),
                        )
                        channels[channel.id] = channel

                    # Add small delay to avoid rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch channels for guild {guild_id}: {e}"
                    )
                    continue

            # Get DM channels
            try:
                dm_channels_data = await self._api_call("GET", "/users/@me/channels")

                for channel_data in dm_channels_data:
                    recipients = []
                    for recipient_data in channel_data.get("recipients", []):
                        recipient = DiscordUser(**recipient_data)
                        recipients.append(recipient)
                        self._users_cache[recipient.id] = recipient

                    channel = DiscordChannel(
                        id=channel_data["id"],
                        type=DiscordChannelType(channel_data["type"]),
                        name=channel_data.get("name"),
                        last_message_id=channel_data.get("last_message_id"),
                        recipients=recipients,
                    )
                    channels[channel.id] = channel

            except Exception as e:
                logger.warning(f"Failed to fetch DM channels: {e}")

            self._channels_cache = channels

        except Exception as e:
            logger.error(f"Failed to refresh channels cache: {e}")

    # =============================================================================
    # Data Access Methods
    # =============================================================================

    async def get_guild(self, guild_id: str) -> Optional[DiscordGuild]:
        """Get guild information by ID."""
        await self._refresh_cache()
        return self._guilds_cache.get(guild_id)

    async def get_channel(self, channel_id: str) -> Optional[DiscordChannel]:
        """Get channel information by ID."""
        await self._refresh_cache()
        return self._channels_cache.get(channel_id)

    async def get_user(self, user_id: str) -> Optional[DiscordUser]:
        """Get user information by ID."""
        # Check cache first
        if user_id in self._users_cache:
            return self._users_cache[user_id]

        # Fetch from API
        try:
            user_data = await self._api_call("GET", f"/users/{user_id}")
            user = DiscordUser(**user_data)
            self._users_cache[user_id] = user
            return user
        except Exception as e:
            logger.warning(f"Failed to fetch user {user_id}: {e}")
            return None

    async def list_guilds(self) -> List[DiscordGuild]:
        """List all accessible guilds."""
        await self._refresh_cache()
        return list(self._guilds_cache.values())

    async def list_channels(
        self, guild_id: Optional[str] = None
    ) -> List[DiscordChannel]:
        """List channels, optionally filtered by guild."""
        await self._refresh_cache()

        if guild_id:
            return [
                channel
                for channel in self._channels_cache.values()
                if channel.guild_id == guild_id
            ]
        else:
            return list(self._channels_cache.values())

    # =============================================================================
    # Message Fetching
    # =============================================================================

    async def fetch_messages(
        self,
        channel_id: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
        around: Optional[str] = None,
        limit: int = 50,
    ) -> List[DiscordMessage]:
        """
        Fetch messages from a channel.

        Args:
            channel_id: Channel ID to fetch from
            before: Get messages before this message ID
            after: Get messages after this message ID
            around: Get messages around this message ID
            limit: Maximum number of messages to fetch (max 100)

        Returns:
            List of Discord messages
        """
        params = {
            "limit": min(limit, 100),  # Discord API limit
        }

        if before:
            params["before"] = before
        elif after:
            params["after"] = after
        elif around:
            params["around"] = around

        try:
            messages_data = await self._api_call(
                "GET", f"/channels/{channel_id}/messages", params=params
            )

            messages = []
            for msg_data in messages_data:
                # Parse author
                author = DiscordUser(**msg_data["author"])
                self._users_cache[author.id] = author

                # Parse mentions
                mentions = []
                for mention_data in msg_data.get("mentions", []):
                    mention = DiscordUser(**mention_data)
                    mentions.append(mention)
                    self._users_cache[mention.id] = mention

                message = DiscordMessage(
                    id=msg_data["id"],
                    channel_id=channel_id,
                    guild_id=msg_data.get("guild_id"),
                    author=author,
                    content=msg_data.get("content", ""),
                    timestamp=datetime.fromisoformat(
                        msg_data["timestamp"].replace("Z", "+00:00")
                    ),
                    edited_timestamp=(
                        datetime.fromisoformat(
                            msg_data["edited_timestamp"].replace("Z", "+00:00")
                        )
                        if msg_data.get("edited_timestamp")
                        else None
                    ),
                    tts=msg_data.get("tts", False),
                    mention_everyone=msg_data.get("mention_everyone", False),
                    mentions=mentions,
                    mention_roles=msg_data.get("mention_roles", []),
                    mention_channels=msg_data.get("mention_channels", []),
                    attachments=msg_data.get("attachments", []),
                    embeds=msg_data.get("embeds", []),
                    reactions=msg_data.get("reactions"),
                    pinned=msg_data.get("pinned", False),
                    webhook_id=msg_data.get("webhook_id"),
                    type=msg_data.get("type", 0),
                    flags=msg_data.get("flags"),
                    referenced_message=msg_data.get("referenced_message"),
                    thread=msg_data.get("thread"),
                )
                messages.append(message)

            logger.info(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to fetch messages from channel {channel_id}: {e}")
            raise ConnectionError(f"Message fetch failed: {e}")

    async def fetch_all_messages(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit_per_channel: int = 100,
    ) -> List[DiscordMessage]:
        """
        Fetch messages from all accessible text channels.

        Args:
            since: Fetch messages since this timestamp
            until: Fetch messages until this timestamp
            limit_per_channel: Maximum messages per channel

        Returns:
            List of all messages
        """
        await self._refresh_cache()

        all_messages = []

        for channel in self._channels_cache.values():
            # Only fetch from text channels
            if not channel.is_text_channel:
                continue

            try:
                # Convert datetime to Discord snowflake if needed
                before_id = None
                after_id = None

                if until:
                    # Convert timestamp to Discord snowflake (approximate)
                    before_id = str(
                        int((until.timestamp() * 1000 - 1420070400000) << 22)
                    )

                if since:
                    # Convert timestamp to Discord snowflake (approximate)
                    after_id = str(
                        int((since.timestamp() * 1000 - 1420070400000) << 22)
                    )

                messages = await self.fetch_messages(
                    channel_id=channel.id,
                    before=before_id,
                    after=after_id,
                    limit=limit_per_channel,
                )
                all_messages.extend(messages)

                # Add delay to avoid rate limiting
                await asyncio.sleep(0.2)

            except Exception as e:
                logger.warning(
                    f"Failed to fetch messages from channel {channel.name or channel.id}: {e}"
                )
                continue

        logger.info(f"Fetched {len(all_messages)} total messages from Discord")
        return all_messages
