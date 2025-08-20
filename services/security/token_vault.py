"""
Token Vault service with KMS integration for secure token storage.

This service provides secure storage and retrieval of authentication tokens
with Hardware Security Module (HSM) or KMS encryption support.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import asyncio
from contextlib import asynccontextmanager

from .types import TokenMetadata, EncryptionKey, KeyType, EncryptionAlgorithm
from .encryption_service import EncryptionService
from .audit_logger import AuditLogger
from ..storage.backends import get_storage_backend

logger = logging.getLogger(__name__)


class TokenVaultError(Exception):
    """Base exception for token vault operations."""
    pass


class TokenNotFoundError(TokenVaultError):
    """Raised when a token is not found."""
    pass


class TokenExpiredError(TokenVaultError):
    """Raised when a token has expired."""
    pass


class TokenVault:
    """
    Secure token storage service with KMS integration.

    Provides secure storage and retrieval of authentication tokens
    with encryption, expiration handling, and audit logging.
    """

    def __init__(
        self,
        encryption_service: EncryptionService,
        audit_logger: AuditLogger,
        storage_backend: Optional[Any] = None,
        kms_key_id: Optional[str] = None
    ):
        self.encryption_service = encryption_service
        self.audit_logger = audit_logger
        self.storage_backend = storage_backend or get_storage_backend()
        self.kms_key_id = kms_key_id
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=15)

    async def store_token(
        self,
        token_id: str,
        token_value: str,
        platform: str,
        user_id: str,
        token_type: str = "access_token",
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TokenMetadata:
        """
        Store a token securely with encryption.

        Args:
            token_id: Unique identifier for the token
            token_value: The actual token value to encrypt and store
            platform: Platform the token belongs to (gmail, slack, etc.)
            user_id: User ID the token belongs to
            token_type: Type of token (access_token, refresh_token, etc.)
            expires_at: When the token expires
            scopes: List of scopes the token has access to
            metadata: Additional metadata to store with the token

        Returns:
            TokenMetadata object with token information
        """
        try:
            # Create token metadata
            token_metadata = TokenMetadata(
                token_id=token_id,
                platform=platform,
                user_id=user_id,
                token_type=token_type,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                scopes=scopes or [],
                metadata=metadata or {}
            )

            # Encrypt the token value
            encrypted_token = await self.encryption_service.encrypt_field(
                token_value,
                field_name="token_value",
                key_type=KeyType.TOKEN_ENCRYPTION_KEY
            )

            # Prepare storage data
            storage_data = {
                "metadata": {
                    "token_id": token_metadata.token_id,
                    "platform": token_metadata.platform,
                    "user_id": token_metadata.user_id,
                    "token_type": token_metadata.token_type,
                    "created_at": token_metadata.created_at.isoformat(),
                    "expires_at": token_metadata.expires_at.isoformat() if token_metadata.expires_at else None,
                    "scopes": token_metadata.scopes,
                    "metadata": token_metadata.metadata
                },
                "encrypted_token": {
                    "encrypted_value": base64.b64encode(encrypted_token.encrypted_value).decode(),
                    "key_id": encrypted_token.key_id,
                    "algorithm": encrypted_token.algorithm.value,
                    "iv": base64.b64encode(encrypted_token.iv).decode(),
                    "tag": base64.b64encode(encrypted_token.tag).decode() if encrypted_token.tag else None
                }
            }

            # Store in backend
            storage_key = f"tokens/{platform}/{user_id}/{token_id}"
            await self.storage_backend.store(storage_key, json.dumps(storage_data))

            # Update cache
            self._token_cache[token_id] = {
                "data": storage_data,
                "cached_at": datetime.utcnow()
            }

            # Audit log
            await self.audit_logger.log_event(
                event_type="token_access",
                action="store_token",
                user_id=user_id,
                resource_type="token",
                resource_id=token_id,
                details={
                    "platform": platform,
                    "token_type": token_type,
                    "has_expiration": expires_at is not None
                }
            )

            logger.info(
                f"Token stored successfully: {token_id} for {platform}/{user_id}")
            return token_metadata

        except Exception as e:
            await self.audit_logger.log_event(
                event_type="token_access",
                action="store_token",
                user_id=user_id,
                resource_type="token",
                resource_id=token_id,
                success=False,
                error_message=str(e),
                details={"platform": platform, "token_type": token_type}
            )
            logger.error(f"Failed to store token {token_id}: {e}")
            raise TokenVaultError(f"Failed to store token: {e}")

    async def retrieve_token(
        self,
        token_id: str,
        user_id: str,
        platform: str
    ) -> str:
        """
        Retrieve and decrypt a token.

        Args:
            token_id: Unique identifier for the token
            user_id: User ID the token belongs to
            platform: Platform the token belongs to

        Returns:
            Decrypted token value

        Raises:
            TokenNotFoundError: If token doesn't exist
            TokenExpiredError: If token has expired
        """
        try:
            # Check cache first
            cached_token = self._get_from_cache(token_id)
            if cached_token:
                storage_data = cached_token["data"]
            else:
                # Load from storage
                storage_key = f"tokens/{platform}/{user_id}/{token_id}"
                stored_data = await self.storage_backend.retrieve(storage_key)
                if not stored_data:
                    raise TokenNotFoundError(f"Token not found: {token_id}")

                storage_data = json.loads(stored_data)

                # Update cache
                self._token_cache[token_id] = {
                    "data": storage_data,
                    "cached_at": datetime.utcnow()
                }

            # Check expiration
            metadata = storage_data["metadata"]
            if metadata.get("expires_at"):
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if datetime.utcnow() > expires_at:
                    await self.audit_logger.log_event(
                        event_type="token_access",
                        action="retrieve_token",
                        user_id=user_id,
                        resource_type="token",
                        resource_id=token_id,
                        success=False,
                        error_message="Token expired",
                        details={"platform": platform,
                                 "expires_at": metadata["expires_at"]}
                    )
                    raise TokenExpiredError(f"Token expired: {token_id}")

            # Decrypt token
            encrypted_data = storage_data["encrypted_token"]
            encrypted_token_data = {
                "encrypted_value": base64.b64decode(encrypted_data["encrypted_value"]),
                "key_id": encrypted_data["key_id"],
                "algorithm": EncryptionAlgorithm(encrypted_data["algorithm"]),
                "iv": base64.b64decode(encrypted_data["iv"]),
                "tag": base64.b64decode(encrypted_data["tag"]) if encrypted_data.get("tag") else None
            }

            decrypted_token = await self.encryption_service.decrypt_field(
                encrypted_token_data,
                field_name="token_value"
            )

            # Audit log
            await self.audit_logger.log_event(
                event_type="token_access",
                action="retrieve_token",
                user_id=user_id,
                resource_type="token",
                resource_id=token_id,
                details={"platform": platform}
            )

            return decrypted_token

        except (TokenNotFoundError, TokenExpiredError):
            raise
        except Exception as e:
            await self.audit_logger.log_event(
                event_type="token_access",
                action="retrieve_token",
                user_id=user_id,
                resource_type="token",
                resource_id=token_id,
                success=False,
                error_message=str(e),
                details={"platform": platform}
            )
            logger.error(f"Failed to retrieve token {token_id}: {e}")
            raise TokenVaultError(f"Failed to retrieve token: {e}")

    async def delete_token(
        self,
        token_id: str,
        user_id: str,
        platform: str
    ) -> bool:
        """
        Delete a token from storage.

        Args:
            token_id: Unique identifier for the token
            user_id: User ID the token belongs to
            platform: Platform the token belongs to

        Returns:
            True if token was deleted, False if not found
        """
        try:
            storage_key = f"tokens/{platform}/{user_id}/{token_id}"
            deleted = await self.storage_backend.delete(storage_key)

            # Remove from cache
            self._token_cache.pop(token_id, None)

            # Audit log
            await self.audit_logger.log_event(
                event_type="data_deletion",
                action="delete_token",
                user_id=user_id,
                resource_type="token",
                resource_id=token_id,
                details={"platform": platform, "deleted": deleted}
            )

            if deleted:
                logger.info(f"Token deleted successfully: {token_id}")
            else:
                logger.warning(f"Token not found for deletion: {token_id}")

            return deleted

        except Exception as e:
            await self.audit_logger.log_event(
                event_type="data_deletion",
                action="delete_token",
                user_id=user_id,
                resource_type="token",
                resource_id=token_id,
                success=False,
                error_message=str(e),
                details={"platform": platform}
            )
            logger.error(f"Failed to delete token {token_id}: {e}")
            raise TokenVaultError(f"Failed to delete token: {e}")

    async def list_tokens(
        self,
        user_id: str,
        platform: Optional[str] = None,
        token_type: Optional[str] = None
    ) -> List[TokenMetadata]:
        """
        List tokens for a user, optionally filtered by platform and type.

        Args:
            user_id: User ID to list tokens for
            platform: Optional platform filter
            token_type: Optional token type filter

        Returns:
            List of TokenMetadata objects
        """
        try:
            # This would need to be implemented based on the storage backend
            # For now, return empty list as this requires storage backend support
            tokens = []

            # Audit log
            await self.audit_logger.log_event(
                event_type="data_access",
                action="list_tokens",
                user_id=user_id,
                resource_type="token",
                details={
                    "platform_filter": platform,
                    "token_type_filter": token_type,
                    "result_count": len(tokens)
                }
            )

            return tokens

        except Exception as e:
            await self.audit_logger.log_event(
                event_type="data_access",
                action="list_tokens",
                user_id=user_id,
                resource_type="token",
                success=False,
                error_message=str(e),
                details={"platform_filter": platform,
                         "token_type_filter": token_type}
            )
            logger.error(f"Failed to list tokens for user {user_id}: {e}")
            raise TokenVaultError(f"Failed to list tokens: {e}")

    def _get_from_cache(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get token from cache if not expired."""
        cached = self._token_cache.get(token_id)
        if not cached:
            return None

        cached_at = cached["cached_at"]
        if datetime.utcnow() - cached_at > self._cache_ttl:
            # Cache expired
            self._token_cache.pop(token_id, None)
            return None

        return cached

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from storage.

        Returns:
            Number of tokens cleaned up
        """
        # This would need to be implemented based on storage backend capabilities
        # For now, return 0 as this requires storage backend support for listing
        cleaned_count = 0

        await self.audit_logger.log_event(
            event_type="data_deletion",
            action="cleanup_expired_tokens",
            details={"cleaned_count": cleaned_count}
        )

        return cleaned_count
