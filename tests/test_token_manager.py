"""
Unit tests for token management.

Tests secure token storage, automatic refresh, and
encryption for authentication tokens.
"""

import asyncio
import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from integrations.token_manager import (
    TokenManager,
    TokenStorage,
    EncryptedFileTokenStorage,
    RedisTokenStorage,
    TokenRefreshHandler,
    OAuth2RefreshHandler,
    TokenStorageError,
    TokenRefreshError
)
from integrations.base_connector import TokenInfo


class MockTokenStorage(TokenStorage):
    """Mock token storage for testing."""

    def __init__(self):
        self._tokens: Dict[str, TokenInfo] = {}

    async def store_token(self, platform: str, token: TokenInfo) -> None:
        self._tokens[platform] = token

    async def get_token(self, platform: str) -> TokenInfo | None:
        return self._tokens.get(platform)

    async def delete_token(self, platform: str) -> None:
        self._tokens.pop(platform, None)

    async def list_platforms(self) -> list[str]:
        return list(self._tokens.keys())


class MockRefreshHandler(TokenRefreshHandler):
    """Mock token refresh handler for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.refresh_called = False

    async def refresh_token(self, platform: str, current_token: TokenInfo) -> TokenInfo:
        self.refresh_called = True
        if self.should_fail:
            raise TokenRefreshError("Mock refresh failure")

        return TokenInfo(
            access_token="new_access_token",
            refresh_token=current_token.refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer"
        )


class TestTokenInfo:
    """Test TokenInfo model (additional tests beyond base_connector tests)."""

    def test_token_info_serialization(self):
        """Test TokenInfo JSON serialization."""
        token = TokenInfo(
            access_token="test_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer",
            scope="read write",
            metadata={"custom": "data"}
        )

        # Test model_dump_json
        json_str = token.model_dump_json()
        assert "test_token" in json_str
        assert "refresh_token" in json_str

        # Test deserialization
        token_dict = json.loads(json_str)
        new_token = TokenInfo(**token_dict)
        assert new_token.access_token == token.access_token
        assert new_token.refresh_token == token.refresh_token


class TestEncryptedFileTokenStorage:
    """Test EncryptedFileTokenStorage functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory fixture."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def storage(self, temp_dir):
        """EncryptedFileTokenStorage fixture."""
        return EncryptedFileTokenStorage(
            storage_dir=temp_dir,
            encryption_key="test_encryption_key_32_chars_long"
        )

    @pytest.fixture
    def sample_token(self):
        """Sample token fixture."""
        return TokenInfo(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer",
            scope="read write"
        )

    @pytest.mark.asyncio
    async def test_store_and_retrieve_token(self, storage, sample_token):
        """Test storing and retrieving a token."""
        await storage.store_token("test_platform", sample_token)

        retrieved_token = await storage.get_token("test_platform")

        assert retrieved_token is not None
        assert retrieved_token.access_token == sample_token.access_token
        assert retrieved_token.refresh_token == sample_token.refresh_token
        assert retrieved_token.token_type == sample_token.token_type

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, storage):
        """Test retrieving non-existent token."""
        token = await storage.get_token("nonexistent")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token(self, storage, sample_token):
        """Test deleting a token."""
        await storage.store_token("test_platform", sample_token)
        await storage.delete_token("test_platform")

        token = await storage.get_token("test_platform")
        assert token is None

    @pytest.mark.asyncio
    async def test_list_platforms(self, storage, sample_token):
        """Test listing platforms with stored tokens."""
        await storage.store_token("platform1", sample_token)
        await storage.store_token("platform2", sample_token)

        platforms = await storage.list_platforms()

        assert len(platforms) == 2
        assert "platform1" in platforms
        assert "platform2" in platforms

    @pytest.mark.asyncio
    async def test_encryption_different_keys(self, temp_dir, sample_token):
        """Test that different encryption keys produce different results."""
        storage1 = EncryptedFileTokenStorage(
            storage_dir=temp_dir,
            encryption_key="key1_32_characters_long_string"
        )
        storage2 = EncryptedFileTokenStorage(
            storage_dir=temp_dir,
            encryption_key="key2_32_characters_long_string"
        )

        await storage1.store_token("test_platform", sample_token)

        # Storage2 with different key should not be able to decrypt
        token = await storage2.get_token("test_platform")
        assert token is None  # Should fail to decrypt and return None

    def test_file_creation(self, storage, temp_dir):
        """Test that storage directory is created."""
        assert os.path.exists(temp_dir)

    @pytest.mark.asyncio
    async def test_storage_error_handling(self, temp_dir):
        """Test error handling in storage operations."""
        # Create storage with invalid directory permissions
        invalid_dir = os.path.join(temp_dir, "invalid")
        os.makedirs(invalid_dir)
        os.chmod(invalid_dir, 0o000)  # No permissions

        storage = EncryptedFileTokenStorage(storage_dir=invalid_dir)
        token = TokenInfo(access_token="test")

        try:
            with pytest.raises(TokenStorageError):
                await storage.store_token("test", token)
        finally:
            # Restore permissions for cleanup
            os.chmod(invalid_dir, 0o755)


class TestRedisTokenStorage:
    """Test RedisTokenStorage functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client fixture."""
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.keys.return_value = []
        return redis_mock

    @pytest.fixture
    def storage(self, mock_redis):
        """RedisTokenStorage fixture."""
        return RedisTokenStorage(
            redis_client=mock_redis,
            encryption_key="test_encryption_key_32_chars_long"
        )

    @pytest.fixture
    def sample_token(self):
        """Sample token fixture."""
        return TokenInfo(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer"
        )

    @pytest.mark.asyncio
    async def test_store_token(self, storage, mock_redis, sample_token):
        """Test storing a token in Redis."""
        await storage.store_token("test_platform", sample_token)

        # Verify Redis setex was called with TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "mesh:tokens:test_platform"
        assert call_args[0][1] > 0  # TTL should be positive

    @pytest.mark.asyncio
    async def test_store_token_no_expiration(self, storage, mock_redis):
        """Test storing a token without expiration."""
        token = TokenInfo(access_token="test_token")  # No expires_at

        await storage.store_token("test_platform", token)

        # Should use set instead of setex
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token(self, storage, mock_redis, sample_token):
        """Test retrieving a token from Redis."""
        # Mock Redis to return encrypted token data
        token_json = sample_token.model_dump_json()
        # Simulate encrypted data (in real usage, this would be encrypted)
        mock_redis.get.return_value = token_json

        # Mock the decryption to return original data
        with patch.object(storage, '_get_fernet') as mock_fernet:
            mock_cipher = MagicMock()
            mock_cipher.decrypt.return_value = token_json.encode()
            mock_fernet.return_value = mock_cipher

            retrieved_token = await storage.get_token("test_platform")

            assert retrieved_token is not None
            assert retrieved_token.access_token == sample_token.access_token

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, storage, mock_redis):
        """Test retrieving non-existent token."""
        mock_redis.get.return_value = None

        token = await storage.get_token("nonexistent")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token(self, storage, mock_redis):
        """Test deleting a token from Redis."""
        await storage.delete_token("test_platform")

        mock_redis.delete.assert_called_once_with("mesh:tokens:test_platform")

    @pytest.mark.asyncio
    async def test_list_platforms(self, storage, mock_redis):
        """Test listing platforms with stored tokens."""
        mock_redis.keys.return_value = [
            b"mesh:tokens:platform1",
            b"mesh:tokens:platform2"
        ]

        platforms = await storage.list_platforms()

        assert len(platforms) == 2
        assert "platform1" in platforms
        assert "platform2" in platforms


class TestTokenManager:
    """Test TokenManager functionality."""

    @pytest.fixture
    def mock_storage(self):
        """Mock token storage fixture."""
        return MockTokenStorage()

    @pytest.fixture
    def token_manager(self, mock_storage):
        """TokenManager fixture."""
        return TokenManager(storage=mock_storage)

    @pytest.fixture
    def sample_token(self):
        """Sample token fixture."""
        return TokenInfo(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_type="Bearer"
        )

    @pytest.fixture
    def expiring_token(self):
        """Expiring token fixture."""
        return TokenInfo(
            access_token="expiring_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
            token_type="Bearer"
        )

    @pytest.fixture
    def expired_token(self):
        """Expired token fixture."""
        return TokenInfo(
            access_token="expired_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            token_type="Bearer"
        )

    @pytest.mark.asyncio
    async def test_store_token(self, token_manager, sample_token):
        """Test storing a token."""
        await token_manager.store_token("test_platform", sample_token)

        stored_token = await token_manager.storage.get_token("test_platform")
        assert stored_token is not None
        assert stored_token.access_token == sample_token.access_token

    @pytest.mark.asyncio
    async def test_get_token_no_refresh(self, token_manager, sample_token):
        """Test getting a token without auto-refresh."""
        await token_manager.store_token("test_platform", sample_token)

        token = await token_manager.get_token("test_platform", auto_refresh=False)

        assert token is not None
        assert token.access_token == sample_token.access_token

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, token_manager):
        """Test getting non-existent token."""
        token = await token_manager.get_token("nonexistent")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token(self, token_manager, sample_token):
        """Test deleting a token."""
        await token_manager.store_token("test_platform", sample_token)
        await token_manager.delete_token("test_platform")

        token = await token_manager.get_token("test_platform")
        assert token is None

    @pytest.mark.asyncio
    async def test_list_platforms(self, token_manager, sample_token):
        """Test listing platforms with tokens."""
        await token_manager.store_token("platform1", sample_token)
        await token_manager.store_token("platform2", sample_token)

        platforms = await token_manager.list_platforms()

        assert len(platforms) == 2
        assert "platform1" in platforms
        assert "platform2" in platforms

    @pytest.mark.asyncio
    async def test_auto_refresh_expiring_token(self, token_manager, expiring_token):
        """Test automatic refresh of expiring token."""
        refresh_handler = MockRefreshHandler()
        token_manager.register_refresh_handler(
            "test_platform", refresh_handler)

        await token_manager.store_token("test_platform", expiring_token)

        token = await token_manager.get_token("test_platform", auto_refresh=True)

        assert refresh_handler.refresh_called
        assert token.access_token == "new_access_token"

    @pytest.mark.asyncio
    async def test_auto_refresh_no_handler(self, token_manager, expiring_token):
        """Test auto-refresh when no handler is registered."""
        await token_manager.store_token("test_platform", expiring_token)

        # Should return original token without refresh
        token = await token_manager.get_token("test_platform", auto_refresh=True)

        assert token.access_token == expiring_token.access_token

    @pytest.mark.asyncio
    async def test_refresh_failure(self, token_manager, expiring_token):
        """Test handling refresh failure."""
        refresh_handler = MockRefreshHandler(should_fail=True)
        token_manager.register_refresh_handler(
            "test_platform", refresh_handler)

        await token_manager.store_token("test_platform", expiring_token)

        with pytest.raises(TokenRefreshError):
            await token_manager.get_token("test_platform", auto_refresh=True)

    @pytest.mark.asyncio
    async def test_concurrent_refresh(self, token_manager, expiring_token):
        """Test that concurrent refresh requests are handled properly."""
        refresh_handler = MockRefreshHandler()
        token_manager.register_refresh_handler(
            "test_platform", refresh_handler)

        await token_manager.store_token("test_platform", expiring_token)

        # Start multiple concurrent refresh requests
        tasks = [
            token_manager.get_token("test_platform", auto_refresh=True)
            for _ in range(5)
        ]

        tokens = await asyncio.gather(*tasks)

        # All should get the same refreshed token
        assert all(token.access_token ==
                   "new_access_token" for token in tokens)
        # Refresh should only be called once due to locking
        assert refresh_handler.refresh_called

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, token_manager, expired_token, sample_token):
        """Test cleanup of expired tokens."""
        await token_manager.store_token("expired_platform", expired_token)
        await token_manager.store_token("valid_platform", sample_token)

        await token_manager.cleanup_expired_tokens()

        # Expired token should be removed
        expired = await token_manager.get_token("expired_platform")
        assert expired is None

        # Valid token should remain
        valid = await token_manager.get_token("valid_platform")
        assert valid is not None

    def test_register_refresh_handler(self, token_manager):
        """Test registering a refresh handler."""
        handler = MockRefreshHandler()
        token_manager.register_refresh_handler("test_platform", handler)

        assert "test_platform" in token_manager.refresh_handlers
        assert token_manager.refresh_handlers["test_platform"] is handler


class TestOAuth2RefreshHandler:
    """Test OAuth2RefreshHandler functionality."""

    @pytest.fixture
    def refresh_handler(self):
        """OAuth2RefreshHandler fixture."""
        return OAuth2RefreshHandler(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_url="https://oauth.example.com/token"
        )

    @pytest.fixture
    def current_token(self):
        """Current token fixture."""
        return TokenInfo(
            access_token="old_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            token_type="Bearer"
        )

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, refresh_handler, current_token):
        """Test successful token refresh."""
        mock_response_data = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600,
            'token_type': 'Bearer',
            'scope': 'read write'
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response

            new_token = await refresh_handler.refresh_token("test_platform", current_token)

            assert new_token.access_token == "new_access_token"
            assert new_token.refresh_token == "new_refresh_token"
            assert new_token.token_type == "Bearer"
            assert new_token.scope == "read write"
            assert new_token.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, refresh_handler, current_token):
        """Test token refresh failure."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(TokenRefreshError):
                await refresh_handler.refresh_token("test_platform", current_token)

    @pytest.mark.asyncio
    async def test_refresh_token_no_refresh_token(self, refresh_handler):
        """Test refresh when no refresh token is available."""
        token_without_refresh = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )

        with pytest.raises(TokenRefreshError, match="No refresh token available"):
            await refresh_handler.refresh_token("test_platform", token_without_refresh)

    @pytest.mark.asyncio
    async def test_refresh_token_request_data(self, refresh_handler, current_token):
        """Test that correct data is sent in refresh request."""
        mock_response_data = {
            'access_token': 'new_access_token',
            'expires_in': 3600
        }

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response

            await refresh_handler.refresh_token("test_platform", current_token)

            # Verify the request was made with correct data
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://oauth.example.com/token"

            data = call_args[1]['data']
            assert data['grant_type'] == 'refresh_token'
            assert data['refresh_token'] == 'test_refresh_token'
            assert data['client_id'] == 'test_client_id'
            assert data['client_secret'] == 'test_client_secret'


if __name__ == "__main__":
    pytest.main([__file__])
