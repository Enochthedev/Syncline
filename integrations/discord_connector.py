"""
Discord connector with Discord Gateway WebSocket integration.

This module provides Discord integration with bot authentication, guild permission
handling, real-time message event processing, and historical message fetching
capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import aiohttp

from .base_connector import BaseConnector, RawMessage, AuthenticationError
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform, RawMessage as SchemaRawMessage

logger = logging.getLogger(__name__)


class DiscordConnectorError(Exception):
    """Discord connector specific errors."""
    pass


class DiscordWebhookError(Exception):
    """Discord webhook processing errors."""
    pass


class DiscordGatewayError(Exception):
    """Discord Gateway specific errors."""
    pass


class DiscordConnector(BaseConnector):
    """
    Discord connector with Discord Gateway WebSocket integration.

    Provides Discord API integration with bot authentication, guild permission
    handling, real-time message event processing with proper rate limiting,
    and historical message fetching with channel message history.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("discord", config, **kwargs)

        self.event_bus = event_bus

        # Discord-specific configuration
        self.bot_token = config.get('bot_token')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.webhook_secret = config.get('webhook_secret')

        # API configuration
        self.api_base_url = "https://discord.com/api/v10"
        self.gateway_url: Optional[str] = None
        self.gateway_version = 10
        self.gateway_encoding = "json"

        # Bot configuration
        # Default: GUILDS + GUILD_MESSAGES
        self.intents = config.get('intents', 513)
        self.presence = config.get('presence', {
            'status': 'online',
            'afk': False,
            'activities': [],
            'since': None
        })

        # Pagination and fetching configuration
        self.max_results = config.get('max_results', 100)
        self.include_dm_channels = config.get('include_dm_channels', True)
        self.monitored_guilds = config.get(
            'monitored_guilds', [])  # Empty = all guilds

        # Gateway connection state
        self._gateway_connection: Optional[aiohttp.ClientWebSocketResponse] = None
        self._gateway_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._sequence_number: Optional[int] = None
        self._session_id: Optional[str] = None
        self._heartbeat_interval: Optional[float] = None
        self._last_heartbeat_ack = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

        # Processing queue
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

        # Caches for Discord entities
        self._guilds_cache: Dict[str, Dict[str, Any]] = {}
        self._channels_cache: Dict[str, Dict[str, Any]] = {}
        self._users_cache: Dict[str, Dict[str, Any]] = {}

        # Rate limiting
        self._rate_limit_remaining = 50
        self._rate_limit_reset_after = 0
        self._rate_limit_bucket = "global"

    async def authenticate(self) -> None:
        """Authenticate with Discord using bot token."""
        try:
            logger.info("Starting Discord bot authentication")

            if not self.bot_token:
                raise AuthenticationError("Discord bot token is required")

            # Validate bot token by getting bot user info
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }

            # Initialize session if not already done
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": f"MESH-Connector/{self.platform}"}
                )

            async with self._session.get(f"{self.api_base_url}/users/@me", headers=headers) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Discord bot token")
                elif response.status != 200:
                    raise AuthenticationError(
                        f"Discord API error: {response.status}")

                bot_user = await response.json()
                logger.info(
                    f"Discord authentication successful for bot: {bot_user.get('username')}#{bot_user.get('discriminator')}")

            # Get gateway URL
            async with self._session.get(f"{self.api_base_url}/gateway/bot", headers=headers) as gateway_response:
                if gateway_response.status != 200:
                    raise AuthenticationError(
                        f"Failed to get Discord gateway URL: {gateway_response.status}")

                gateway_data = await gateway_response.json()
                self.gateway_url = gateway_data.get('url')

                if not self.gateway_url:
                    raise AuthenticationError(
                        "No Discord gateway URL received")

                logger.info(
                    f"Discord gateway URL obtained: {self.gateway_url}")

        except Exception as e:
            logger.error(f"Discord authentication failed: {e}")
            raise AuthenticationError(f"Discord authentication failed: {e}")

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion using Discord Gateway."""
        try:
            logger.info("Starting Discord real-time ingestion")

            # Start message processor
            self._processor_task = asyncio.create_task(
                self._process_message_queue()
            )

            # Start Gateway connection
            await self._start_gateway_connection()

            logger.info("Discord real-time ingestion started successfully")

        except Exception as e:
            logger.error(f"Failed to start Discord real-time ingestion: {e}")
            raise DiscordConnectorError(
                f"Failed to start real-time ingestion: {e}")

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            logger.info("Stopping Discord real-time ingestion")

            # Stop Gateway connection
            await self._stop_gateway_connection()

            # Stop processor task
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
                self._processor_task = None

            logger.info("Discord real-time ingestion stopped")

        except Exception as e:
            logger.error(f"Error stopping Discord real-time ingestion: {e}")

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """
        Fetch historical messages with cursor-based pagination.

        Args:
            cursor: Message ID to start from (None for most recent)
            limit: Maximum number of messages to fetch

        Returns:
            List of raw messages
        """
        try:
            logger.debug(
                f"Fetching historical Discord messages (cursor: {cursor}, limit: {limit})")

            if not self.bot_token:
                raise DiscordConnectorError("Bot token not available")

            raw_messages = []

            # Get all accessible channels
            channels = await self._get_all_channels()

            for channel in channels:
                channel_id = channel['id']
                channel_messages = await self._fetch_channel_history(
                    channel_id, cursor, limit
                )
                raw_messages.extend(channel_messages)

                # Respect rate limits
                await self._handle_rate_limit()

            logger.info(f"Fetched {len(raw_messages)} Discord messages")
            return raw_messages

        except Exception as e:
            logger.error(f"Error fetching Discord messages: {e}")
            raise DiscordConnectorError(f"Error fetching messages: {e}")

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Handle incoming Discord webhook payload.

        Args:
            payload: Webhook payload from Discord
        """
        try:
            logger.debug("Processing Discord webhook payload")

            # Validate webhook signature if secret is configured
            if self.webhook_secret:
                await self._validate_webhook_signature(payload)

            # Process webhook event
            event_type = payload.get('type')

            if event_type == 'MESSAGE_CREATE':
                # Remove the type field and pass the rest as message data
                message_data = {k: v for k,
                                v in payload.items() if k != 'type'}
                await self._handle_message_event(message_data)
            elif event_type == 'MESSAGE_UPDATE':
                message_data = {k: v for k,
                                v in payload.items() if k != 'type'}
                await self._handle_message_update_event(message_data)
            elif event_type == 'MESSAGE_DELETE':
                message_data = {k: v for k,
                                v in payload.items() if k != 'type'}
                await self._handle_message_delete_event(message_data)

        except Exception as e:
            logger.error(f"Error handling Discord webhook: {e}")
            raise DiscordWebhookError(f"Webhook processing failed: {e}")

    async def _start_gateway_connection(self) -> None:
        """Start Discord Gateway WebSocket connection."""
        try:
            logger.info("Starting Discord Gateway connection")

            if not self.gateway_url:
                raise DiscordGatewayError("Gateway URL not available")

            # Start Gateway task
            self._gateway_task = asyncio.create_task(
                self._gateway_handler()
            )

            logger.info("Discord Gateway connection started")

        except Exception as e:
            logger.error(f"Failed to start Discord Gateway: {e}")
            raise DiscordGatewayError(f"Failed to start Gateway: {e}")

    async def _stop_gateway_connection(self) -> None:
        """Stop Discord Gateway WebSocket connection."""
        try:
            logger.info("Stopping Discord Gateway connection")

            # Stop heartbeat task
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None

            # Stop Gateway task
            if self._gateway_task:
                self._gateway_task.cancel()
                try:
                    await self._gateway_task
                except asyncio.CancelledError:
                    pass
                self._gateway_task = None

            # Close Gateway connection
            if self._gateway_connection:
                await self._gateway_connection.close()
                self._gateway_connection = None

            logger.info("Discord Gateway connection stopped")

        except Exception as e:
            logger.error(f"Error stopping Discord Gateway: {e}")

    async def _gateway_handler(self) -> None:
        """Handle Discord Gateway WebSocket connection."""
        while self._running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                logger.info(
                    f"Connecting to Discord Gateway: {self.gateway_url}")

                gateway_url = f"{self.gateway_url}/?v={self.gateway_version}&encoding={self.gateway_encoding}"

                if not self._session:
                    self._session = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=30),
                        headers={
                            "User-Agent": f"MESH-Connector/{self.platform}"}
                    )

                async with self._session.ws_connect(gateway_url) as ws:
                    self._gateway_connection = ws
                    self._reconnect_attempts = 0

                    logger.info("Discord Gateway connection established")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                await self._handle_gateway_message(data)
                            except json.JSONDecodeError as e:
                                logger.error(
                                    f"Failed to parse Gateway message: {e}")
                            except Exception as e:
                                logger.error(
                                    f"Error handling Gateway message: {e}")
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(
                                f"Gateway WebSocket error: {ws.exception()}")
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSE:
                            logger.warning(
                                "Gateway WebSocket connection closed")
                            break

            except aiohttp.ClientError as e:
                logger.warning(f"Gateway connection error: {e}")
                self._reconnect_attempts += 1
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait_time = min(2 ** self._reconnect_attempts, 60)
                    logger.info(
                        f"Reconnecting to Gateway in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max Gateway reconnection attempts reached")
                    break
            except Exception as e:
                logger.error(f"Gateway connection error: {e}")
                self._reconnect_attempts += 1
                await asyncio.sleep(5)

        self._gateway_connection = None

    async def _handle_gateway_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming Gateway message."""
        try:
            opcode = data.get('op')
            sequence = data.get('s')
            event_type = data.get('t')
            event_data = data.get('d')

            # Update sequence number
            if sequence is not None:
                self._sequence_number = sequence

            if opcode == 0:  # Dispatch
                await self._handle_gateway_event(event_type, event_data)
            elif opcode == 1:  # Heartbeat
                await self._send_heartbeat()
            elif opcode == 7:  # Reconnect
                logger.info("Gateway requested reconnect")
                await self._reconnect_gateway()
            elif opcode == 9:  # Invalid Session
                logger.warning("Invalid session, reconnecting...")
                self._session_id = None
                await asyncio.sleep(5)
                await self._identify()
            elif opcode == 10:  # Hello
                await self._handle_hello(event_data)
            elif opcode == 11:  # Heartbeat ACK
                self._last_heartbeat_ack = True

        except Exception as e:
            logger.error(f"Error handling Gateway message: {e}")

    async def _handle_hello(self, data: Dict[str, Any]) -> None:
        """Handle Gateway Hello message."""
        try:
            self._heartbeat_interval = data.get(
                'heartbeat_interval', 41250) / 1000.0
            logger.info(
                f"Gateway heartbeat interval: {self._heartbeat_interval}s")

            # Start heartbeat task
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Send identify or resume
            if self._session_id:
                await self._resume()
            else:
                await self._identify()

        except Exception as e:
            logger.error(f"Error handling Hello message: {e}")

    async def _identify(self) -> None:
        """Send identify payload to Gateway."""
        try:
            identify_payload = {
                'op': 2,
                'd': {
                    'token': self.bot_token,
                    'intents': self.intents,
                    'properties': {
                        'os': 'linux',
                        'browser': 'mesh-connector',
                        'device': 'mesh-connector'
                    },
                    'presence': self.presence
                }
            }

            await self._send_gateway_message(identify_payload)
            logger.info("Sent identify payload to Gateway")

        except Exception as e:
            logger.error(f"Error sending identify: {e}")

    async def _resume(self) -> None:
        """Send resume payload to Gateway."""
        try:
            resume_payload = {
                'op': 6,
                'd': {
                    'token': self.bot_token,
                    'session_id': self._session_id,
                    'seq': self._sequence_number
                }
            }

            await self._send_gateway_message(resume_payload)
            logger.info("Sent resume payload to Gateway")

        except Exception as e:
            logger.error(f"Error sending resume: {e}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to Gateway."""
        try:
            while self._running:
                await asyncio.sleep(self._heartbeat_interval)

                if not self._last_heartbeat_ack:
                    logger.warning(
                        "Heartbeat ACK not received, reconnecting...")
                    await self._reconnect_gateway()
                    break

                await self._send_heartbeat()

        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")

    async def _send_heartbeat(self) -> None:
        """Send heartbeat to Gateway."""
        try:
            heartbeat_payload = {
                'op': 1,
                'd': self._sequence_number
            }

            await self._send_gateway_message(heartbeat_payload)
            self._last_heartbeat_ack = False

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    async def _send_gateway_message(self, payload: Dict[str, Any]) -> None:
        """Send message to Gateway."""
        if self._gateway_connection:
            await self._gateway_connection.send_str(json.dumps(payload))

    async def _reconnect_gateway(self) -> None:
        """Reconnect to Gateway."""
        if self._gateway_connection:
            await self._gateway_connection.close()
        self._gateway_connection = None

    async def _handle_gateway_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle Gateway event."""
        try:
            if event_type == 'READY':
                await self._handle_ready_event(event_data)
            elif event_type == 'RESUMED':
                logger.info("Gateway session resumed")
            elif event_type == 'MESSAGE_CREATE':
                await self._handle_message_event(event_data)
            elif event_type == 'MESSAGE_UPDATE':
                await self._handle_message_update_event(event_data)
            elif event_type == 'MESSAGE_DELETE':
                await self._handle_message_delete_event(event_data)
            elif event_type == 'GUILD_CREATE':
                await self._handle_guild_create_event(event_data)
            elif event_type == 'CHANNEL_CREATE':
                await self._handle_channel_create_event(event_data)

        except Exception as e:
            logger.error(f"Error handling Gateway event {event_type}: {e}")

    async def _handle_ready_event(self, data: Dict[str, Any]) -> None:
        """Handle READY event from Gateway."""
        try:
            self._session_id = data.get('session_id')
            bot_user = data.get('user', {})
            guilds = data.get('guilds', [])

            logger.info(
                f"Discord bot ready: {bot_user.get('username')}#{bot_user.get('discriminator')}")
            logger.info(f"Connected to {len(guilds)} guilds")

            # Cache guild information
            for guild in guilds:
                self._guilds_cache[guild['id']] = guild

        except Exception as e:
            logger.error(f"Error handling READY event: {e}")

    async def _handle_guild_create_event(self, data: Dict[str, Any]) -> None:
        """Handle GUILD_CREATE event."""
        try:
            guild_id = data.get('id')
            if guild_id:
                self._guilds_cache[guild_id] = data

                # Cache channels
                channels = data.get('channels', [])
                for channel in channels:
                    self._channels_cache[channel['id']] = channel

                # Cache members
                members = data.get('members', [])
                for member in members:
                    user = member.get('user', {})
                    if user.get('id'):
                        self._users_cache[user['id']] = user

                logger.debug(f"Cached guild: {data.get('name')} ({guild_id})")

        except Exception as e:
            logger.error(f"Error handling GUILD_CREATE event: {e}")

    async def _handle_channel_create_event(self, data: Dict[str, Any]) -> None:
        """Handle CHANNEL_CREATE event."""
        try:
            channel_id = data.get('id')
            if channel_id:
                self._channels_cache[channel_id] = data
                logger.debug(
                    f"Cached channel: {data.get('name')} ({channel_id})")

        except Exception as e:
            logger.error(f"Error handling CHANNEL_CREATE event: {e}")

    async def _handle_message_event(self, data: Dict[str, Any]) -> None:
        """Handle MESSAGE_CREATE event."""
        try:
            # Skip bot messages
            if data.get('author', {}).get('bot'):
                return

            # Skip system messages
            if data.get('type', 0) != 0:
                return

            # Check if we should monitor this guild
            guild_id = data.get('guild_id')
            if self.monitored_guilds and guild_id not in self.monitored_guilds:
                return

            # Queue message for processing
            await self._processing_queue.put({
                'type': 'message_create',
                'data': data,
                'timestamp': datetime.now(timezone.utc)
            })

        except Exception as e:
            logger.error(f"Error handling message event: {e}")

    async def _handle_message_update_event(self, data: Dict[str, Any]) -> None:
        """Handle MESSAGE_UPDATE event."""
        try:
            # Queue update for processing
            await self._processing_queue.put({
                'type': 'message_update',
                'data': data,
                'timestamp': datetime.now(timezone.utc)
            })

        except Exception as e:
            logger.error(f"Error handling message update event: {e}")

    async def _handle_message_delete_event(self, data: Dict[str, Any]) -> None:
        """Handle MESSAGE_DELETE event."""
        try:
            logger.debug(f"Message deleted: {data.get('id')}")

        except Exception as e:
            logger.error(f"Error handling message delete event: {e}")

    async def _process_message_queue(self) -> None:
        """Process queued messages from Gateway events."""
        logger.info("Starting Discord message queue processor")

        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )

                if item['type'] == 'message_create':
                    await self._process_message_create(item['data'])
                elif item['type'] == 'message_update':
                    await self._process_message_update(item['data'])

                # Mark task as done
                self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Discord message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")

    async def _process_message_create(self, data: Dict[str, Any]) -> None:
        """Process a MESSAGE_CREATE event."""
        try:
            logger.debug(f"Processing Discord message: {data.get('id')}")

            # Create raw message
            raw_message = RawMessage(
                id=f"discord_{data.get('id', '')}",
                platform=self.platform,
                platform_message_id=data.get('id', ''),
                thread_id=data.get('channel_id', ''),
                sender_id=data.get('author', {}).get('id', ''),
                content=self._extract_message_content(data),
                timestamp=self._extract_timestamp(data),
                raw_data=data
            )

            # Publish to event bus if available
            if self.event_bus:
                event = Event(
                    type=EventType.MESSAGE_RECEIVED,
                    data={
                        'platform': self.platform,
                        'message': raw_message.__dict__
                    },
                    source=f"{self.platform}_connector"
                )

                await self.event_bus.publish('messages.raw', event)
                logger.debug(
                    f"Published new Discord message to event bus: {raw_message.id}")

        except Exception as e:
            logger.error(f"Error processing message create: {e}")

    async def _process_message_update(self, data: Dict[str, Any]) -> None:
        """Process a MESSAGE_UPDATE event."""
        try:
            logger.debug(
                f"Processing Discord message update: {data.get('id')}")
            # Handle message updates if needed

        except Exception as e:
            logger.error(f"Error processing message update: {e}")

    async def _get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all accessible channels for historical message fetching."""
        channels = []

        # Get channels from cached guilds
        for guild_id, guild_data in self._guilds_cache.items():
            # Skip if we're monitoring specific guilds and this isn't one
            if self.monitored_guilds and guild_id not in self.monitored_guilds:
                continue

            # Get guild channels via API
            guild_channels = await self._fetch_guild_channels(guild_id)
            channels.extend(guild_channels)

        # Get DM channels if enabled
        if self.include_dm_channels:
            dm_channels = await self._fetch_dm_channels()
            channels.extend(dm_channels)

        return channels

    async def _fetch_guild_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        """Fetch channels for a specific guild."""
        try:
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }

            url = f"{self.api_base_url}/guilds/{guild_id}/channels"

            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": f"MESH-Connector/{self.platform}"}
                )

            async with self._session.get(url, headers=headers) as response:
                await self._handle_rate_limit_response(response)

                if response.status == 200:
                    channels = await response.json()
                    # Filter for text channels
                    text_channels = [
                        ch for ch in channels
                        # Text channel types
                        if ch.get('type') in [0, 5, 10, 11, 12]
                    ]
                    return text_channels
                else:
                    logger.warning(
                        f"Failed to fetch channels for guild {guild_id}: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching guild channels for {guild_id}: {e}")
            return []

    async def _fetch_dm_channels(self) -> List[Dict[str, Any]]:
        """Fetch DM channels."""
        try:
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }

            url = f"{self.api_base_url}/users/@me/channels"

            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": f"MESH-Connector/{self.platform}"}
                )

            async with self._session.get(url, headers=headers) as response:
                await self._handle_rate_limit_response(response)

                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(
                        f"Failed to fetch DM channels: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching DM channels: {e}")
            return []

    async def _fetch_channel_history(
        self,
        channel_id: str,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """Fetch message history for a specific channel."""
        try:
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }

            params = {
                'limit': min(limit, self.max_results)
            }

            if cursor:
                params['before'] = cursor

            url = f"{self.api_base_url}/channels/{channel_id}/messages"

            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": f"MESH-Connector/{self.platform}"}
                )

            async with self._session.get(url, headers=headers, params=params) as response:
                await self._handle_rate_limit_response(response)

                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch history for channel {channel_id}: {response.status}")
                    return []

                messages = await response.json()
                raw_messages = []

                for message in messages:
                    # Skip bot messages and system messages
                    if (message.get('author', {}).get('bot') or
                            message.get('type', 0) != 0):
                        continue

                    raw_message = RawMessage(
                        id=f"discord_{message.get('id', '')}",
                        platform=self.platform,
                        platform_message_id=message.get('id', ''),
                        thread_id=channel_id,
                        sender_id=message.get('author', {}).get('id', ''),
                        content=self._extract_message_content(message),
                        timestamp=self._extract_timestamp(message),
                        raw_data=message
                    )

                    raw_messages.append(raw_message)

                return raw_messages

        except Exception as e:
            logger.error(
                f"Error fetching channel history for {channel_id}: {e}")
            return []

    async def _handle_rate_limit_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle rate limit headers from Discord API response."""
        try:
            # Update rate limit info from headers
            self._rate_limit_remaining = int(
                response.headers.get('X-RateLimit-Remaining', 1))
            self._rate_limit_reset_after = float(
                response.headers.get('X-RateLimit-Reset-After', 0))
            self._rate_limit_bucket = response.headers.get(
                'X-RateLimit-Bucket', 'global')

            # Handle rate limit exceeded
            if response.status == 429:
                retry_after = float(response.headers.get('Retry-After', 1))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)

        except Exception as e:
            logger.error(f"Error handling rate limit response: {e}")

    async def _handle_rate_limit(self) -> None:
        """Handle rate limiting between requests."""
        if self._rate_limit_remaining <= 1 and self._rate_limit_reset_after > 0:
            logger.debug(
                f"Rate limit approaching, waiting {self._rate_limit_reset_after} seconds")
            await asyncio.sleep(self._rate_limit_reset_after)

    def _extract_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from Discord message."""
        content = {
            'text': message.get('content', ''),
            'attachments': [],
            'embeds': message.get('embeds', [])
        }

        # Handle file attachments
        attachments = message.get('attachments', [])
        for attachment in attachments:
            content['attachments'].append({
                'id': attachment.get('id'),
                'filename': attachment.get('filename'),
                'size': attachment.get('size'),
                'url': attachment.get('url'),
                'proxy_url': attachment.get('proxy_url'),
                'content_type': attachment.get('content_type')
            })

        return content

    def _extract_timestamp(self, message: Dict[str, Any]) -> datetime:
        """Extract timestamp from Discord message."""
        timestamp_str = message.get('timestamp')
        if timestamp_str:
            try:
                # Discord timestamps are ISO 8601 format
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        return datetime.now(timezone.utc)

    async def _validate_webhook_signature(self, payload: Dict[str, Any]) -> None:
        """Validate webhook signature from Discord."""
        # Implementation would verify the signature using webhook_secret
        # This is a placeholder for webhook validation logic
        if self.webhook_secret:
            logger.debug(
                "Discord webhook signature validation not fully implemented")

    async def _platform_health_check(self) -> None:
        """Discord-specific health check."""
        try:
            if not self.bot_token:
                raise DiscordConnectorError("Bot token not available")

            # Test API access
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }

            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": f"MESH-Connector/{self.platform}"}
                )

            async with self._session.get(f"{self.api_base_url}/users/@me", headers=headers) as response:
                if response.status != 200:
                    raise DiscordConnectorError(
                        f"API test failed: {response.status}")

                bot_user = await response.json()
                logger.debug(
                    f"Discord health check passed for bot: {bot_user.get('username')}")

        except Exception as e:
            logger.error(f"Discord health check failed: {e}")
            raise DiscordConnectorError(f"Health check failed: {e}")

    def get_guild_info(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get guild information from cache."""
        return self._guilds_cache.get(guild_id)

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information from cache."""
        return self._channels_cache.get(channel_id)

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from cache."""
        return self._users_cache.get(user_id)
