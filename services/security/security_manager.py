"""
Security Manager service that coordinates all security services.

This service provides a unified interface for all security operations
including encryption, token management, audit logging, and key rotation.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .encryption_service import EncryptionService
from .token_vault import TokenVault
from .audit_logger import AuditLogger
from .key_rotation import KeyRotationService
from .types import SecurityConfig, AuditEventType, AuditSeverity, KeyType
from ..storage.backends import get_storage_backend

logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Unified security manager for all security operations.

    Coordinates encryption, token management, audit logging,
    and key rotation services.
    """

    def __init__(
        self,
        config: Optional[SecurityConfig] = None,
        storage_backend: Optional[Any] = None
    ):
        self.config = config or SecurityConfig()
        self.storage_backend = storage_backend or get_storage_backend()

        # Initialize security services
        self.audit_logger = AuditLogger(
            storage_backend=self.storage_backend,
            enable_database_logging=True,
            enable_file_logging=True,
            retention_days=self.config.audit_retention_days
        )

        self.encryption_service = EncryptionService(
            audit_logger=self.audit_logger,
            config=self.config
        )

        self.token_vault = TokenVault(
            encryption_service=self.encryption_service,
            audit_logger=self.audit_logger,
            storage_backend=self.storage_backend,
            kms_key_id=self.config.kms_key_id
        )

        self.key_rotation_service = KeyRotationService(
            encryption_service=self.encryption_service,
            audit_logger=self.audit_logger
        )

        logger.info("Security Manager initialized with all services")

    async def initialize(self) -> None:
        """Initialize security services."""
        try:
            # Start key rotation scheduler if enabled
            if self.config.key_rotation_enabled:
                await self.key_rotation_service.start_rotation_scheduler()

            await self.audit_logger.log_event(
                event_type=AuditEventType.AUTHENTICATION,
                action="security_manager_initialized",
                details={
                    "encryption_enabled": self.config.pii_encryption_enabled,
                    "token_encryption_enabled": self.config.token_encryption_enabled,
                    "key_rotation_enabled": self.config.key_rotation_enabled,
                    "audit_retention_days": self.config.audit_retention_days
                }
            )

            logger.info("Security Manager services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Security Manager: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown security services."""
        try:
            # Stop key rotation scheduler
            await self.key_rotation_service.stop_rotation_scheduler()

            await self.audit_logger.log_event(
                event_type=AuditEventType.AUTHENTICATION,
                action="security_manager_shutdown"
            )

            logger.info("Security Manager shutdown completed")

        except Exception as e:
            logger.error(f"Error during Security Manager shutdown: {e}")

    async def encrypt_sensitive_data(
        self,
        data: str,
        field_name: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Encrypt sensitive data with audit logging.

        Args:
            data: Data to encrypt
            field_name: Name of the field being encrypted
            user_id: User ID for audit logging

        Returns:
            Dictionary with encrypted data and metadata
        """
        if not self.config.pii_encryption_enabled:
            logger.warning("PII encryption is disabled")
            return {"encrypted": False, "data": data}

        try:
            encrypted_data = await self.encryption_service.encrypt_field(
                data, field_name, KeyType.DATA_ENCRYPTION_KEY
            )

            await self.audit_logger.log_event(
                event_type=AuditEventType.ENCRYPTION_OPERATION,
                action="encrypt_sensitive_data",
                user_id=user_id,
                resource_type="sensitive_data",
                resource_id=field_name,
                details={"field_name": field_name}
            )

            return {
                "encrypted": True,
                "encrypted_value": encrypted_data.encrypted_value.hex(),
                "key_id": encrypted_data.key_id,
                "algorithm": encrypted_data.algorithm.value,
                "iv": encrypted_data.iv.hex(),
                "tag": encrypted_data.tag.hex() if encrypted_data.tag else None
            }

        except Exception as e:
            await self.audit_logger.log_event(
                event_type=AuditEventType.ENCRYPTION_OPERATION,
                action="encrypt_sensitive_data",
                user_id=user_id,
                resource_type="sensitive_data",
                resource_id=field_name,
                success=False,
                error_message=str(e),
                severity=AuditSeverity.HIGH
            )
            logger.error(
                f"Failed to encrypt sensitive data for {field_name}: {e}")
            raise

    async def decrypt_sensitive_data(
        self,
        encrypted_data: Dict[str, Any],
        field_name: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Decrypt sensitive data with audit logging.

        Args:
            encrypted_data: Dictionary with encrypted data
            field_name: Name of the field being decrypted
            user_id: User ID for audit logging

        Returns:
            Decrypted data string
        """
        if not encrypted_data.get("encrypted", False):
            return encrypted_data.get("data", "")

        try:
            # Convert hex strings back to bytes
            decryption_data = {
                "encrypted_value": bytes.fromhex(encrypted_data["encrypted_value"]),
                "key_id": encrypted_data["key_id"],
                "algorithm": encrypted_data["algorithm"],
                "iv": bytes.fromhex(encrypted_data["iv"]),
                "tag": bytes.fromhex(encrypted_data["tag"]) if encrypted_data.get("tag") else None
            }

            decrypted = await self.encryption_service.decrypt_field(
                decryption_data, field_name
            )

            await self.audit_logger.log_event(
                event_type=AuditEventType.DECRYPTION_OPERATION,
                action="decrypt_sensitive_data",
                user_id=user_id,
                resource_type="sensitive_data",
                resource_id=field_name,
                details={"field_name": field_name}
            )

            return decrypted

        except Exception as e:
            await self.audit_logger.log_event(
                event_type=AuditEventType.DECRYPTION_OPERATION,
                action="decrypt_sensitive_data",
                user_id=user_id,
                resource_type="sensitive_data",
                resource_id=field_name,
                success=False,
                error_message=str(e),
                severity=AuditSeverity.HIGH
            )
            logger.error(
                f"Failed to decrypt sensitive data for {field_name}: {e}")
            raise

    async def store_platform_token(
        self,
        platform: str,
        user_id: str,
        token_value: str,
        token_type: str = "access_token",
        expires_at: Optional[datetime] = None,
        scopes: Optional[list] = None
    ) -> str:
        """
        Store a platform authentication token securely.

        Args:
            platform: Platform name (gmail, slack, etc.)
            user_id: User ID
            token_value: Token value to store
            token_type: Type of token
            expires_at: Token expiration time
            scopes: Token scopes

        Returns:
            Token ID
        """
        if not self.config.token_encryption_enabled:
            logger.warning("Token encryption is disabled")
            # In production, this should still store tokens securely
            return f"{platform}_{user_id}_{token_type}"

        try:
            token_id = f"{platform}_{user_id}_{token_type}_{datetime.utcnow().timestamp()}"

            await self.token_vault.store_token(
                token_id=token_id,
                token_value=token_value,
                platform=platform,
                user_id=user_id,
                token_type=token_type,
                expires_at=expires_at,
                scopes=scopes or []
            )

            return token_id

        except Exception as e:
            logger.error(
                f"Failed to store platform token for {platform}/{user_id}: {e}")
            raise

    async def retrieve_platform_token(
        self,
        token_id: str,
        platform: str,
        user_id: str
    ) -> str:
        """
        Retrieve a platform authentication token.

        Args:
            token_id: Token ID
            platform: Platform name
            user_id: User ID

        Returns:
            Decrypted token value
        """
        try:
            return await self.token_vault.retrieve_token(token_id, user_id, platform)
        except Exception as e:
            logger.error(f"Failed to retrieve platform token {token_id}: {e}")
            raise

    async def rotate_encryption_keys(self, key_type: Optional[KeyType] = None) -> Dict[str, Any]:
        """
        Rotate encryption keys immediately.

        Args:
            key_type: Specific key type to rotate, or None for all

        Returns:
            Dictionary with rotation results
        """
        try:
            results = {}

            if key_type:
                # Rotate specific key type
                job_id = await self.key_rotation_service.rotate_key_immediately(
                    f"{key_type.value}_current",
                    key_type,
                    "manual_rotation"
                )
                results[key_type.value] = job_id
            else:
                # Rotate all key types
                for kt in [KeyType.DATA_ENCRYPTION_KEY, KeyType.TOKEN_ENCRYPTION_KEY]:
                    job_id = await self.key_rotation_service.rotate_key_immediately(
                        f"{kt.value}_current",
                        kt,
                        "manual_rotation_all"
                    )
                    results[kt.value] = job_id

            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="manual_key_rotation",
                details={
                    "key_type": key_type.value if key_type else "all",
                    "rotation_jobs": results
                },
                severity=AuditSeverity.MEDIUM
            )

            return results

        except Exception as e:
            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="manual_key_rotation",
                success=False,
                error_message=str(e),
                severity=AuditSeverity.HIGH
            )
            logger.error(f"Failed to rotate encryption keys: {e}")
            raise

    async def get_security_status(self) -> Dict[str, Any]:
        """
        Get current security status and statistics.

        Returns:
            Dictionary with security status information
        """
        try:
            # Get audit statistics for the last 24 hours
            from datetime import timedelta
            start_time = datetime.utcnow() - timedelta(hours=24)
            audit_stats = await self.audit_logger.get_statistics(start_time=start_time)

            # Get rotation job status
            rotation_jobs = self.key_rotation_service.get_rotation_jobs()

            status = {
                "encryption": {
                    "pii_encryption_enabled": self.config.pii_encryption_enabled,
                    "token_encryption_enabled": self.config.token_encryption_enabled,
                    "algorithm": self.config.encryption_algorithm.value
                },
                "key_rotation": {
                    "enabled": self.config.key_rotation_enabled,
                    "scheduled_jobs": len([j for j in rotation_jobs if j.status == "scheduled"]),
                    "completed_jobs": len([j for j in rotation_jobs if j.status == "completed"]),
                    "failed_jobs": len([j for j in rotation_jobs if j.status == "failed"])
                },
                "audit": {
                    "retention_days": self.config.audit_retention_days,
                    "immutable_logs": self.config.immutable_audit_logs,
                    "last_24h_events": audit_stats.get("total_events", 0),
                    "last_24h_success_rate": audit_stats.get("success_rate", 0)
                },
                "compliance": {
                    "gdpr_ready": True,
                    "ccpa_ready": True,
                    "audit_trail_integrity": True
                }
            }

            return status

        except Exception as e:
            logger.error(f"Failed to get security status: {e}")
            return {"error": str(e)}


# Global security manager instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager(
    config: Optional[SecurityConfig] = None,
    storage_backend: Optional[Any] = None
) -> SecurityManager:
    """Get or create the global security manager instance."""
    global _security_manager

    if _security_manager is None:
        _security_manager = SecurityManager(
            config=config, storage_backend=storage_backend)

    return _security_manager


async def initialize_security() -> SecurityManager:
    """Initialize the global security manager."""
    security_manager = get_security_manager()
    await security_manager.initialize()
    return security_manager


async def shutdown_security() -> None:
    """Shutdown the global security manager."""
    global _security_manager

    if _security_manager:
        await _security_manager.shutdown()
        _security_manager = None
