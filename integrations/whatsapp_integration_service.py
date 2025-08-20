"""
WhatsApp Integration Service for R.E.M.I System

Implements scalable WhatsApp message aggregation using mautrix-whatsapp bridge
with tiered sync strategies and bridge pooling for production-ready architecture.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
import aiohttp

# Optional Docker dependency
try:
    import docker
    from docker.errors import DockerException
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False
    DockerException = Exception

from .matrix_bridge_hub import MatrixBridgeHub, BridgeConfig, BridgeType, AuthMethod
from .base_connector import BaseConnector, RawMessage
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform

logger = logging.getLogger(__name__)


class SyncTier(Enum):
    """WhatsApp sync tiers for scalable architecture."""
    REAL_TIME = "real_time"      # 5 bridges for premium/demo users
    HOURLY_BATCH = "hourly_batch"  # 3 bridges rotating through users
    DAILY_BATCH = "daily_batch"    # 2 bridges for bulk processing


class UserConnectionStatus(Enum):
    """User WhatsApp connection status."""
    DISCONNECTED = "disconnected"
    QUEUED = "queued"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"


@dataclass
class WhatsAppPreferences:
    """User preferences for WhatsApp integration."""
    sync_tier: SyncTier = SyncTier.DAILY_BATCH
    include_groups: bool = False
    include_dms: bool = True
    sync_history_days: int = 30
    auto_sync: bool = True
    notification_keywords: List[str] = field(default_factory=list)


@dataclass
class UserSession:
    """WhatsApp user session management."""
    user_id: str
    session_id: str
    status: UserConnectionStatus
    preferences: WhatsAppPreferences
    bridge_id: Optional[str] = None
    qr_code: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    queue_position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeInstance:
    """WhatsApp bridge instance in the pool."""
    bridge_id: str
    container_id: Optional[str]
    status: str
    assigned_user: Optional[str]
    sync_tier: SyncTier
    created_at: datetime
    last_activity: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0


class BridgePool:
    """Manages pool of WhatsApp bridges for scalable architecture."""

    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.bridges: Dict[str, BridgeInstance] = {}
        self.docker_client = None
        self.tier_allocation = {
            SyncTier.REAL_TIME: 5,
            SyncTier.HOURLY_BATCH: 3,
            SyncTier.DAILY_BATCH: 2
        }

    async def initialize(self):
        """Initialize Docker client and bridge pool."""
        try:
            if not HAS_DOCKER:
                logger.warning("Docker not available, using mock bridge pool")
                return

            self.docker_client = docker.from_env()
            await self._create_initial_bridges()
            logger.info(
                f"Bridge pool initialized with {len(self.bridges)} bridges")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    async def _create_initial_bridges(self):
        """Create initial set of bridges based on tier allocation."""
        for tier, count in self.tier_allocation.items():
            for i in range(count):
                bridge_id = f"{tier.value}_{i}"
                await self._spawn_bridge(bridge_id, tier)

    async def _spawn_bridge(self, bridge_id: str, tier: SyncTier) -> BridgeInstance:
        """Spawn a new mautrix-whatsapp bridge container."""
        try:
            if not HAS_DOCKER or not self.docker_client:
                # Mock bridge for testing/development
                bridge_instance = BridgeInstance(
                    bridge_id=bridge_id,
                    container_id=f"mock_container_{bridge_id}",
                    status="running",
                    assigned_user=None,
                    sync_tier=tier,
                    created_at=datetime.now(timezone.utc)
                )
                self.bridges[bridge_id] = bridge_instance
                logger.info(f"Created mock bridge {bridge_id}")
                return bridge_instance

            # Bridge configuration
            config_volume = f"whatsapp_bridge_{bridge_id}_config"
            data_volume = f"whatsapp_bridge_{bridge_id}_data"

            # Create container
            container = self.docker_client.containers.run(
                "dock.mau.dev/mautrix/whatsapp:latest",
                name=f"whatsapp_bridge_{bridge_id}",
                detach=True,
                volumes={
                    config_volume: {'bind': '/data', 'mode': 'rw'}
                },
                environment={
                    'MAUTRIX_BRIDGE_ID': bridge_id,
                    'MAUTRIX_SYNC_TIER': tier.value
                },
                network_mode="bridge",
                restart_policy={"Name": "unless-stopped"}
            )

            bridge_instance = BridgeInstance(
                bridge_id=bridge_id,
                container_id=container.id,
                status="starting",
                assigned_user=None,
                sync_tier=tier,
                created_at=datetime.now(timezone.utc)
            )

            self.bridges[bridge_id] = bridge_instance
            logger.info(
                f"Spawned bridge {bridge_id} with container {container.id}")

            return bridge_instance

        except DockerException as e:
            logger.error(f"Failed to spawn bridge {bridge_id}: {e}")
            raise

    async def get_available_bridge(self, tier: SyncTier) -> Optional[str]:
        """Get an available bridge for the specified tier."""
        available_bridges = [
            bridge_id for bridge_id, bridge in self.bridges.items()
            if bridge.sync_tier == tier and bridge.assigned_user is None
        ]
        return available_bridges[0] if available_bridges else None

    async def assign_bridge(self, bridge_id: str, user_id: str) -> bool:
        """Assign a bridge to a user."""
        if bridge_id in self.bridges:
            self.bridges[bridge_id].assigned_user = user_id
            self.bridges[bridge_id].last_activity = datetime.now(timezone.utc)
            return True
        return False

    async def release_bridge(self, bridge_id: str) -> bool:
        """Release a bridge from user assignment."""
        if bridge_id in self.bridges:
            self.bridges[bridge_id].assigned_user = None
            return True
        return False

    async def cleanup_bridge(self, bridge_id: str) -> bool:
        """Clean up and recycle a bridge."""
        try:
            if bridge_id in self.bridges:
                bridge = self.bridges[bridge_id]
                if bridge.container_id:
                    container = self.docker_client.containers.get(
                        bridge.container_id)
                    container.stop()
                    container.remove()

                # Respawn fresh bridge
                await self._spawn_bridge(bridge_id, bridge.sync_tier)
                return True
        except DockerException as e:
            logger.error(f"Failed to cleanup bridge {bridge_id}: {e}")
        return False


class SyncScheduler:
    """Manages sync scheduling across different tiers."""

    def __init__(self, bridge_pool: BridgePool):
        self.bridge_pool = bridge_pool
        self.user_queues: Dict[SyncTier, List[str]] = {
            tier: [] for tier in SyncTier
        }
        self.scheduler_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """Start the sync scheduler."""
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Sync scheduler started")

    async def stop(self):
        """Stop the sync scheduler."""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Sync scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                # Process real-time tier every 30 seconds
                await self._process_tier(SyncTier.REAL_TIME)

                # Process hourly tier every hour
                if datetime.now().minute == 0:
                    await self._process_tier(SyncTier.HOURLY_BATCH)

                # Process daily tier at midnight
                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    await self._process_tier(SyncTier.DAILY_BATCH)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _process_tier(self, tier: SyncTier):
        """Process sync requests for a specific tier."""
        queue = self.user_queues[tier]
        if not queue:
            return

        available_bridge = await self.bridge_pool.get_available_bridge(tier)
        if available_bridge:
            user_id = queue.pop(0)
            await self.bridge_pool.assign_bridge(available_bridge, user_id)
            logger.info(
                f"Assigned bridge {available_bridge} to user {user_id} for {tier.value}")

    def queue_user(self, user_id: str, tier: SyncTier) -> int:
        """Queue a user for sync and return position."""
        if user_id not in self.user_queues[tier]:
            self.user_queues[tier].append(user_id)
        return self.user_queues[tier].index(user_id) + 1


class WhatsAppIntegrationService(BaseConnector):
    """
    WhatsApp Integration Service for R.E.M.I System

    Implements scalable WhatsApp message aggregation with:
    - Bridge pooling and lifecycle management
    - Tiered sync strategies (real-time, hourly, daily)
    - User session management with queuing
    - Integration with existing R.E.M.I pipeline
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("whatsapp", config, **kwargs)

        self.event_bus = event_bus

        # Core components
        self.bridge_pool = BridgePool(max_size=config.get('max_bridges', 10))
        self.sync_scheduler = SyncScheduler(self.bridge_pool)

        # User management
        self.user_sessions: Dict[str, UserSession] = {}
        self.connection_queue: List[str] = []

        # Matrix integration
        self.matrix_hub = MatrixBridgeHub(
            config.get('matrix_config', {}),
            event_bus=event_bus
        )

        # Message processing
        self.message_processor = WhatsAppMessageProcessor(event_bus)

        # Monitoring
        self.metrics = {
            'total_users': 0,
            'active_connections': 0,
            'messages_processed': 0,
            'sync_latency_ms': 0,
            'bridge_utilization': 0.0
        }

    async def authenticate(self) -> None:
        """Initialize WhatsApp integration service."""
        try:
            logger.info("Initializing WhatsApp Integration Service")

            # Initialize bridge pool
            await self.bridge_pool.initialize()

            # Start sync scheduler
            await self.sync_scheduler.start()

            # Initialize Matrix hub
            await self.matrix_hub.authenticate()

            logger.info(
                "WhatsApp Integration Service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp service: {e}")
            raise

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion."""
        try:
            await self.matrix_hub.start_real_time_ingestion()
            logger.info("WhatsApp real-time ingestion started")
        except Exception as e:
            logger.error(f"Failed to start WhatsApp ingestion: {e}")
            raise

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            await self.sync_scheduler.stop()
            await self.matrix_hub.stop_real_time_ingestion()
            logger.info("WhatsApp real-time ingestion stopped")
        except Exception as e:
            logger.error(f"Error stopping WhatsApp ingestion: {e}")

    async def connect_whatsapp(
        self,
        user_id: str,
        preferences: WhatsAppPreferences
    ) -> Dict[str, Any]:
        """
        Connect a user's WhatsApp account.

        User Experience Flow:
        1. User clicks "Connect WhatsApp" in R.E.M.I dashboard
        2. System checks bridge availability
        3. If available: Show QR code immediately
        4. If busy: Queue user with estimated wait time
        5. User scans QR with WhatsApp "Link Device"
        6. System confirms connection and starts sync
        """
        try:
            session_id = str(uuid.uuid4())

            # Check bridge availability
            available_bridge = await self.bridge_pool.get_available_bridge(
                preferences.sync_tier
            )

            if available_bridge:
                # Immediate connection
                session = UserSession(
                    user_id=user_id,
                    session_id=session_id,
                    status=UserConnectionStatus.CONNECTING,
                    preferences=preferences,
                    bridge_id=available_bridge
                )

                # Assign bridge
                await self.bridge_pool.assign_bridge(available_bridge, user_id)

                # Generate QR code
                qr_code = await self._generate_qr_code(available_bridge, user_id)
                session.qr_code = qr_code

                self.user_sessions[user_id] = session

                return {
                    "status": "ready",
                    "session_id": session_id,
                    "qr_code": qr_code,
                    "message": "Scan QR code with WhatsApp to connect"
                }

            else:
                # Queue user
                queue_position = self.sync_scheduler.queue_user(
                    user_id, preferences.sync_tier
                )
                estimated_wait = queue_position * 15  # 15 minutes per user estimate

                session = UserSession(
                    user_id=user_id,
                    session_id=session_id,
                    status=UserConnectionStatus.QUEUED,
                    preferences=preferences,
                    queue_position=queue_position,
                    estimated_wait_minutes=estimated_wait
                )

                self.user_sessions[user_id] = session

                return {
                    "status": "queued",
                    "session_id": session_id,
                    "queue_position": queue_position,
                    "estimated_wait_minutes": estimated_wait,
                    "message": f"You're #{queue_position} in queue, ~{estimated_wait} minutes estimated"
                }

        except Exception as e:
            logger.error(f"Failed to connect WhatsApp for user {user_id}: {e}")
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}"
            }

    async def _generate_qr_code(self, bridge_id: str, user_id: str) -> str:
        """Generate QR code for WhatsApp connection."""
        try:
            # This would integrate with the mautrix-whatsapp bridge
            # For now, return a placeholder
            return f"whatsapp_qr_code_{bridge_id}_{user_id}"
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            raise

    async def get_connection_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's WhatsApp connection status."""
        session = self.user_sessions.get(user_id)
        if not session:
            return {"status": "not_found"}

        return {
            "status": session.status.value,
            "session_id": session.session_id,
            "bridge_id": session.bridge_id,
            "queue_position": session.queue_position,
            "estimated_wait_minutes": session.estimated_wait_minutes,
            "connected_at": session.connected_at.isoformat() if session.connected_at else None,
            "last_sync": session.last_sync.isoformat() if session.last_sync else None,
            "preferences": {
                "sync_tier": session.preferences.sync_tier.value,
                "include_groups": session.preferences.include_groups,
                "include_dms": session.preferences.include_dms,
                "sync_history_days": session.preferences.sync_history_days
            }
        }

    async def disconnect_whatsapp(self, user_id: str) -> Dict[str, Any]:
        """Disconnect user's WhatsApp account."""
        try:
            session = self.user_sessions.get(user_id)
            if not session:
                return {"status": "not_found"}

            # Release bridge
            if session.bridge_id:
                await self.bridge_pool.release_bridge(session.bridge_id)

            # Remove session
            del self.user_sessions[user_id]

            return {"status": "disconnected"}

        except Exception as e:
            logger.error(
                f"Failed to disconnect WhatsApp for user {user_id}: {e}")
            return {"status": "error", "message": str(e)}

    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for academic evaluation."""
        active_connections = len([
            s for s in self.user_sessions.values()
            if s.status == UserConnectionStatus.CONNECTED
        ])

        bridge_utilization = len([
            b for b in self.bridge_pool.bridges.values()
            if b.assigned_user is not None
        ]) / len(self.bridge_pool.bridges) if self.bridge_pool.bridges else 0

        return {
            "total_users": len(self.user_sessions),
            "active_connections": active_connections,
            "messages_processed": self.metrics['messages_processed'],
            "sync_latency_ms": self.metrics['sync_latency_ms'],
            "bridge_utilization": bridge_utilization,
            "bridge_pool_size": len(self.bridge_pool.bridges),
            "queue_lengths": {
                tier.value: len(queue)
                for tier, queue in self.sync_scheduler.user_queues.items()
            }
        }

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """Fetch historical WhatsApp messages."""
        return await self.matrix_hub.fetch_historical_messages(cursor, limit)

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Handle WhatsApp webhook events."""
        await self.matrix_hub.handle_webhook(payload)


class WhatsAppMessageProcessor:
    """
    Processes WhatsApp messages from Matrix events into R.E.M.I format.

    Integration with existing R.E.M.I infrastructure:
    WhatsApp → mautrix-bridge → Matrix → R.E.M.I Event Bus → AI Processing
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.contact_resolver = WhatsAppContactResolver()

    async def handle_matrix_event(self, matrix_event: Dict[str, Any]) -> None:
        """Transform Matrix event to R.E.M.I format."""
        try:
            # Extract user from Matrix room
            user_id = self.extract_user_from_matrix_room(
                matrix_event.get('room_id', ''))

            # Resolve contact information
            sender_info = await self.contact_resolver.resolve_contact(
                matrix_event.get('sender', '')
            )

            # Determine chat type
            chat_type = self._determine_chat_type(matrix_event)

            # Create R.E.M.I message format
            remi_message = {
                "platform": "whatsapp",
                "user_id": user_id,
                "sender": sender_info,
                "content": matrix_event.get('content', {}).get('body', ''),
                "timestamp": matrix_event.get('origin_server_ts', 0),
                "chat_type": chat_type,
                "metadata": {
                    "matrix_event_id": matrix_event.get('event_id', ''),
                    "whatsapp_chat_id": matrix_event.get('room_id', ''),
                    "message_type": matrix_event.get('content', {}).get('msgtype', 'm.text')
                }
            }

            # Send to existing R.E.M.I Redis Streams
            if self.event_bus:
                event = Event(
                    type=EventType.MESSAGE_RECEIVED,
                    data={
                        'platform': 'whatsapp',
                        'message': remi_message
                    },
                    source='whatsapp_integration'
                )

                await self.event_bus.publish('remi:messages:whatsapp', event)
                logger.debug(
                    f"Published WhatsApp message to R.E.M.I pipeline: {remi_message['metadata']['matrix_event_id']}")

        except Exception as e:
            logger.error(f"Failed to process WhatsApp message: {e}")

    def extract_user_from_matrix_room(self, room_id: str) -> str:
        """Extract R.E.M.I user ID from Matrix room ID."""
        # This would implement the mapping logic
        # For now, return a placeholder
        return f"user_from_room_{room_id}"

    def _determine_chat_type(self, matrix_event: Dict[str, Any]) -> str:
        """Determine if message is from DM or group chat."""
        # Logic to determine chat type based on Matrix room properties
        # For now, default to DM
        return "dm"


class WhatsAppContactResolver:
    """Resolves WhatsApp contacts with existing R.E.M.I contact system."""

    async def resolve_contact(self, matrix_sender: str) -> Dict[str, Any]:
        """
        Integrate with existing R.E.M.I contact system.
        Cross-reference WhatsApp contacts with Gmail, phone contacts.
        Build unified contact graph across platforms.
        """
        try:
            # This would integrate with the existing contact resolution system
            return {
                "id": matrix_sender,
                "name": f"Contact_{matrix_sender}",
                "phone": None,
                "email": None,
                "platform_specific": {
                    "whatsapp_id": matrix_sender,
                    "matrix_id": matrix_sender
                }
            }
        except Exception as e:
            logger.error(f"Failed to resolve contact {matrix_sender}: {e}")
            return {"id": matrix_sender, "name": "Unknown Contact"}
