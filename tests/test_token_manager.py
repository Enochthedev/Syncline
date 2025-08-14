"""
Unit tests for token management system.

Tests token storage, encryption, refresh handlers,
and token manager functionality.
"""

import asyncio
import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet

from integrations.base_connector import TokenInfo
from integrations.token_manager import (
    TokenManager,
    EncryptedFileTokenStorage,
    RedisTokenStorage,
    OAuth2RefreshHandler,
    TokenStorageError,
    TokenRefreshError
)


class TestTokenInfo:
    """Test TokenInfo model (additional tests)."""

    def test_token_serialization(self):
        """Test token serialization to JSON."""
        token = TokenInfo(
            access_token="test_token",
            refresh_token="refresh_token",
            expires_at=datetime(2024, 1, 1, 12, 0, 0),
            token_type="Bearer",
            scope="read write",
            metadata={"custom": "data"}
        )

        json_data = token.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["access_token"] == "test_token"
        assert parsed["refresh_token"] == "refresh_token"
        assert parsed["token_type"] == "Bearer"
        assert parsed["scope"] == "read write"
        assert parsed["metadata"]["custom"] == "data"

    def test_token_deserialization(self):
        """Test token deserialization from dict."""
        token_dict = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "expires_at": "2024-01-01T12:00:00",
            "token_type": "Bearer",
            "scope": "read write",
            "metadata": {"custom": "data"}
        }

        token = TokenInfo(**token_dict)

        assert token.access_token == "test_token"
        assert token.refresh_token == "refresh_token"
        assert token.token_type == "Bearer"
        assert token.scope == "read write"
        assert token.metadata["custom"] == "data"


class TestEncryptedFileTokenStorage:
    """Test EncryptedFileTokenStorage functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory fixture."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def storage(self, temp_dir):
        """File token storage fixture."""
        return EncryptedFileTokenStorage(
            storage_dir=temp_dir,
            encryption_key="test_encryption_key_32_bytes_long"
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
        platform = "test_platform"

        # Store token
        await storage.store_token(platform, sample_token)

        # Retrieve token
        retrieved_token = await storage.get_token(platform)

        assert retrieved_token is not None
        assert retrieved_token.access_token == sample_token.access_token
        assert retrieved_token.refresh_token == sample_token.refresh_token
        assert retrieved_token.token_type == sample_token.token_type
        assert retrieved_token.scope == sample_token.scope

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, storage):
        """Test retrieving non-existent token."""
        token = await storage.get_token("nonexistent_platform")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token(self, storage, sample_token):
        """Test deleting a token."""
        platform = "test_platform"

        # Store token
        await storage.store_token(platform, sample_token)

        # Verify it exists
        token = await storage.get_token(platform)
        assert token is not None

        # Delete token
        await storage.delete_token(platform)

        # Verify it's gone
        token = await storage.get_token(platform)
        assert token is None

    @pytest.mark.asyncio
    async def test_list_platforms(self, storage, sample_token):
        """Test listing platforms with stored tokens."""
        platforms = ["platform1", "platform2", "platform3"]

        # Store tokens for multiple platforms
        for platform in platforms:
            await storage.store_token(platform, sample_token)

        # List platforms
        stored_platforms = await storage.list_platforms()

        assert set(stored_platforms) == set(platforms)

    @pytest.mark.asyncio
    async def test_encryption_integrity(self, storage, sample_token, temp_dir):
        """Test that tokens are actually encrypted on disk."""
        platform = "test_platform"

        # Store token
        await storage.store_token(platform, sample_token)

        # Read raw file content
        token_file = os.path.join(temp_dir, f"{platform}.token")
        with open(token_file, 'rb') as f:
            encrypted_data = f.read()

        # Should not contain plaintext token
        assert b"test_access_token" not in encrypted_data
        assert b"test_refresh_token" not in encrypted_data

    @pytest.mark.asyncio
    async def test_storage_error_handling(self, temp_dir):
        """Test storage error handling."""
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
        redis_mock.set = AsyncMock()
        redis_mock.setex = AsyncMock()
        redis_mock.get = AsyncMock()
        redis_mock.delete = AsyncMock()
        redis_mock.keys = AsyncMock()
        return redis_mock

    @pytest.fixture
    def storage(self, mock_redis):
        """Redis token storage fixture."""
        return RedisTokenStorage(
            redis_client=mock_redis,
            encryption_key="test_encryption_key_32_bytes_long"
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
    async def test_store_token_with_ttl(self, storage, mock_redis, sample_token):
        """Test storing token with TTL."""
        platform = "test_platform"

        await storage.store_token(platform, sample_token)

        # Should call setex with TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "mesh:tokens:test_platform"  # key
        assert call_args[0][1] > 0  # ttl
        assert call_args[0][2] is not None  # encrypted data

    @pytest.mark.asyncio
    async def test_store_token_no_expiration(self, storage, mock_redis):
        """Test storing token without expiration."""
        platform = "test_platform"
        token = TokenInfo(access_token="test_token")  # No expiration

        await storage.store_token(platform, token)

        # Should call set without TTL
        mock_redis.set.assert_called_once()
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_token(self, storage, mock_redis, sample_token):
        """Test retrieving token from Redis."""
        platform = "test_platform"

        # Mock Redis response with encrypted data
        fernet = storage._get_fernet()
        token_json = sample_token.model_dump_json()
        encrypted_data = fernet.encrypt(token_json.encode()).decode()
        mock_redis.get.return_value = encrypted_data

        retrieved_token = await storage.get_token(platform)

        assert retrieved_token is not None
        assert retrieved_token.access_token == sample_token.access_token
        mock_redis.get.assert_called_once_with("mesh:tokens:test_platform")

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, storage, mock_redis):
        """Test retrieving non-existent token."""
        mock_redis.get.return_value = None

        token = await storage.get_token("nonexistent")

        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token(self, storage, mock_redis):
        """Test deleting token from Redis."""
        platform = "test_platform"

        await storage.delete_token(platform)

        mock_redis.delete.assert_called_once_with("mesh:tokens:test_platform")

    @pytest.mark.asyncio
    async def test_list_platforms(self, storage, mock_redis):
        """Test listing platforms from Redis."""
        mock_redis.keys.return_value = [
            b"mesh:tokens:platform1",
            b"mesh:tokens:platform2",
            b"mesh:tokens:platform3"
        ]

        platforms = await storage.list_platforms()

        assert set(platforms) == {"platform1", "platform2", "platform3"}
        mock_redis.keys.assert_called_once_with("mesh:tokens:*")


class TestOAuth2RefreshHandler:
    """Test OAuth2RefreshHandler functionality."""

    @pytest.fixture
    def refresh_handler(self):
        """OAuth2 refresh handler fixture."""
        return OAuth2RefreshHandler(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_url="https://oauth.example.com/token"
        )

    @pytest.fixture
    def expired_token(self):
        """Expired token fixture."""
        return TokenInfo(
            access_token="old_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            token_type="Bearer",
            scope="read write"
        )

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, refresh_handler, expired_token):
        """Test successful token refresh."""
        mock_response_data = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "read write"
        }

        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            new_token = await refresh_handler.refresh_token("test_platform", expired_token)

            assert new_token.access_token == "new_access_token"
            assert new_token.refresh_token == "new_refresh_token"
            assert new_token.token_type == "Bearer"
            assert new_token.scope == "read write"
            assert new_token.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_refresh_token_no_refresh_token(self, refresh_handler):
        """Test refresh when no refresh token available."""
        token_without_refresh = TokenInfo(access_token="test_token")

        with pytest.raises(TokenRefreshError, match="No refresh token available"):
            await refresh_handler.refresh_token("test_platform", token_without_refresh)

    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self, refresh_handler, expired_token):
        """Test refresh with HTTP error."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 400

            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(TokenRefreshError, match="Token refresh failed: 400"):
                await refresh_handler.refresh_token("test_platform", expired_token)


class TestTokenManager:
    """Test TokenManager functionality."""

    @pytest.fixture
    def mock_storage(self):
        """Mock token storage fixture."""
        storage = AsyncMock()
        storage.store_token = AsyncMock()
        storage.get_token = AsyncMock()
        storage.delete_token = AsyncMock()
        storage.list_platforms = AsyncMock()
        return storage

    @pytest.fixture
    def mock_refresh_handler(self):
        """Mock refresh handler fixture."""
        handler = AsyncMock()
        handler.refresh_token = AsyncMock()
        return handler

    @pytest.fixture
    def token_manager(self, mock_storage):
        """Token manager fixture."""
        return TokenManager(storage=mock_storage)

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
    async def test_store_token(self, token_manager, mock_storage, sample_token):
        """Test storing a token."""
        platform = "test_platform"

        await token_manager.store_token(platform, sample_token)

        mock_storage.store_token.assert_called_once_with(
            platform, sample_token)

    @pytest.mark.asyncio
    async def test_get_token_no_refresh(self, token_manager, mock_storage, sample_token):
        """Test getting token without refresh."""
        platform = "test_platform"
        mock_storage.get_token.return_value = sample_token

        token = await token_manager.get_token(platform, auto_refresh=False)

        assert token is sample_token
        mock_storage.get_token.assert_called_once_with(platform)

    @pytest.mark.asyncio
    async def test_get_token_with_refresh(self, token_manager, mock_storage, mock_refresh_handler):
        """Test getting token with automatic refresh."""
        platform = "test_platform"

        # Token that expires soon
        expiring_token = TokenInfo(
            access_token="old_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=2)  # Expires soon
        )

        new_token = TokenInfo(
            access_token="new_token",
            refresh_token="new_refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        mock_storage.get_token.side_effect = [expiring_token, new_token]
        mock_refresh_handler.refresh_token.return_value = new_token

        token_manager.register_refresh_handler(platform, mock_refresh_handler)

        token = await token_manager.get_token(platform, auto_refresh=True)

        assert token is new_token
        mock_refresh_handler.refresh_token.assert_called_once_with(
            platform, expiring_token)
        mock_storage.store_token.assert_called_once_with(platform, new_token)

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, token_manager, mock_storage):
        """Test getting non-existent token."""
        mock_storage.get_token.return_value = None

        token = await token_manager.get_token("nonexistent")

        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token(self, token_manager, mock_storage):
        """Test deleting a token."""
        platform = "test_platform"

        await token_manager.delete_token(platform)

        mock_storage.delete_token.assert_called_once_with(platform)

    @pytest.mark.asyncio
    async def test_list_platforms(self, token_manager, mock_storage):
        """Test listing platforms."""
        platforms = ["platform1", "platform2", "platform3"]
        mock_storage.list_platforms.return_value = platforms

        result = await token_manager.list_platforms()

        assert result == platforms

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, token_manager, mock_storage):
        """Test cleaning up expired tokens."""
        platforms = ["platform1", "platform2", "platform3"]

        # Mock tokens: expired, valid, expired
        tokens = [
            TokenInfo(access_token="token1",
                      expires_at=datetime.now(timezone.utc) - timedelta(hours=1)),
            TokenInfo(access_token="token2",
                      expires_at=datetime.now(timezone.utc) + timedelta(hours=1)),
            TokenInfo(access_token="token3",
                      expires_at=datetime.now(timezone.utc) - timedelta(hours=2))
        ]

        mock_storage.list_platforms.return_value = platforms
        mock_storage.get_token.side_effect = tokens

        await token_manager.cleanup_expired_tokens()

        # Should delete expired tokens (platform1 and platform3)
        expected_deletes = [
            (("platform1",), {}),
            (("platform3",), {})
        ]
        assert mock_storage.delete_token.call_args_list == expected_deletes

    @pytest.mark.asyncio
    async def test_refresh_token_no_handler(self, token_manager, mock_storage):
        """Test refresh when no handler registered."""
        platform = "test_platform"

        expiring_token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=2)
        )

        mock_storage.get_token.return_value = expiring_token

        # Should return original token when no handler
        token = await token_manager.get_token(platform, auto_refresh=True)

        assert token is expiring_token

    @pytest.mark.asyncio
    async def test_concurrent_refresh_protection(self, token_manager, mock_storage, mock_refresh_handler):
        """Test that concurrent refreshes are protected by locks."""
        platform = "test_platform"

        expiring_token = TokenInfo(
            access_token="old_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=2)
        )

        new_token = TokenInfo(
            access_token="new_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        # First call returns expiring token, subsequent calls return new token
        mock_storage.get_token.side_effect = [
            expiring_token, new_token, new_token]
        mock_refresh_handler.refresh_token.return_value = new_token

        token_manager.register_refresh_handler(platform, mock_refresh_handler)

        # Make concurrent requests
        tasks = [
            token_manager.get_token(platform, auto_refresh=True),
            token_manager.get_token(platform, auto_refresh=True)
        ]

        results = await asyncio.gather(*tasks)

        # Both should get the new token
        assert all(token.access_token == "new_token" for token in results)

        # Refresh should only be called once due to locking
        assert mock_refresh_handler.refresh_token.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
