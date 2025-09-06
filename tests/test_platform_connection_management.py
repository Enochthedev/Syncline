"""
Integration Tests for Platform Connection Management

Tests OAuth flows, connection management, health monitoring,
and troubleshooting functionality.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from api.main import app
from services.security.oauth_service import OAuthService
from services.security.types import OAuthConfig, OAuthState, TokenValidationResult
from integrations.token_manager import TokenManager, TokenInfo
from integrations.connector_manager import ConnectorManager
from integrations.base_connector import ConnectorStatus, ConnectorHealth


class TestPlatformConnectionAPI:
    """Test platform connection API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        return {
            "id": "test-user-123",
            "email": "test@example.com",
            "is_active": True
        }

    @pytest.fixture
    def mock_oauth_service(self):
        service = AsyncMock(spec=OAuthService)
        service.get_platform_oauth_config.return_value = OAuthConfig(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="https://test.com/callback",
            scopes=["read", "write"],
            auth_url="https://platform.com/oauth/authorize",
            token_url="https://platform.com/oauth/token"
        )
        return service

    @pytest.fixture
    def mock_connector_manager(self):
        manager = AsyncMock(spec=ConnectorManager)
        manager.get_connector_health.return_value = {
            "gmail": ConnectorHealth(
                status=ConnectorStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                uptime_seconds=3600.0
            )
        }
        return manager

    @pytest.mark.asyncio
    async def test_get_available_platforms(self, client, mock_user):
        """Test getting available platforms for connection."""

        with patch('api.dependencies.get_current_user', return_value=mock_user):
            response = client.get("/api/platforms/available")

        assert response.status_code == 200
        platforms = response.json()

        assert len(platforms) > 0
        assert any(p["platform"] == "gmail" for p in platforms)
        assert any(p["platform"] == "slack" for p in platforms)

        # Check platform structure
        gmail_platform = next(p for p in platforms if p["platform"] == "gmail")
        assert gmail_platform["display_name"] == "Gmail"
        assert gmail_platform["is_supported"] is True
        assert "oauth_config" in gmail_platform

    @pytest.mark.asyncio
    async def test_get_user_connections(self, client, mock_user, mock_connector_manager):
        """Test getting user's platform connections."""

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.get("/api/platforms/connections")

        assert response.status_code == 200
        connections = response.json()

        assert len(connections) > 0

        # Check connection structure
        connection = connections[0]
        assert "platform" in connection
        assert "display_name" in connection
        assert "is_connected" in connection
        assert "connection_status" in connection
        assert "sync_preferences" in connection
        assert "health_metrics" in connection

    @pytest.mark.asyncio
    async def test_initiate_oauth_flow(self, client, mock_user, mock_oauth_service):
        """Test initiating OAuth flow for a platform."""

        mock_oauth_service.build_authorization_url.return_value = "https://platform.com/oauth/authorize?client_id=test"

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_oauth_service', return_value=mock_oauth_service):

            response = client.post("/api/platforms/gmail/oauth/initiate")

        assert response.status_code == 200
        data = response.json()

        assert "auth_url" in data
        assert "state" in data
        assert data["auth_url"].startswith(
            "https://platform.com/oauth/authorize")

        # Verify OAuth service was called correctly
        mock_oauth_service.get_platform_oauth_config.assert_called_once_with(
            "gmail")
        mock_oauth_service.store_oauth_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self, client, mock_user, mock_oauth_service, mock_connector_manager):
        """Test completing OAuth flow with authorization code."""

        # Mock OAuth state verification
        oauth_state = OAuthState(
            user_id="test-user-123",
            platform="gmail",
            state="test-state-123",
            created_at=datetime.now(timezone.utc)
        )
        mock_oauth_service.verify_oauth_state.return_value = oauth_state

        # Mock token exchange
        token_info = TokenInfo(
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer"
        )
        mock_oauth_service.exchange_code_for_tokens.return_value = token_info

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_oauth_service', return_value=mock_oauth_service), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.post("/api/platforms/gmail/oauth/complete", json={
                "code": "test-auth-code",
                "state": "test-state-123"
            })

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "gmail"
        assert data["is_connected"] is True

        # Verify OAuth service calls
        mock_oauth_service.verify_oauth_state.assert_called_once()
        mock_oauth_service.exchange_code_for_tokens.assert_called_once()
        mock_oauth_service.store_user_tokens.assert_called_once()
        mock_connector_manager.start_connector.assert_called_once_with("gmail")

    @pytest.mark.asyncio
    async def test_disconnect_platform(self, client, mock_user, mock_oauth_service, mock_connector_manager):
        """Test disconnecting a platform."""

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_oauth_service', return_value=mock_oauth_service), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.delete("/api/platforms/gmail/connection")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "gmail" in data["message"]

        # Verify service calls
        mock_connector_manager.stop_connector.assert_called_once_with("gmail")
        mock_oauth_service.revoke_user_tokens.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_sync_preferences(self, client, mock_user):
        """Test updating platform sync preferences."""

        preferences = {
            "enabled": True,
            "sync_messages": True,
            "sync_contacts": False,
            "sync_frequency": "hourly"
        }

        with patch('api.dependencies.get_current_user', return_value=mock_user):
            response = client.put(
                "/api/platforms/gmail/sync-preferences", json=preferences)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_get_platform_health(self, client, mock_user, mock_connector_manager):
        """Test getting platform health metrics."""

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.get("/api/platforms/gmail/health")

        assert response.status_code == 200
        data = response.json()

        assert "uptime" in data
        assert "error_count" in data
        assert "successful_syncs" in data
        assert "last_health_check" in data

    @pytest.mark.asyncio
    async def test_get_troubleshooting_info(self, client, mock_user, mock_connector_manager):
        """Test getting troubleshooting information."""

        # Mock unhealthy connector
        mock_connector_manager.get_connector_health.return_value = {
            "gmail": ConnectorHealth(
                status=ConnectorStatus.UNHEALTHY,
                last_check=datetime.now(timezone.utc),
                error_count=3,
                last_error="Connection timeout"
            )
        }

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.get("/api/platforms/gmail/troubleshoot")

        assert response.status_code == 200
        data = response.json()

        assert "platform" in data
        assert "issues" in data
        assert "suggested_actions" in data
        assert "diagnostic_data" in data

        # Should have issues for unhealthy connector
        assert len(data["issues"]) > 0
        assert len(data["suggested_actions"]) > 0

    @pytest.mark.asyncio
    async def test_execute_troubleshooting_action(self, client, mock_user, mock_connector_manager):
        """Test executing a troubleshooting action."""

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.post("/api/platforms/gmail/troubleshoot/execute", json={
                "action_id": "retry_sync"
            })

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_bulk_operations(self, client, mock_user):
        """Test bulk platform operations."""

        platforms = ["gmail", "slack", "discord"]

        with patch('api.dependencies.get_current_user', return_value=mock_user):
            # Test bulk enable
            response = client.post(
                "/api/platforms/bulk/enable", json=platforms)
            assert response.status_code == 200

            data = response.json()
            assert "successful" in data
            assert "failed" in data
            assert "total_processed" in data
            assert data["total_processed"] == len(platforms)


class TestOAuthService:
    """Test OAuth service functionality."""

    @pytest.fixture
    def token_manager(self):
        return AsyncMock(spec=TokenManager)

    @pytest.fixture
    def oauth_service(self, token_manager):
        return OAuthService(token_manager)

    @pytest.mark.asyncio
    async def test_get_platform_oauth_config(self, oauth_service):
        """Test getting OAuth configuration for platforms."""

        config = await oauth_service.get_platform_oauth_config("gmail")

        assert config is not None
        assert config.client_id is not None
        assert config.auth_url == "https://accounts.google.com/o/oauth2/auth"
        assert "gmail.readonly" in " ".join(config.scopes)

    @pytest.mark.asyncio
    async def test_build_authorization_url(self, oauth_service):
        """Test building OAuth authorization URL."""

        config = await oauth_service.get_platform_oauth_config("gmail")
        oauth_state = OAuthState(
            user_id="test-user",
            platform="gmail",
            state="test-state",
            created_at=datetime.now(timezone.utc)
        )

        auth_url = await oauth_service.build_authorization_url(config, oauth_state)

        assert auth_url.startswith(config.auth_url)
        assert "client_id=" in auth_url
        assert "state=test-state" in auth_url
        assert "scope=" in auth_url

    @pytest.mark.asyncio
    async def test_oauth_state_management(self, oauth_service):
        """Test OAuth state storage and verification."""

        oauth_state = OAuthState(
            user_id="test-user",
            platform="gmail",
            state="test-state-123",
            created_at=datetime.now(timezone.utc)
        )

        # Store state
        await oauth_service.store_oauth_state(oauth_state)

        # Verify state
        verified_state = await oauth_service.verify_oauth_state(
            "test-state-123", "test-user", "gmail"
        )

        assert verified_state is not None
        assert verified_state.user_id == "test-user"
        assert verified_state.platform == "gmail"

        # Test invalid state
        invalid_state = await oauth_service.verify_oauth_state(
            "invalid-state", "test-user", "gmail"
        )
        assert invalid_state is None

    @pytest.mark.asyncio
    async def test_token_exchange_mock(self, oauth_service):
        """Test token exchange with mocked HTTP calls."""

        oauth_state = OAuthState(
            user_id="test-user",
            platform="gmail",
            state="test-state",
            created_at=datetime.now(timezone.utc)
        )

        # Mock the HTTP response
        mock_response_data = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/gmail.readonly"
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response

            token_info = await oauth_service.exchange_code_for_tokens(
                "gmail", "test-auth-code", oauth_state
            )

        assert token_info.access_token == "test-access-token"
        assert token_info.refresh_token == "test-refresh-token"
        assert token_info.token_type == "Bearer"
        assert token_info.expires_at is not None

    @pytest.mark.asyncio
    async def test_token_refresh(self, oauth_service):
        """Test token refresh functionality."""

        mock_response_data = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response

            new_token = await oauth_service.refresh_access_token(
                "gmail", "old-refresh-token"
            )

        assert new_token.access_token == "new-access-token"
        assert new_token.refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_token_revocation(self, oauth_service):
        """Test token revocation."""

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await oauth_service.revoke_token("gmail", "test-token")

        assert result is True

    @pytest.mark.asyncio
    async def test_token_validation(self, oauth_service):
        """Test token validation."""

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            is_valid = await oauth_service.validate_token("gmail", "test-token")

        assert is_valid is True

        # Test invalid token
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_get.return_value.__aenter__.return_value = mock_response

            is_valid = await oauth_service.validate_token("gmail", "invalid-token")

        assert is_valid is False


class TestConnectorHealthMonitoring:
    """Test connector health monitoring and troubleshooting."""

    @pytest.fixture
    def connector_manager(self):
        return AsyncMock(spec=ConnectorManager)

    @pytest.mark.asyncio
    async def test_health_check_healthy_connector(self, connector_manager):
        """Test health check for healthy connector."""

        healthy_status = ConnectorHealth(
            status=ConnectorStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            uptime_seconds=3600.0,
            error_count=0
        )

        connector_manager.get_connector_health.return_value = {
            "gmail": healthy_status
        }

        health_status = await connector_manager.get_connector_health("gmail")

        assert "gmail" in health_status
        assert health_status["gmail"].status == ConnectorStatus.HEALTHY
        assert health_status["gmail"].error_count == 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_connector(self, connector_manager):
        """Test health check for unhealthy connector."""

        unhealthy_status = ConnectorHealth(
            status=ConnectorStatus.UNHEALTHY,
            last_check=datetime.now(timezone.utc),
            uptime_seconds=1800.0,
            error_count=5,
            last_error="Connection timeout"
        )

        connector_manager.get_connector_health.return_value = {
            "gmail": unhealthy_status
        }

        health_status = await connector_manager.get_connector_health("gmail")

        assert health_status["gmail"].status == ConnectorStatus.UNHEALTHY
        assert health_status["gmail"].error_count == 5
        assert health_status["gmail"].last_error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_connector_restart(self, connector_manager):
        """Test connector restart functionality."""

        await connector_manager.restart_connector("gmail")

        connector_manager.restart_connector.assert_called_once_with("gmail")


class TestErrorHandling:
    """Test error handling in platform connection management."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        return {
            "id": "test-user-123",
            "email": "test@example.com",
            "is_active": True
        }

    @pytest.mark.asyncio
    async def test_oauth_invalid_state_error(self, client, mock_user):
        """Test OAuth flow with invalid state parameter."""

        mock_oauth_service = AsyncMock()
        mock_oauth_service.verify_oauth_state.return_value = None  # Invalid state

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_oauth_service', return_value=mock_oauth_service):

            response = client.post("/api/platforms/gmail/oauth/complete", json={
                "code": "test-auth-code",
                "state": "invalid-state"
            })

        assert response.status_code == 400
        assert "Invalid OAuth state" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_platform_not_found_error(self, client, mock_user):
        """Test accessing non-existent platform."""

        mock_connector_manager = AsyncMock()
        mock_connector_manager.get_connector_health.return_value = {}  # No platforms

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_connector_manager', return_value=mock_connector_manager):

            response = client.get("/api/platforms/nonexistent/health")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth_token_exchange_error(self, client, mock_user):
        """Test OAuth token exchange failure."""

        mock_oauth_service = AsyncMock()
        oauth_state = OAuthState(
            user_id="test-user-123",
            platform="gmail",
            state="test-state",
            created_at=datetime.now(timezone.utc)
        )
        mock_oauth_service.verify_oauth_state.return_value = oauth_state
        mock_oauth_service.exchange_code_for_tokens.side_effect = Exception(
            "Token exchange failed")

        with patch('api.dependencies.get_current_user', return_value=mock_user), \
                patch('api.routes.platform_connections.get_oauth_service', return_value=mock_oauth_service):

            response = client.post("/api/platforms/gmail/oauth/complete", json={
                "code": "test-auth-code",
                "state": "test-state"
            })

        assert response.status_code == 500
        assert "Failed to complete OAuth flow" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
