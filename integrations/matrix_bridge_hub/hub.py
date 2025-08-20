"""
Main Matrix bridge hub implementation.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import aiohttp

from ..base_connector import BaseConnector, RawMessage, AuthenticationError
from services.event_bus import EventBus, Event, EventType

from .types import (
    BridgeType, BridgeStatus, BridgeConfig, BridgeInstance,
    MatrixBridgeHubError, AuthMethod
)
from .auth_manager import MatrixAuthManager
from .bridge_manager import BridgeManager

logger = logging.getLogger(__name__)


class MatrixBridgeHub(BaseConnector):
    """
    Matrix bridge hub for managing multiple Matrix bridges.

    Provides unified management of WhatsApp, Instagram/Facebook Messenger,
    and other mautrix-based integrations with authentication and session management.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("matrix_hub", config, **kwargs)

        self.event_bus = event_bus

        # Matrix configuration
        self.homeserver_url = config.get(
            'homeserver_url', 'https://matrix.org')
        self.access_token = config.get('access_token')
        self.user_id = config.get('user_id')
        self.device_id = config.get('device_id', 'MESH_BRIDGE_HUB')

        # Managers
        self.auth_manager = MatrixAuthManager(
            homeserver_url=self.homeserver_url,
            access_token=self.access_token,
            user_id=self.user_id,
            device_id=self.device_id
        )
        self.bridge_manager = BridgeManager()

        # Matrix client session
        self._matrix_session: Optional[aiohttp.ClientSession] = None
        self._sync_token: Optional[str] = None
        self._sync_running = False

        # Message processing
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None

        # Initialize bridge configurations
        self._initialize_bridge_configs(config)

    def _initialize_bridge_configs(self, config: Dict[str, Any]) -> None:
        """Initialize bridge configurations from config."""
        try:
            self._bridge_configs_data = config.get('bridges', {})
            logger.info(f"Stored bridge configuration data")

        except Exception as e:
            logger.error(f"Error initializing bridge configs: {e}")
            raise MatrixBridgeHubError(
                f"Failed to initialize bridge configs: {e}")

    async def _setup_bridge_configs(self) -> None:
        """Setup bridge configurations (called during authentication)."""
        try:
            bridges_config = self._bridge_configs_data

            # WhatsApp bridge configuration
            if 'whatsapp' in bridges_config:
                whatsapp_config = bridges_config['whatsapp']
                bridge_config = BridgeConfig(
                    bridge_type=BridgeType.WHATSAPP,
                    bridge_name='mautrix-whatsapp',
                    executable_path=whatsapp_config.get(
                        'executable_path', 'mautrix-whatsapp'),
                    config_path=whatsapp_config.get(
                        'config_path', './bridges/whatsapp/config.yaml'),
                    database_path=whatsapp_config.get(
                        'database_path', './bridges/whatsapp/whatsapp.db'),
                    homeserver_url=self.homeserver_url,
                    access_token=self.access_token,
                    user_id=self.user_id,
                    device_id=f"{self.device_id}_WA",
                    enabled=whatsapp_config.get('enabled', True),
                    environment=whatsapp_config.get('environment', {}),
                    extra_args=whatsapp_config.get('extra_args', []),
                    auth_method=AuthMethod.QR_CODE
                )
                await self.bridge_manager.add_bridge(bridge_config)

            # Instagram/Facebook bridge configuration
            if 'instagram' in bridges_config:
                instagram_config = bridges_config['instagram']
                bridge_config = BridgeConfig(
                    bridge_type=BridgeType.INSTAGRAM,
                    bridge_name='mautrix-meta',
                    executable_path=instagram_config.get(
                        'executable_path', 'mautrix-meta'),
                    config_path=instagram_config.get(
                        'config_path', './bridges/instagram/config.yaml'),
                    database_path=instagram_config.get(
                        'database_path', './bridges/instagram/meta.db'),
                    homeserver_url=self.homeserver_url,
                    access_token=self.access_token,
                    user_id=self.user_id,
                    device_id=f"{self.device_id}_IG",
                    enabled=instagram_config.get('enabled', True),
                    environment=instagram_config.get('environment', {}),
                    extra_args=instagram_config.get('extra_args', []),
                    auth_method=AuthMethod.OAUTH
                )
                await self.bridge_manager.add_bridge(bridge_config)

            # LinkedIn bridge configuration
            if 'linkedin' in bridges_config:
                linkedin_config = bridges_config['linkedin']
                bridge_config = BridgeConfig(
                    bridge_type=BridgeType.LINKEDIN,
                    bridge_name='mautrix-linkedin',
                    executable_path=linkedin_config.get(
                        'executable_path', 'mautrix-linkedin'),
                    config_path=linkedin_config.get(
                        'config_path', './bridges/linkedin/config.yaml'),
                    database_path=linkedin_config.get(
                        'database_path', './bridges/linkedin/linkedin.db'),
                    homeserver_url=self.homeserver_url,
                    access_token=self.access_token,
                    user_id=self.user_id,
                    device_id=f"{self.device_id}_LI",
                    enabled=linkedin_config.get('enabled', True),
                    environment=linkedin_config.get('environment', {}),
                    extra_args=linkedin_config.get('extra_args', []),
                    auth_method=AuthMethod.OAUTH
                )
                await self.bridge_manager.add_bridge(bridge_config)

            logger.info(f"Setup bridge configurations")

        except Exception as e:
            logger.error(f"Error setting up bridge configs: {e}")
            raise MatrixBridgeHubError(f"Failed to setup bridge configs: {e}")

    async def authenticate(self) -> None:
        """Authenticate with Matrix homeserver and initialize managers."""
        try:
            logger.info("Authenticating Matrix bridge hub")

            if not self.access_token:
                raise AuthenticationError("Matrix access token is required")

            if not self.user_id:
                raise AuthenticationError("Matrix user ID is required")

            # Initialize managers
            await self.auth_manager.initialize()
            await self.bridge_manager.initialize()

            # Setup bridge configurations
            await self._setup_bridge_configs()

            logger.info("Matrix bridge hub authentication successful")

        except Exception as e:
            logger.error(f"Matrix bridge hub authentication failed: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion from Matrix bridges."""
        try:
            logger.info("Starting Matrix bridge hub real-time ingestion")

            # Start message processor
            self._processor_task = asyncio.create_task(
                self._process_message_queue())

            # Start Matrix sync
            self._sync_task = asyncio.create_task(self._matrix_sync_loop())

            # Start enabled bridges
            await self._start_enabled_bridges()

            logger.info("Matrix bridge hub real-time ingestion started")

        except Exception as e:
            logger.error(f"Failed to start Matrix bridge hub ingestion: {e}")
            raise MatrixBridgeHubError(f"Failed to start ingestion: {e}")

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            logger.info("Stopping Matrix bridge hub real-time ingestion")

            # Stop Matrix sync
            self._sync_running = False
            if self._sync_task:
                self._sync_task.cancel()
                try:
                    await self._sync_task
                except asyncio.CancelledError:
                    pass
                self._sync_task = None

            # Stop processor
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
                self._processor_task = None

            # Cleanup managers
            await self.bridge_manager.cleanup()
            await self.auth_manager.cleanup()

            # Close Matrix session
            if self._matrix_session:
                await self._matrix_session.close()
                self._matrix_session = None

            logger.info("Matrix bridge hub real-time ingestion stopped")

        except Exception as e:
            logger.error(f"Error stopping Matrix bridge hub ingestion: {e}")

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """Fetch historical messages from Matrix bridges."""
        try:
            logger.debug(
                f"Fetching historical Matrix messages (cursor: {cursor}, limit: {limit})")

            raw_messages = []

            # Get messages from Matrix rooms
            rooms = await self._get_bridge_rooms()

            for room_id in rooms:
                room_messages = await self._fetch_room_history(room_id, cursor, limit)
                raw_messages.extend(room_messages)

            logger.info(f"Fetched {len(raw_messages)} Matrix messages")
            return raw_messages

        except Exception as e:
            logger.error(f"Error fetching Matrix messages: {e}")
            raise MatrixBridgeHubError(f"Error fetching messages: {e}")

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Handle incoming Matrix webhook payload."""
        try:
            logger.debug("Processing Matrix webhook payload")

            # Process Matrix events
            events = payload.get('events', [])
            for event in events:
                await self._handle_matrix_event(event)

        except Exception as e:
            logger.error(f"Error handling Matrix webhook: {e}")
            raise MatrixBridgeHubError(f"Webhook processing failed: {e}")

    async def _start_enabled_bridges(self) -> None:
        """Start all enabled bridges."""
        try:
            start_tasks = []
            for bridge_name, instance in self.bridge_manager.bridge_instances.items():
                if instance.config.enabled:
                    start_tasks.append(
                        self.bridge_manager.start_bridge(bridge_name))

            if start_tasks:
                results = await asyncio.gather(*start_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to start bridge: {result}")

        except Exception as e:
            logger.error(f"Error starting enabled bridges: {e}")

    async def _matrix_sync_loop(self) -> None:
        """Matrix sync loop for real-time events."""
        try:
            logger.info("Starting Matrix sync loop")
            self._sync_running = True

            # Initialize Matrix session
            self._matrix_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "MESH Matrix Bridge Hub"
                }
            )

            while self._sync_running:
                try:
                    # Build sync URL
                    url = f"{self.homeserver_url}/_matrix/client/r0/sync"
                    params = {"timeout": 30000}  # 30 second timeout

                    if self._sync_token:
                        params["since"] = self._sync_token

                    # Make sync request
                    async with self._matrix_session.get(url, params=params) as response:
                        if response.status == 200:
                            sync_data = await response.json()
                            await self._process_sync_response(sync_data)
                        else:
                            logger.warning(
                                f"Matrix sync error: {response.status}")
                            await asyncio.sleep(5)

                except asyncio.CancelledError:
                    logger.info("Matrix sync loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in Matrix sync loop: {e}")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Matrix sync loop error: {e}")
        finally:
            self._sync_running = False

    async def _process_sync_response(self, sync_data: Dict[str, Any]) -> None:
        """Process Matrix sync response."""
        try:
            # Update sync token
            self._sync_token = sync_data.get('next_batch')

            # Process room events
            rooms = sync_data.get('rooms', {})
            joined_rooms = rooms.get('join', {})

            for room_id, room_data in joined_rooms.items():
                timeline = room_data.get('timeline', {})
                events = timeline.get('events', [])

                for event in events:
                    if event.get('type') == 'm.room.message':
                        await self._processing_queue.put({
                            'type': 'matrix_message',
                            'room_id': room_id,
                            'event': event,
                            'timestamp': datetime.now(timezone.utc)
                        })

        except Exception as e:
            logger.error(f"Error processing sync response: {e}")

    async def _process_message_queue(self) -> None:
        """Process queued messages from Matrix events."""
        logger.info("Starting Matrix message queue processor")

        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )

                if item['type'] == 'matrix_message':
                    await self._process_matrix_message(item)

                # Mark task as done
                self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Matrix message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")

    async def _process_matrix_message(self, item: Dict[str, Any]) -> None:
        """Process a Matrix message event."""
        try:
            room_id = item['room_id']
            event = item['event']

            # Extract message data
            sender = event.get('sender', '')
            content = event.get('content', {})
            event_id = event.get('event_id', '')
            timestamp = event.get('origin_server_ts', 0)

            # Convert timestamp
            msg_timestamp = datetime.fromtimestamp(
                timestamp / 1000, tz=timezone.utc)

            # Determine platform based on sender or room
            platform = self._determine_message_platform(sender, room_id)

            # Create raw message
            raw_message = RawMessage(
                id=f"matrix_{event_id}",
                platform=platform,
                platform_message_id=event_id,
                thread_id=room_id,
                sender_id=sender,
                content=self._extract_message_content(content),
                timestamp=msg_timestamp,
                raw_data=event
            )

            # Publish to event bus if available
            if self.event_bus:
                event_obj = Event(
                    type=EventType.MESSAGE_RECEIVED,
                    data={
                        'platform': platform,
                        'message': raw_message.__dict__
                    },
                    source=f"{self.platform}_connector"
                )

                await self.event_bus.publish('messages.raw', event_obj)
                logger.debug(
                    f"Published Matrix message to event bus: {raw_message.id}")

        except Exception as e:
            logger.error(f"Error processing Matrix message: {e}")

    def _determine_message_platform(self, sender: str, room_id: str) -> str:
        """Determine the original platform of a Matrix message."""
        # Check sender for bridge patterns
        if 'whatsapp' in sender.lower():
            return 'whatsapp'
        elif 'instagram' in sender.lower() or 'meta' in sender.lower():
            return 'instagram'
        elif 'facebook' in sender.lower():
            return 'facebook'
        elif 'linkedin' in sender.lower():
            return 'linkedin'
        else:
            return 'matrix'

    def _extract_message_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message content from Matrix event."""
        return {
            'text': content.get('body', ''),
            'msgtype': content.get('msgtype', 'm.text'),
            'format': content.get('format'),
            'formatted_body': content.get('formatted_body'),
            'url': content.get('url'),
            'info': content.get('info', {}),
        }

    async def _get_bridge_rooms(self) -> List[str]:
        """Get list of rooms managed by bridges."""
        try:
            if not self._matrix_session:
                return []

            url = f"{self.homeserver_url}/_matrix/client/r0/joined_rooms"

            async with self._matrix_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('joined_rooms', [])
                else:
                    logger.warning(
                        f"Failed to get joined rooms: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting bridge rooms: {e}")
            return []

    async def _fetch_room_history(
        self,
        room_id: str,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """Fetch message history for a specific room."""
        try:
            if not self._matrix_session:
                return []

            url = f"{self.homeserver_url}/_matrix/client/r0/rooms/{room_id}/messages"
            params = {
                'dir': 'b',  # backwards
                'limit': limit
            }

            if cursor:
                params['from'] = cursor

            async with self._matrix_session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('chunk', [])

                    raw_messages = []
                    for event in events:
                        if event.get('type') == 'm.room.message':
                            # Convert to RawMessage
                            sender = event.get('sender', '')
                            content = event.get('content', {})
                            event_id = event.get('event_id', '')
                            timestamp = event.get('origin_server_ts', 0)

                            msg_timestamp = datetime.fromtimestamp(
                                timestamp / 1000, tz=timezone.utc)
                            platform = self._determine_message_platform(
                                sender, room_id)

                            raw_message = RawMessage(
                                id=f"matrix_{event_id}",
                                platform=platform,
                                platform_message_id=event_id,
                                thread_id=room_id,
                                sender_id=sender,
                                content=self._extract_message_content(content),
                                timestamp=msg_timestamp,
                                raw_data=event
                            )

                            raw_messages.append(raw_message)

                    return raw_messages
                else:
                    logger.warning(
                        f"Failed to fetch room history: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching room history: {e}")
            return []

    async def _handle_matrix_event(self, event: Dict[str, Any]) -> None:
        """Handle a Matrix event from webhook."""
        try:
            event_type = event.get('type')

            if event_type == 'm.room.message':
                await self._processing_queue.put({
                    'type': 'matrix_message',
                    'room_id': event.get('room_id', ''),
                    'event': event,
                    'timestamp': datetime.now(timezone.utc)
                })

        except Exception as e:
            logger.error(f"Error handling Matrix event: {e}")

    # Bridge management methods
    async def start_bridge_auth(self, bridge_name: str) -> Dict[str, Any]:
        """Start authentication for a specific bridge."""
        try:
            instance = self.bridge_manager.bridge_instances.get(bridge_name)
            if not instance:
                raise MatrixBridgeHubError(f"Bridge not found: {bridge_name}")

            auth_session = await self.auth_manager.start_bridge_auth(instance.config)
            return {
                'session_id': auth_session.session_id,
                'auth_method': auth_session.auth_method.value,
                'status': auth_session.status,
                'qr_code': auth_session.qr_data.qr_code if auth_session.qr_data else None,
                'oauth_url': auth_session.metadata.get('oauth_url') if auth_session.metadata else None
            }

        except Exception as e:
            logger.error(f"Error starting bridge auth: {e}")
            raise MatrixBridgeHubError(f"Failed to start bridge auth: {e}")

    async def get_bridge_status(self, bridge_name: str) -> Dict[str, Any]:
        """Get comprehensive status for a bridge."""
        try:
            # Get bridge status
            bridge_status = await self.bridge_manager.get_bridge_status(bridge_name)

            # Get auth status
            auth_status = await self.auth_manager.get_bridge_auth_status(bridge_name)

            # Combine status
            return {
                **bridge_status,
                'auth': auth_status
            }

        except Exception as e:
            logger.error(f"Error getting bridge status: {e}")
            return {"status": "error", "bridge_name": bridge_name, "error": str(e)}

    async def get_all_bridge_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all bridges."""
        try:
            status_data = {}
            for bridge_name in self.bridge_manager.bridge_instances.keys():
                status_data[bridge_name] = await self.get_bridge_status(bridge_name)
            return status_data

        except Exception as e:
            logger.error(f"Error getting all bridge status: {e}")
            return {}
