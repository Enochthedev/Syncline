"""
Token management with secure storage and refresh capabilities.

This module provides secure token storage, automatic refresh, and
encryption for authentication tokens across different platforms.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from .base_connector import TokenInfo

logger = logging.getLogger(__name__)


class TokenStorageError(Exception):
    """Raised when token storage operations fail."""
    pass


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    pass


class TokenStorage(ABC):
    """Abstract base class for token storage backends."""

    @abstractmethod
    async def store_token(self, platform: str, token: TokenInfo) -> None:
        """Store a token for a platform."""
        pass

    @abstractmethod
    async def get_token(self, platform: str) -> Optional[TokenInfo]:
        """Retrieve a token for a platform."""
        pass

    @abstractmethod
    async def delete_token(self, platform: str) -> None:
        """Delete a token for a platform."""
        pass

    @abstractmethod
    async def list_platforms(self) -> list[str]:
        """List all platforms with stored tokens."""
        pass


class EncryptedFileTokenStorage(TokenStorage):
    """
    File-based token storage with encryption.

    Stores tokens in encrypted files using Fernet symmetric encryption.
    """

    def __init__(self, storage_dir: str = ".tokens", encryption_key: Optional[str] = None):
        self.storage_dir = storage_dir
        self._encryption_key = encryption_key
        self._fernet: Optional[Fernet] = None
        self._lock = asyncio.Lock()

        # Ensure storage directory exists
        os.makedirs(storage_dir, exist_ok=True)

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet encryption instance."""
        if self._fernet is None:
            if self._encryption_key:
                key = self._encryption_key.encode()
            else:
                # Use environment variable or generate key
                key_env = os.getenv("TOKEN_ENCRYPTION_KEY")
                if key_env:
                    key = key_env.encode()
                else:
                    # Generate key from system entropy (not recommended for production)
                    logger.warning(
                        "No encryption key provided, using system-generated key")
                    key = os.urandom(32)

            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'mesh_token_salt',  # In production, use random salt per token
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(key))
            self._fernet = Fernet(derived_key)

        return self._fernet

    def _get_token_file_path(self, platform: str) -> str:
        """Get file path for platform token."""
        return os.path.join(self.storage_dir, f"{platform}.token")

    async def store_token(self, platform: str, token: TokenInfo) -> None:
        """Store encrypted token to file."""
        async with self._lock:
            try:
                fernet = self._get_fernet()
                token_data = token.model_dump_json()
                encrypted_data = fernet.encrypt(token_data.encode())

                file_path = self._get_token_file_path(platform)
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)

                logger.debug(f"Token stored for platform: {platform}")

            except Exception as e:
                logger.error(f"Failed to store token for {platform}: {e}")
                raise TokenStorageError(f"Failed to store token: {e}")

    async def get_token(self, platform: str) -> Optional[TokenInfo]:
        """Retrieve and decrypt token from file."""
        async with self._lock:
            try:
                file_path = self._get_token_file_path(platform)
                if not os.path.exists(file_path):
                    return None

                fernet = self._get_fernet()
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()

                decrypted_data = fernet.decrypt(encrypted_data)
                token_dict = json.loads(decrypted_data.decode())

                return TokenInfo(**token_dict)

            except Exception as e:
                logger.error(f"Failed to retrieve token for {platform}: {e}")
                return None

    async def delete_token(self, platform: str) -> None:
        """Delete token file."""
        async with self._lock:
            try:
                file_path = self._get_token_file_path(platform)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Token deleted for platform: {platform}")

            except Exception as e:
                logger.error(f"Failed to delete token for {platform}: {e}")
                raise TokenStorageError(f"Failed to delete token: {e}")

    async def list_platforms(self) -> list[str]:
        """List all platforms with stored tokens."""
        try:
            platforms = []
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.token'):
                    platform = filename[:-6]  # Remove .token extension
                    platforms.append(platform)
            return platforms

        except Exception as e:
            logger.error(f"Failed to list platforms: {e}")
            return []


class RedisTokenStorage(TokenStorage):
    """
    Redis-based token storage with encryption.

    Stores tokens in Redis with optional encryption and TTL support.
    """

    def __init__(self, redis_client, encryption_key: Optional[str] = None, key_prefix: str = "mesh:tokens:"):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._encryption_key = encryption_key
        self._fernet: Optional[Fernet] = None

    def _get_fernet(self) -> Optional[Fernet]:
        """Get Fernet encryption instance if key provided."""
        if self._encryption_key and self._fernet is None:
            key = self._encryption_key.encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'mesh_redis_salt',
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(key))
            self._fernet = Fernet(derived_key)
        return self._fernet

    def _get_redis_key(self, platform: str) -> str:
        """Get Redis key for platform token."""
        return f"{self.key_prefix}{platform}"

    async def store_token(self, platform: str, token: TokenInfo) -> None:
        """Store token in Redis."""
        try:
            token_data = token.model_dump_json()

            # Encrypt if key provided
            fernet = self._get_fernet()
            if fernet:
                token_data = fernet.encrypt(token_data.encode()).decode()

            redis_key = self._get_redis_key(platform)

            # Set TTL based on token expiration
            ttl = None
            if token.expires_at:
                ttl = int(
                    (token.expires_at - datetime.now(timezone.utc)).total_seconds())
                if ttl <= 0:
                    logger.warning(f"Token for {platform} is already expired")
                    return

            if ttl:
                await self.redis.setex(redis_key, ttl, token_data)
            else:
                await self.redis.set(redis_key, token_data)

            logger.debug(f"Token stored in Redis for platform: {platform}")

        except Exception as e:
            logger.error(f"Failed to store token in Redis for {platform}: {e}")
            raise TokenStorageError(f"Failed to store token: {e}")

    async def get_token(self, platform: str) -> Optional[TokenInfo]:
        """Retrieve token from Redis."""
        try:
            redis_key = self._get_redis_key(platform)
            token_data = await self.redis.get(redis_key)

            if not token_data:
                return None

            # Decrypt if encrypted
            fernet = self._get_fernet()
            if fernet:
                token_data = fernet.decrypt(token_data.encode()).decode()

            token_dict = json.loads(token_data)
            return TokenInfo(**token_dict)

        except Exception as e:
            logger.error(
                f"Failed to retrieve token from Redis for {platform}: {e}")
            return None

    async def delete_token(self, platform: str) -> None:
        """Delete token from Redis."""
        try:
            redis_key = self._get_redis_key(platform)
            await self.redis.delete(redis_key)
            logger.debug(f"Token deleted from Redis for platform: {platform}")

        except Exception as e:
            logger.error(
                f"Failed to delete token from Redis for {platform}: {e}")
            raise TokenStorageError(f"Failed to delete token: {e}")

    async def list_platforms(self) -> list[str]:
        """List all platforms with stored tokens."""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)
            platforms = [key.decode().replace(self.key_prefix, '')
                         for key in keys]
            return platforms

        except Exception as e:
            logger.error(f"Failed to list platforms from Redis: {e}")
            return []


class TokenRefreshHandler(ABC):
    """Abstract base class for token refresh handlers."""

    @abstractmethod
    async def refresh_token(self, platform: str, current_token: TokenInfo) -> TokenInfo:
        """Refresh an expired or expiring token."""
        pass


class TokenManager:
    """
    Token manager with automatic refresh and secure storage.

    Manages authentication tokens across platforms with automatic refresh,
    secure storage, and expiration handling.
    """

    def __init__(
        self,
        storage: TokenStorage,
        refresh_handlers: Optional[Dict[str, TokenRefreshHandler]] = None
    ):
        self.storage = storage
        self.refresh_handlers = refresh_handlers or {}
        self._refresh_locks: Dict[str, asyncio.Lock] = {}

    def register_refresh_handler(self, platform: str, handler: TokenRefreshHandler) -> None:
        """Register a token refresh handler for a platform."""
        self.refresh_handlers[platform] = handler

    async def store_token(self, platform: str, token: TokenInfo) -> None:
        """Store a token for a platform."""
        await self.storage.store_token(platform, token)

    async def get_token(self, platform: str, auto_refresh: bool = True) -> Optional[TokenInfo]:
        """
        Get a token for a platform, with optional automatic refresh.

        Args:
            platform: Platform identifier
            auto_refresh: Whether to automatically refresh expiring tokens

        Returns:
            Valid token or None if not available
        """
        token = await self.storage.get_token(platform)

        if not token:
            return None

        # Check if token needs refresh
        if auto_refresh and token.expires_soon():
            token = await self._refresh_token_if_needed(platform, token)

        return token

    async def delete_token(self, platform: str) -> None:
        """Delete a token for a platform."""
        await self.storage.delete_token(platform)

    async def list_platforms(self) -> list[str]:
        """List all platforms with stored tokens."""
        return await self.storage.list_platforms()

    async def _refresh_token_if_needed(self, platform: str, token: TokenInfo) -> TokenInfo:
        """Refresh token if needed, with locking to prevent concurrent refreshes."""
        # Get or create lock for this platform
        if platform not in self._refresh_locks:
            self._refresh_locks[platform] = asyncio.Lock()

        async with self._refresh_locks[platform]:
            # Check again in case another coroutine already refreshed
            current_token = await self.storage.get_token(platform)
            if current_token and not current_token.expires_soon():
                return current_token

            # Refresh token
            if platform not in self.refresh_handlers:
                logger.warning(f"No refresh handler for platform {platform}")
                return token

            try:
                logger.info(f"Refreshing token for platform: {platform}")
                new_token = await self.refresh_handlers[platform].refresh_token(platform, token)
                await self.storage.store_token(platform, new_token)
                logger.info(
                    f"Token refreshed successfully for platform: {platform}")
                return new_token

            except Exception as e:
                logger.error(f"Failed to refresh token for {platform}: {e}")
                raise TokenRefreshError(f"Token refresh failed: {e}")

    async def cleanup_expired_tokens(self) -> None:
        """Remove expired tokens from storage."""
        platforms = await self.list_platforms()

        for platform in platforms:
            try:
                token = await self.storage.get_token(platform)
                if token and token.is_expired():
                    logger.info(
                        f"Removing expired token for platform: {platform}")
                    await self.storage.delete_token(platform)

            except Exception as e:
                logger.error(f"Error cleaning up token for {platform}: {e}")

    def get_token_info(self, platform: str) -> Dict[str, Any]:
        """Get token information without exposing sensitive data."""
        async def _get_info():
            token = await self.storage.get_token(platform)
            if not token:
                return {"exists": False}

            return {
                "exists": True,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                "is_expired": token.is_expired(),
                "expires_soon": token.expires_soon(),
                "token_type": token.token_type,
                "scope": token.scope
            }

        return asyncio.create_task(_get_info())


# Example refresh handler for OAuth 2.0
class OAuth2RefreshHandler(TokenRefreshHandler):
    """OAuth 2.0 token refresh handler."""

    def __init__(self, client_id: str, client_secret: str, token_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url

    async def refresh_token(self, platform: str, current_token: TokenInfo) -> TokenInfo:
        """Refresh OAuth 2.0 token."""
        if not current_token.refresh_token:
            raise TokenRefreshError("No refresh token available")

        import aiohttp

        async with aiohttp.ClientSession() as session:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': current_token.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }

            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    raise TokenRefreshError(
                        f"Token refresh failed: {response.status}")

                token_data = await response.json()

                return TokenInfo(
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get(
                        'refresh_token', current_token.refresh_token),
                    expires_at=datetime.now(
                        timezone.utc) + timedelta(seconds=token_data.get('expires_in', 3600)),
                    token_type=token_data.get('token_type', 'Bearer'),
                    scope=token_data.get('scope', current_token.scope)
                )
