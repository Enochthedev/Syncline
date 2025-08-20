"""
Integration tests for Matrix bridge hub connectivity and message flow.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from integrations.matrix_bridge_hub import (
    MatrixBridgeHub, BridgeManager, MatrixAuthManager,
    BridgeType, BridgeStatus, BridgeConfig, AuthMethod
)
from integrations.matrix_bridge_hub.types import MatrixBridgeHubError, BridgeAuthError
from services.event_bus import EventBus, Event, EventType


class TestMatrixBridgeHub:
    """Test Matrix bridge hub functionality."""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def bridge_config(self):
        """Sample bridge configuration."""
        return {
            'homeserver_url': 'https://matrix.example.com',
            'access_token': 'test_token_123',
            'user_id': '@testuser:example.com',
            'device_id': 'TEST_DEVICE',
            'bridges': {
                'whatsapp': {
                    'enabled': True,
                    'executable_path': '/usr/local/bin/mautrix-whatsapp',
                    'config_path': './test_bridges/whatsapp/config.yaml',
                    'database_path': './test_bridges/whatsapp/whatsapp.db',
                    'environment': {'LOG_LEVEL': 'DEBUG'},
                    'extra_args': ['--verbose']
                },
                'instagram': {
                    'enabled': True,
                    'executable_path': '/usr/local/bin/mautrix-meta',
                    'config_path': './test_bridges/instagram/config.yaml',
                    'database_path': './test_bridges/instagram/meta.db',
                    'environment': {'META_MODE': 'instagram'}
                }
            }
        }

    @pytest.fixture
    def matrix_hub(self, bridge_config, mock_event_bus):
        """Create Matrix bridge hub instance."""
        return MatrixBridgeHub(bridge_config, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_matrix_hub_initialization(self, matrix_hub):
        """Test Matrix bridge hub initialization."""
        assert matrix_hub.platform == "matrix_hub"
        assert matrix_hub.homeserver_url == 'https://matrix.example.com'
        assert matrix_hub.access_token == 'test_token_123'
        assert matrix_hub.user_id == '@testuser:example.com'
        assert matrix_hub.device_id == 'TEST_DEVICE'

        # Check managers are initialized
        assert isinstance(matrix_hub.auth_manager, MatrixAuthManager)
        assert isinstance(matrix_hub.bridge_manager, BridgeManager)

    @pytest.mark.asyncio
    async def test_authentication_success(self, matrix_hub):
        """Test successful Matrix authentication."""
        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock) as mock_auth_init, \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock) as mock_bridge_init:

            await matrix_hub.authenticate()

            mock_auth_init.assert_called_once()
            mock_bridge_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_failure_no_token(self, bridge_config, mock_event_bus):
        """Test authentication failure with missing token."""
        bridge_config['access_token'] = None
        matrix_hub = MatrixBridgeHub(bridge_config, event_bus=mock_event_bus)

        with pytest.raises(Exception):  # Should raise AuthenticationError
            await matrix_hub.authenticate()

    @pytest.mark.asyncio
    async def test_start_real_time_ingestion(self, matrix_hub):
        """Test starting real-time ingestion."""
        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub, '_start_enabled_bridges', new_callable=AsyncMock) as mock_start_bridges:

            await matrix_hub.authenticate()
            await matrix_hub.start_real_time_ingestion()

            # Check tasks are created
            assert matrix_hub._processor_task is not None
            assert matrix_hub._sync_task is not None

            mock_start_bridges.assert_called_once()

            # Cleanup
            await matrix_hub.stop_real_time_ingestion()

    @pytest.mark.asyncio
    async def test_stop_real_time_ingestion(self, matrix_hub):
        """Test stopping real-time ingestion."""
        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'cleanup', new_callable=AsyncMock) as mock_bridge_cleanup, \
                patch.object(matrix_hub.auth_manager, 'cleanup', new_callable=AsyncMock) as mock_auth_cleanup, \
                patch.object(matrix_hub, '_start_enabled_bridges', new_callable=AsyncMock):

            await matrix_hub.authenticate()
            await matrix_hub.start_real_time_ingestion()
            await matrix_hub.stop_real_time_ingestion()

            # Check cleanup was called
            mock_bridge_cleanup.assert_called_once()
            mock_auth_cleanup.assert_called_once()

            # Check tasks are cleaned up
            assert matrix_hub._processor_task is None
            assert matrix_hub._sync_task is None

    @pytest.mark.asyncio
    async def test_message_processing(self, matrix_hub):
        """Test Matrix message processing."""
        # Mock Matrix event
        matrix_event = {
            'type': 'm.room.message',
            'event_id': '$test_event_123',
            'sender': '@whatsapp_user:example.com',
            'room_id': '!test_room:example.com',
            'origin_server_ts': int(datetime.now(timezone.utc).timestamp() * 1000),
            'content': {
                'msgtype': 'm.text',
                'body': 'Hello from WhatsApp!'
            }
        }

        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock):

            await matrix_hub.authenticate()

            # Process message
            await matrix_hub._process_matrix_message({
                'room_id': matrix_event['room_id'],
                'event': matrix_event,
                'timestamp': datetime.now(timezone.utc)
            })

            # Check event was published
            matrix_hub.event_bus.publish.assert_called_once()
            call_args = matrix_hub.event_bus.publish.call_args

            assert call_args[0][0] == 'messages.raw'
            event = call_args[0][1]
            assert event.type == EventType.MESSAGE_RECEIVED
            # Determined from sender
            assert event.data['platform'] == 'whatsapp'
            assert 'Hello from WhatsApp!' in str(event.data['message'])

    @pytest.mark.asyncio
    async def test_platform_determination(self, matrix_hub):
        """Test platform determination from Matrix messages."""
        # WhatsApp message
        platform = matrix_hub._determine_message_platform(
            '@whatsapp_user:example.com', '!room:example.com')
        assert platform == 'whatsapp'

        # Instagram message
        platform = matrix_hub._determine_message_platform(
            '@instagram_user:example.com', '!room:example.com')
        assert platform == 'instagram'

        # Facebook message
        platform = matrix_hub._determine_message_platform(
            '@facebook_user:example.com', '!room:example.com')
        assert platform == 'facebook'

        # Generic Matrix message
        platform = matrix_hub._determine_message_platform(
            '@regular_user:example.com', '!room:example.com')
        assert platform == 'matrix'

    @pytest.mark.asyncio
    async def test_bridge_auth_start(self, matrix_hub):
        """Test starting bridge authentication."""
        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.auth_manager, 'start_bridge_auth', new_callable=AsyncMock) as mock_start_auth:

            # Mock auth session response
            mock_auth_session = Mock()
            mock_auth_session.session_id = 'test_session_123'
            mock_auth_session.auth_method = AuthMethod.QR_CODE
            mock_auth_session.status = 'qr_ready'
            mock_auth_session.qr_data = Mock()
            mock_auth_session.qr_data.qr_code = 'base64_qr_code_data'
            mock_auth_session.metadata = {}

            mock_start_auth.return_value = mock_auth_session

            await matrix_hub.authenticate()

            # Start auth for WhatsApp bridge
            result = await matrix_hub.start_bridge_auth('mautrix-whatsapp')

            assert result['session_id'] == 'test_session_123'
            assert result['auth_method'] == 'qr_code'
            assert result['status'] == 'qr_ready'
            assert result['qr_code'] == 'base64_qr_code_data'
            assert result['oauth_url'] is None

    @pytest.mark.asyncio
    async def test_bridge_status_retrieval(self, matrix_hub):
        """Test retrieving bridge status."""
        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'get_bridge_status', new_callable=AsyncMock) as mock_bridge_status, \
                patch.object(matrix_hub.auth_manager, 'get_bridge_auth_status', new_callable=AsyncMock) as mock_auth_status:

            # Mock status responses
            mock_bridge_status.return_value = {
                'bridge_name': 'mautrix-whatsapp',
                'bridge_type': 'whatsapp',
                'status': 'running',
                'enabled': True,
                'pid': 12345,
                'uptime_seconds': 3600
            }

            mock_auth_status.return_value = {
                'status': 'completed',
                'bridge_name': 'mautrix-whatsapp',
                'session_id': 'test_session_123'
            }

            await matrix_hub.authenticate()

            # Get bridge status
            status = await matrix_hub.get_bridge_status('mautrix-whatsapp')

            assert status['bridge_name'] == 'mautrix-whatsapp'
            assert status['status'] == 'running'
            assert status['auth']['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_webhook_handling(self, matrix_hub):
        """Test Matrix webhook handling."""
        webhook_payload = {
            'events': [
                {
                    'type': 'm.room.message',
                    'event_id': '$webhook_event_123',
                    'sender': '@instagram_user:example.com',
                    'room_id': '!webhook_room:example.com',
                    'origin_server_ts': int(datetime.now(timezone.utc).timestamp() * 1000),
                    'content': {
                        'msgtype': 'm.text',
                        'body': 'Webhook test message'
                    }
                }
            ]
        }

        with patch.object(matrix_hub, '_handle_matrix_event', new_callable=AsyncMock) as mock_handle_event:
            await matrix_hub.handle_webhook(webhook_payload)

            # Check event was handled
            mock_handle_event.assert_called_once()
            call_args = mock_handle_event.call_args[0][0]
            assert call_args['type'] == 'm.room.message'
            assert call_args['sender'] == '@instagram_user:example.com'

    @pytest.mark.asyncio
    async def test_historical_message_fetching(self, matrix_hub):
        """Test fetching historical messages."""
        with patch.object(matrix_hub.auth_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub.bridge_manager, 'initialize', new_callable=AsyncMock), \
                patch.object(matrix_hub, '_get_bridge_rooms', new_callable=AsyncMock) as mock_get_rooms, \
                patch.object(matrix_hub, '_fetch_room_history', new_callable=AsyncMock) as mock_fetch_history:

            # Mock rooms and messages
            mock_get_rooms.return_value = [
                '!room1:example.com', '!room2:example.com']

            mock_message = Mock()
            mock_message.id = 'matrix_test_123'
            mock_message.platform = 'whatsapp'
            mock_message.content = {'text': 'Historical message'}

            mock_fetch_history.return_value = [mock_message]

            await matrix_hub.authenticate()

            # Fetch historical messages
            messages = await matrix_hub.fetch_historical_messages(limit=50)

            assert len(messages) == 2  # One message per room
            mock_get_rooms.assert_called_once()
            assert mock_fetch_history.call_count == 2  # Called for each room


class TestMatrixAuthManager:
    """Test Matrix authentication manager."""

    @pytest.fixture
    def auth_manager(self):
        """Create auth manager instance."""
        return MatrixAuthManager(
            homeserver_url='https://matrix.example.com',
            access_token='test_token_123',
            user_id='@testuser:example.com',
            device_id='TEST_DEVICE'
        )

    @pytest.mark.asyncio
    async def test_auth_manager_initialization(self, auth_manager):
        """Test auth manager initialization."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value.status = 200
            mock_session.get.return_value.__aenter__.return_value.json.return_value = {
                'user_id': '@testuser:example.com'}
            mock_session_class.return_value = mock_session

            await auth_manager.initialize()

            assert auth_manager._matrix_session is not None
            mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_whatsapp_qr_generation(self, auth_manager):
        """Test WhatsApp QR code generation."""
        bridge_config = BridgeConfig(
            bridge_type=BridgeType.WHATSAPP,
            bridge_name='mautrix-whatsapp',
            executable_path='/usr/local/bin/mautrix-whatsapp',
            config_path='./test_config.yaml',
            database_path='./test_db.db',
            homeserver_url='https://matrix.example.com',
            access_token='test_token',
            user_id='@testuser:example.com',
            device_id='TEST_DEVICE',
            auth_method=AuthMethod.QR_CODE
        )

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value.status = 200
            mock_session.get.return_value.__aenter__.return_value.json.return_value = {
                'user_id': '@testuser:example.com'}
            mock_session_class.return_value = mock_session

            await auth_manager.initialize()

            auth_session = await auth_manager.start_bridge_auth(bridge_config)

            assert auth_session.bridge_name == 'mautrix-whatsapp'
            assert auth_session.auth_method == AuthMethod.QR_CODE
            assert auth_session.status == 'qr_ready'
            assert auth_session.qr_data is not None
            assert auth_session.qr_data.qr_code is not None

    @pytest.mark.asyncio
    async def test_instagram_oauth_flow(self, auth_manager):
        """Test Instagram OAuth flow."""
        bridge_config = BridgeConfig(
            bridge_type=BridgeType.INSTAGRAM,
            bridge_name='mautrix-meta',
            executable_path='/usr/local/bin/mautrix-meta',
            config_path='./test_config.yaml',
            database_path='./test_db.db',
            homeserver_url='https://matrix.example.com',
            access_token='test_token',
            user_id='@testuser:example.com',
            device_id='TEST_DEVICE',
            auth_method=AuthMethod.OAUTH
        )

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value.status = 200
            mock_session.get.return_value.__aenter__.return_value.json.return_value = {
                'user_id': '@testuser:example.com'}
            mock_session_class.return_value = mock_session

            await auth_manager.initialize()

            auth_session = await auth_manager.start_bridge_auth(bridge_config)

            assert auth_session.bridge_name == 'mautrix-meta'
            assert auth_session.auth_method == AuthMethod.OAUTH
            assert auth_session.status == 'oauth_ready'
            assert 'oauth_url' in auth_session.metadata
            assert 'facebook.com' in auth_session.metadata['oauth_url']


class TestBridgeManager:
    """Test bridge manager functionality."""

    @pytest.fixture
    def bridge_manager(self):
        """Create bridge manager instance."""
        return BridgeManager()

    @pytest.fixture
    def whatsapp_config(self):
        """WhatsApp bridge configuration."""
        return BridgeConfig(
            bridge_type=BridgeType.WHATSAPP,
            bridge_name='mautrix-whatsapp',
            executable_path='/usr/local/bin/mautrix-whatsapp',
            config_path='./test_bridges/whatsapp/config.yaml',
            database_path='./test_bridges/whatsapp/whatsapp.db',
            homeserver_url='https://matrix.example.com',
            access_token='test_token',
            user_id='@testuser:example.com',
            device_id='TEST_DEVICE'
        )

    @pytest.mark.asyncio
    async def test_bridge_manager_initialization(self, bridge_manager):
        """Test bridge manager initialization."""
        await bridge_manager.initialize()

        assert bridge_manager._monitoring is True
        assert bridge_manager._monitor_task is not None

        await bridge_manager.cleanup()

    @pytest.mark.asyncio
    async def test_add_bridge(self, bridge_manager, whatsapp_config):
        """Test adding a bridge configuration."""
        with patch.object(bridge_manager, '_validate_bridge_config', new_callable=AsyncMock), \
                patch.object(bridge_manager, '_generate_bridge_config', new_callable=AsyncMock):

            await bridge_manager.initialize()

            instance = await bridge_manager.add_bridge(whatsapp_config)

            assert instance.config.bridge_name == 'mautrix-whatsapp'
            assert instance.status == BridgeStatus.STOPPED
            assert 'mautrix-whatsapp' in bridge_manager.bridge_instances

            await bridge_manager.cleanup()

    @pytest.mark.asyncio
    async def test_bridge_status_retrieval(self, bridge_manager, whatsapp_config):
        """Test retrieving bridge status."""
        with patch.object(bridge_manager, '_validate_bridge_config', new_callable=AsyncMock), \
                patch.object(bridge_manager, '_generate_bridge_config', new_callable=AsyncMock):

            await bridge_manager.initialize()
            await bridge_manager.add_bridge(whatsapp_config)

            status = await bridge_manager.get_bridge_status('mautrix-whatsapp')

            assert status['bridge_name'] == 'mautrix-whatsapp'
            assert status['bridge_type'] == 'whatsapp'
            assert status['status'] == 'stopped'
            assert status['enabled'] is True

            await bridge_manager.cleanup()

    @pytest.mark.asyncio
    async def test_bridge_process_management(self, bridge_manager, whatsapp_config):
        """Test bridge process start/stop."""
        with patch.object(bridge_manager, '_validate_bridge_config', new_callable=AsyncMock), \
                patch.object(bridge_manager, '_generate_bridge_config', new_callable=AsyncMock), \
                patch.object(bridge_manager, '_start_bridge_process', new_callable=AsyncMock) as mock_start, \
                patch.object(bridge_manager, '_stop_bridge_process', new_callable=AsyncMock) as mock_stop:

            mock_start.return_value = True
            mock_stop.return_value = True

            await bridge_manager.initialize()
            await bridge_manager.add_bridge(whatsapp_config)

            # Start bridge
            success = await bridge_manager.start_bridge('mautrix-whatsapp')
            assert success is True
            mock_start.assert_called_once()

            # Stop bridge
            success = await bridge_manager.stop_bridge('mautrix-whatsapp')
            assert success is True
            mock_stop.assert_called_once()

            await bridge_manager.cleanup()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
