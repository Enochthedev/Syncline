"""
Integration tests for WhatsApp Integration Service.

Tests the complete WhatsApp integration flow including:
- Bridge pool management
- User connection flow
- Message processing pipeline
- Sync scheduling
- Academic evaluation metrics
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from integrations.whatsapp_integration_service import (
    WhatsAppIntegrationService, WhatsAppPreferences, SyncTier,
    UserConnectionStatus, BridgePool, SyncScheduler, WhatsAppMessageProcessor
)
from services.event_bus import EventBus, Event, EventType


class TestWhatsAppIntegrationService:
    """Test WhatsApp integration service functionality."""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def whatsapp_config(self):
        """Sample WhatsApp integration configuration."""
        return {
            'max_bridges': 10,
            'matrix_config': {
                'homeserver_url': 'http://matrix.remi.local:8008',
                'access_token': 'test_matrix_token',
                'user_id': '@remi_bot:matrix.remi.local',
                'device_id': 'REMI_WHATSAPP_HUB',
                'bridges': {
                    'whatsapp': {
                        'enabled': True,
                        'executable_path': 'mautrix-whatsapp',
                        'config_path': './bridges/whatsapp/config.yaml',
                        'database_path': './bridges/whatsapp/whatsapp.db'
                    }
                }
            }
        }

    @pytest.fixture
    def whatsapp_service(self, whatsapp_config, mock_event_bus):
        """Create WhatsApp integration service instance."""
        # Since docker is optional, we can create the service directly
        service = WhatsAppIntegrationService(
            whatsapp_config, event_bus=mock_event_bus)
        return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, whatsapp_service):
        """Test WhatsApp service initialization."""
        assert whatsapp_service.platform == "whatsapp"
        assert isinstance(whatsapp_service.bridge_pool, BridgePool)
        assert isinstance(whatsapp_service.sync_scheduler, SyncScheduler)
        assert whatsapp_service.bridge_pool.max_size == 10

    @pytest.mark.asyncio
    async def test_user_connection_flow_immediate(self, whatsapp_service):
        """Test immediate WhatsApp connection when bridge is available."""
        # Mock bridge pool to have available bridge
        with patch.object(whatsapp_service.bridge_pool, 'get_available_bridge', return_value='real_time_0'), \
                patch.object(whatsapp_service.bridge_pool, 'assign_bridge', return_value=True), \
                patch.object(whatsapp_service, '_generate_qr_code', return_value='test_qr_code'):

            preferences = WhatsAppPreferences(
                sync_tier=SyncTier.REAL_TIME,
                include_groups=False,
                include_dms=True
            )

            result = await whatsapp_service.connect_whatsapp('user123', preferences)

            assert result['status'] == 'ready'
            assert 'session_id' in result
            assert result['qr_code'] == 'test_qr_code'
            assert result['message'] == 'Scan QR code with WhatsApp to connect'

            # Check user session was created
            assert 'user123' in whatsapp_service.user_sessions
            session = whatsapp_service.user_sessions['user123']
            assert session.status == UserConnectionStatus.CONNECTING
            assert session.bridge_id == 'real_time_0'

    @pytest.mark.asyncio
    async def test_user_connection_flow_queued(self, whatsapp_service):
        """Test user queuing when no bridges are available."""
        # Mock bridge pool to have no available bridges
        with patch.object(whatsapp_service.bridge_pool, 'get_available_bridge', return_value=None), \
                patch.object(whatsapp_service.sync_scheduler, 'queue_user', return_value=3):

            preferences = WhatsAppPreferences(
                sync_tier=SyncTier.REAL_TIME,
                include_groups=True,
                include_dms=True
            )

            result = await whatsapp_service.connect_whatsapp('user456', preferences)

            assert result['status'] == 'queued'
            assert result['queue_position'] == 3
            assert result['estimated_wait_minutes'] == 45  # 3 * 15 minutes
            assert 'You\'re #3 in queue' in result['message']

            # Check user session was created
            assert 'user456' in whatsapp_service.user_sessions
            session = whatsapp_service.user_sessions['user456']
            assert session.status == UserConnectionStatus.QUEUED
            assert session.queue_position == 3

    @pytest.mark.asyncio
    async def test_connection_status_retrieval(self, whatsapp_service):
        """Test retrieving user connection status."""
        # Create a mock user session
        from integrations.whatsapp_integration_service import UserSession
        session = UserSession(
            user_id='user789',
            session_id='session123',
            status=UserConnectionStatus.CONNECTED,
            preferences=WhatsAppPreferences(),
            bridge_id='daily_batch_0',
            connected_at=datetime.now(timezone.utc)
        )
        whatsapp_service.user_sessions['user789'] = session

        status = await whatsapp_service.get_connection_status('user789')

        assert status['status'] == 'connected'
        assert status['session_id'] == 'session123'
        assert status['bridge_id'] == 'daily_batch_0'
        assert 'connected_at' in status
        assert status['preferences']['sync_tier'] == 'daily_batch'

    @pytest.mark.asyncio
    async def test_disconnect_whatsapp(self, whatsapp_service):
        """Test disconnecting WhatsApp account."""
        # Create a mock user session
        from integrations.whatsapp_integration_service import UserSession
        session = UserSession(
            user_id='user999',
            session_id='session456',
            status=UserConnectionStatus.CONNECTED,
            preferences=WhatsAppPreferences(),
            bridge_id='hourly_batch_1'
        )
        whatsapp_service.user_sessions['user999'] = session

        with patch.object(whatsapp_service.bridge_pool, 'release_bridge', return_value=True):
            result = await whatsapp_service.disconnect_whatsapp('user999')

            assert result['status'] == 'disconnected'
            assert 'user999' not in whatsapp_service.user_sessions

    @pytest.mark.asyncio
    async def test_metrics_collection(self, whatsapp_service):
        """Test academic evaluation metrics collection."""
        # Create mock user sessions and bridge data
        from integrations.whatsapp_integration_service import UserSession, BridgeInstance

        # Add connected user
        session1 = UserSession(
            user_id='user1',
            session_id='session1',
            status=UserConnectionStatus.CONNECTED,
            preferences=WhatsAppPreferences(),
            bridge_id='real_time_0'
        )
        whatsapp_service.user_sessions['user1'] = session1

        # Add queued user
        session2 = UserSession(
            user_id='user2',
            session_id='session2',
            status=UserConnectionStatus.QUEUED,
            preferences=WhatsAppPreferences()
        )
        whatsapp_service.user_sessions['user2'] = session2

        # Mock bridge pool
        bridge1 = BridgeInstance(
            bridge_id='real_time_0',
            container_id='container123',
            status='running',
            assigned_user='user1',
            sync_tier=SyncTier.REAL_TIME,
            created_at=datetime.now(timezone.utc)
        )
        whatsapp_service.bridge_pool.bridges['real_time_0'] = bridge1

        bridge2 = BridgeInstance(
            bridge_id='real_time_1',
            container_id='container456',
            status='running',
            assigned_user=None,
            sync_tier=SyncTier.REAL_TIME,
            created_at=datetime.now(timezone.utc)
        )
        whatsapp_service.bridge_pool.bridges['real_time_1'] = bridge2

        metrics = await whatsapp_service.get_metrics()

        assert metrics['total_users'] == 2
        assert metrics['active_connections'] == 1
        assert metrics['bridge_utilization'] == 0.5  # 1 of 2 bridges assigned
        assert metrics['bridge_pool_size'] == 2
        assert 'queue_lengths' in metrics


class TestBridgePool:
    """Test bridge pool management."""

    @pytest.fixture
    def bridge_pool(self):
        """Create bridge pool instance."""
        with patch('integrations.whatsapp_integration_service.docker.from_env'):
            pool = BridgePool(max_size=5)
            return pool

    @pytest.mark.asyncio
    async def test_bridge_pool_initialization(self, bridge_pool):
        """Test bridge pool initialization."""
        with patch.object(bridge_pool, '_create_initial_bridges') as mock_create:
            await bridge_pool.initialize()
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_bridge(self, bridge_pool):
        """Test getting available bridge for specific tier."""
        # Mock bridges
        from integrations.whatsapp_integration_service import BridgeInstance
        bridge1 = BridgeInstance(
            bridge_id='real_time_0',
            container_id='container1',
            status='running',
            assigned_user=None,  # Available
            sync_tier=SyncTier.REAL_TIME,
            created_at=datetime.now(timezone.utc)
        )
        bridge2 = BridgeInstance(
            bridge_id='real_time_1',
            container_id='container2',
            status='running',
            assigned_user='user123',  # Assigned
            sync_tier=SyncTier.REAL_TIME,
            created_at=datetime.now(timezone.utc)
        )

        bridge_pool.bridges['real_time_0'] = bridge1
        bridge_pool.bridges['real_time_1'] = bridge2

        available = await bridge_pool.get_available_bridge(SyncTier.REAL_TIME)
        assert available == 'real_time_0'

    @pytest.mark.asyncio
    async def test_assign_and_release_bridge(self, bridge_pool):
        """Test bridge assignment and release."""
        # Mock bridge
        from integrations.whatsapp_integration_service import BridgeInstance
        bridge = BridgeInstance(
            bridge_id='hourly_batch_0',
            container_id='container3',
            status='running',
            assigned_user=None,
            sync_tier=SyncTier.HOURLY_BATCH,
            created_at=datetime.now(timezone.utc)
        )
        bridge_pool.bridges['hourly_batch_0'] = bridge

        # Test assignment
        success = await bridge_pool.assign_bridge('hourly_batch_0', 'user456')
        assert success is True
        assert bridge_pool.bridges['hourly_batch_0'].assigned_user == 'user456'

        # Test release
        success = await bridge_pool.release_bridge('hourly_batch_0')
        assert success is True
        assert bridge_pool.bridges['hourly_batch_0'].assigned_user is None


class TestSyncScheduler:
    """Test sync scheduling functionality."""

    @pytest.fixture
    def sync_scheduler(self):
        """Create sync scheduler instance."""
        mock_bridge_pool = Mock()
        scheduler = SyncScheduler(mock_bridge_pool)
        return scheduler

    @pytest.mark.asyncio
    async def test_user_queuing(self, sync_scheduler):
        """Test user queuing for different sync tiers."""
        # Queue users for real-time tier
        position1 = sync_scheduler.queue_user('user1', SyncTier.REAL_TIME)
        position2 = sync_scheduler.queue_user('user2', SyncTier.REAL_TIME)
        position3 = sync_scheduler.queue_user(
            'user1', SyncTier.REAL_TIME)  # Duplicate

        assert position1 == 1
        assert position2 == 2
        assert position3 == 1  # Should return existing position

        # Check queue state
        assert len(sync_scheduler.user_queues[SyncTier.REAL_TIME]) == 2
        assert 'user1' in sync_scheduler.user_queues[SyncTier.REAL_TIME]
        assert 'user2' in sync_scheduler.user_queues[SyncTier.REAL_TIME]

    @pytest.mark.asyncio
    async def test_tier_processing(self, sync_scheduler):
        """Test processing sync requests for specific tier."""
        # Setup mock bridge pool
        sync_scheduler.bridge_pool.get_available_bridge = AsyncMock(
            return_value='test_bridge')
        sync_scheduler.bridge_pool.assign_bridge = AsyncMock(return_value=True)

        # Queue a user
        sync_scheduler.user_queues[SyncTier.DAILY_BATCH] = ['user123']

        # Process tier
        await sync_scheduler._process_tier(SyncTier.DAILY_BATCH)

        # Verify bridge assignment
        sync_scheduler.bridge_pool.get_available_bridge.assert_called_once_with(
            SyncTier.DAILY_BATCH)
        sync_scheduler.bridge_pool.assign_bridge.assert_called_once_with(
            'test_bridge', 'user123')

        # Verify user was removed from queue
        assert len(sync_scheduler.user_queues[SyncTier.DAILY_BATCH]) == 0


class TestWhatsAppMessageProcessor:
    """Test WhatsApp message processing pipeline."""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def message_processor(self, mock_event_bus):
        """Create message processor instance."""
        return WhatsAppMessageProcessor(mock_event_bus)

    @pytest.mark.asyncio
    async def test_matrix_event_processing(self, message_processor):
        """Test processing Matrix event into R.E.M.I format."""
        # Mock Matrix event
        matrix_event = {
            'event_id': '$test_event_123',
            'sender': '@whatsapp_user:matrix.remi.local',
            'room_id': '!whatsapp_room:matrix.remi.local',
            'origin_server_ts': int(datetime.now(timezone.utc).timestamp() * 1000),
            'content': {
                'msgtype': 'm.text',
                'body': 'Hello from WhatsApp!'
            }
        }

        # Mock contact resolver
        with patch.object(message_processor.contact_resolver, 'resolve_contact') as mock_resolve:
            mock_resolve.return_value = {
                'id': '@whatsapp_user:matrix.remi.local',
                'name': 'WhatsApp User',
                'phone': '+1234567890'
            }

            await message_processor.handle_matrix_event(matrix_event)

            # Verify event was published to R.E.M.I pipeline
            message_processor.event_bus.publish.assert_called_once()
            call_args = message_processor.event_bus.publish.call_args

            assert call_args[0][0] == 'remi:messages:whatsapp'
            event = call_args[0][1]
            assert event.type == EventType.MESSAGE_RECEIVED
            assert event.data['platform'] == 'whatsapp'
            assert 'Hello from WhatsApp!' in str(event.data['message'])

    def test_user_extraction_from_room(self, message_processor):
        """Test extracting R.E.M.I user ID from Matrix room ID."""
        room_id = '!whatsapp_user123_room:matrix.remi.local'
        user_id = message_processor.extract_user_from_matrix_room(room_id)

        # Should extract user identifier from room
        assert 'user_from_room_' in user_id
        assert room_id in user_id

    def test_chat_type_determination(self, message_processor):
        """Test determining chat type (DM vs group)."""
        # Test DM event
        dm_event = {
            'room_id': '!dm_room:matrix.remi.local',
            'content': {'body': 'Direct message'}
        }
        chat_type = message_processor._determine_chat_type(dm_event)
        assert chat_type == 'dm'


class TestAcademicEvaluation:
    """Test academic evaluation features and metrics."""

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, whatsapp_service):
        """Test collection of performance metrics for academic evaluation."""
        # Simulate message processing
        whatsapp_service.metrics['messages_processed'] = 1500
        whatsapp_service.metrics['sync_latency_ms'] = 250.5

        metrics = await whatsapp_service.get_metrics()

        # Verify academic evaluation metrics
        assert 'total_users' in metrics
        assert 'active_connections' in metrics
        assert 'messages_processed' in metrics
        assert 'sync_latency_ms' in metrics
        assert 'bridge_utilization' in metrics
        assert 'bridge_pool_size' in metrics
        assert 'queue_lengths' in metrics

        # Verify performance data
        assert metrics['messages_processed'] == 1500
        assert metrics['sync_latency_ms'] == 250.5

    @pytest.mark.asyncio
    async def test_scalability_demonstration(self, whatsapp_service):
        """Test scalability features for academic demonstration."""
        # Simulate 50 concurrent users across different tiers
        from integrations.whatsapp_integration_service import UserSession

        for i in range(50):
            tier = [SyncTier.REAL_TIME, SyncTier.HOURLY_BATCH,
                    SyncTier.DAILY_BATCH][i % 3]
            status = UserConnectionStatus.CONNECTED if i < 30 else UserConnectionStatus.QUEUED

            session = UserSession(
                user_id=f'user{i}',
                session_id=f'session{i}',
                status=status,
                preferences=WhatsAppPreferences(sync_tier=tier),
                bridge_id=f'bridge_{i % 10}' if status == UserConnectionStatus.CONNECTED else None
            )
            whatsapp_service.user_sessions[f'user{i}'] = session

        metrics = await whatsapp_service.get_metrics()

        # Verify scalability metrics
        assert metrics['total_users'] == 50
        assert metrics['active_connections'] == 30  # Connected users

        # Demonstrate resource efficiency
        bridge_utilization = metrics['bridge_utilization']
        assert 0 <= bridge_utilization <= 1.0

    @pytest.mark.asyncio
    async def test_cross_platform_intelligence(self, message_processor):
        """Test cross-platform message correlation for AI agentic behavior."""
        # Mock WhatsApp message about same topic as Gmail
        whatsapp_event = {
            'event_id': '$whatsapp_event_123',
            'sender': '@john_doe:matrix.remi.local',
            'room_id': '!whatsapp_room:matrix.remi.local',
            'origin_server_ts': int(datetime.now(timezone.utc).timestamp() * 1000),
            'content': {
                'msgtype': 'm.text',
                'body': 'Can we schedule the project meeting for tomorrow?'
            }
        }

        with patch.object(message_processor.contact_resolver, 'resolve_contact') as mock_resolve:
            mock_resolve.return_value = {
                'id': '@john_doe:matrix.remi.local',
                'name': 'John Doe',
                'email': 'john.doe@company.com',  # Cross-platform correlation
                'phone': '+1234567890',
                'platform_specific': {
                    'whatsapp_id': '@john_doe:matrix.remi.local',
                    'gmail_id': 'john.doe@company.com'
                }
            }

            await message_processor.handle_matrix_event(whatsapp_event)

            # Verify cross-platform contact resolution
            mock_resolve.assert_called_once()

            # Verify message contains cross-platform metadata
            call_args = message_processor.event_bus.publish.call_args
            message_data = call_args[0][1].data['message']

            assert message_data['sender']['email'] == 'john.doe@company.com'
            assert 'gmail_id' in message_data['sender']['platform_specific']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
