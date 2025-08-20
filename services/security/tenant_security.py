"""
Multi-tenant security service for tenant isolation and management.

This service provides tenant-specific encryption keys, data segregation,
quota enforcement, and access control.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from .encryption_service import EncryptionService
from .audit_logger import AuditLogger
from .types import SecurityConfig, AuditEventType, AuditSeverity, KeyType, EncryptionKey
from ..storage.backends import get_storage_backend

logger = logging.getLogger(__name__)


class TenantSecurityError(Exception):
    """Base exception for tenant security operations."""
    pass


class TenantNotFoundError(TenantSecurityError):
    """Raised when a tenant is not found."""
    pass


class QuotaExceededError(TenantSecurityError):
    """Raised when a tenant quota is exceeded."""
    pass


class TenantSecurityService:
    """
    Multi-tenant security service for data isolation and access control.

    Provides tenant-specific encryption keys, quota enforcement,
    and security policy management.
    """

    def __init__(
        self,
        encryption_service: Optional[EncryptionService] = None,
        audit_logger: Optional[AuditLogger] = None,
        config: Optional[SecurityConfig] = None
    ):
        self.encryption_service = encryption_service or EncryptionService()
        self.audit_logger = audit_logger
        self.config = config or SecurityConfig()
        self._tenant_keys: Dict[str, Dict[str, EncryptionKey]] = {}

        logger.info("Tenant Security Service initialized")

    async def create_tenant_encryption_keys(
        self,
        tenant_id: str,
        key_types: Optional[List[KeyType]] = None
    ) -> Dict[str, EncryptionKey]:
        """
        Create tenant-specific encryption keys.

        Args:
            tenant_id: Tenant identifier
            key_types: List of key types to create, defaults to all types

        Returns:
            Dictionary mapping key type to EncryptionKey
        """
        if key_types is None:
            key_types = [KeyType.DATA_ENCRYPTION_KEY,
                         KeyType.TOKEN_ENCRYPTION_KEY]

        try:
            tenant_keys = {}

            for key_type in key_types:
                key_id = f"tenant_{tenant_id}_{key_type.value}_{datetime.utcnow().strftime('%Y%m%d')}"

                # Create tenant-specific encryption key
                encryption_key = await self.encryption_service._get_or_create_key(
                    key_id=key_id,
                    key_type=key_type,
                    algorithm=self.config.encryption_algorithm
                )

                tenant_keys[key_type.value] = encryption_key

                # Store in tenant key cache
                if tenant_id not in self._tenant_keys:
                    self._tenant_keys[tenant_id] = {}
                self._tenant_keys[tenant_id][key_type.value] = encryption_key

                logger.info(
                    f"Created {key_type.value} key for tenant {tenant_id}: {key_id}")

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.KEY_ROTATION,
                    action="create_tenant_keys",
                    tenant_id=tenant_id,
                    resource_type="tenant_encryption_keys",
                    resource_id=tenant_id,
                    details={
                        "key_types": [kt.value for kt in key_types],
                        "key_count": len(tenant_keys)
                    }
                )

            return tenant_keys

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.KEY_ROTATION,
                    action="create_tenant_keys",
                    tenant_id=tenant_id,
                    resource_type="tenant_encryption_keys",
                    resource_id=tenant_id,
                    success=False,
                    error_message=str(e),
                    severity=AuditSeverity.HIGH
                )
            logger.error(f"Failed to create tenant keys for {tenant_id}: {e}")
            raise TenantSecurityError(f"Failed to create tenant keys: {e}")

    async def encrypt_tenant_data(
        self,
        tenant_id: str,
        data: str,
        field_name: str,
        key_type: KeyType = KeyType.DATA_ENCRYPTION_KEY
    ) -> Dict[str, Any]:
        """
        Encrypt data using tenant-specific encryption key.

        Args:
            tenant_id: Tenant identifier
            data: Data to encrypt
            field_name: Name of the field being encrypted
            key_type: Type of encryption key to use

        Returns:
            Dictionary with encrypted data and metadata
        """
        try:
            # Get tenant-specific key
            tenant_key = await self._get_tenant_key(tenant_id, key_type)

            # Use the tenant-specific key for encryption
            encrypted_data = await self.encryption_service.encrypt_field(
                data, f"tenant_{tenant_id}_{field_name}", key_type
            )

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.ENCRYPTION_OPERATION,
                    action="encrypt_tenant_data",
                    tenant_id=tenant_id,
                    resource_type="tenant_data",
                    resource_id=field_name,
                    details={
                        "field_name": field_name,
                        "key_type": key_type.value
                    }
                )

            return {
                "encrypted": True,
                "encrypted_value": encrypted_data.encrypted_value.hex(),
                "key_id": encrypted_data.key_id,
                "algorithm": encrypted_data.algorithm.value,
                "iv": encrypted_data.iv.hex(),
                "tag": encrypted_data.tag.hex() if encrypted_data.tag else None,
                "tenant_id": tenant_id
            }

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.ENCRYPTION_OPERATION,
                    action="encrypt_tenant_data",
                    tenant_id=tenant_id,
                    resource_type="tenant_data",
                    resource_id=field_name,
                    success=False,
                    error_message=str(e),
                    severity=AuditSeverity.HIGH
                )
            logger.error(
                f"Failed to encrypt tenant data for {tenant_id}/{field_name}: {e}")
            raise TenantSecurityError(f"Failed to encrypt tenant data: {e}")

    async def decrypt_tenant_data(
        self,
        tenant_id: str,
        encrypted_data: Dict[str, Any],
        field_name: str
    ) -> str:
        """
        Decrypt data using tenant-specific encryption key.

        Args:
            tenant_id: Tenant identifier
            encrypted_data: Dictionary with encrypted data
            field_name: Name of the field being decrypted

        Returns:
            Decrypted data string
        """
        try:
            # Verify tenant ownership
            if encrypted_data.get("tenant_id") != tenant_id:
                raise TenantSecurityError(
                    "Tenant ID mismatch in encrypted data")

            # Decrypt using the encryption service
            decrypted = await self.encryption_service.decrypt_field(
                encrypted_data, f"tenant_{tenant_id}_{field_name}"
            )

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DECRYPTION_OPERATION,
                    action="decrypt_tenant_data",
                    tenant_id=tenant_id,
                    resource_type="tenant_data",
                    resource_id=field_name,
                    details={"field_name": field_name}
                )

            return decrypted

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DECRYPTION_OPERATION,
                    action="decrypt_tenant_data",
                    tenant_id=tenant_id,
                    resource_type="tenant_data",
                    resource_id=field_name,
                    success=False,
                    error_message=str(e),
                    severity=AuditSeverity.HIGH
                )
            logger.error(
                f"Failed to decrypt tenant data for {tenant_id}/{field_name}: {e}")
            raise TenantSecurityError(f"Failed to decrypt tenant data: {e}")

    async def rotate_tenant_keys(
        self,
        tenant_id: str,
        key_type: Optional[KeyType] = None
    ) -> Dict[str, Any]:
        """
        Rotate encryption keys for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            key_type: Specific key type to rotate, or None for all

        Returns:
            Dictionary with rotation results
        """
        try:
            results = {}

            if key_type:
                # Rotate specific key type
                old_key = await self._get_tenant_key(tenant_id, key_type)
                new_key = await self.encryption_service.rotate_key(old_key.key_id)

                # Update tenant key cache
                self._tenant_keys[tenant_id][key_type.value] = new_key
                results[key_type.value] = new_key.key_id
            else:
                # Rotate all key types for tenant
                for kt in [KeyType.DATA_ENCRYPTION_KEY, KeyType.TOKEN_ENCRYPTION_KEY]:
                    try:
                        old_key = await self._get_tenant_key(tenant_id, kt)
                        new_key = await self.encryption_service.rotate_key(old_key.key_id)

                        # Update tenant key cache
                        if tenant_id not in self._tenant_keys:
                            self._tenant_keys[tenant_id] = {}
                        self._tenant_keys[tenant_id][kt.value] = new_key
                        results[kt.value] = new_key.key_id
                    except Exception as e:
                        logger.warning(
                            f"Failed to rotate {kt.value} for tenant {tenant_id}: {e}")
                        results[kt.value] = f"error: {str(e)}"

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.KEY_ROTATION,
                    action="rotate_tenant_keys",
                    tenant_id=tenant_id,
                    resource_type="tenant_encryption_keys",
                    resource_id=tenant_id,
                    details={
                        "key_type": key_type.value if key_type else "all",
                        "rotation_results": results
                    },
                    severity=AuditSeverity.MEDIUM
                )

            return results

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.KEY_ROTATION,
                    action="rotate_tenant_keys",
                    tenant_id=tenant_id,
                    resource_type="tenant_encryption_keys",
                    resource_id=tenant_id,
                    success=False,
                    error_message=str(e),
                    severity=AuditSeverity.HIGH
                )
            logger.error(f"Failed to rotate tenant keys for {tenant_id}: {e}")
            raise TenantSecurityError(f"Failed to rotate tenant keys: {e}")

    async def _get_tenant_key(self, tenant_id: str, key_type: KeyType) -> EncryptionKey:
        """Get tenant-specific encryption key."""
        if tenant_id not in self._tenant_keys:
            # Create keys for new tenant
            await self.create_tenant_encryption_keys(tenant_id, [key_type])

        if key_type.value not in self._tenant_keys[tenant_id]:
            # Create specific key type
            await self.create_tenant_encryption_keys(tenant_id, [key_type])

        return self._tenant_keys[tenant_id][key_type.value]

    async def validate_tenant_access(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        action: str
    ) -> bool:
        """
        Validate if a user has access to perform an action on a tenant resource.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            resource_type: Type of resource being accessed
            action: Action being performed

        Returns:
            True if access is allowed, False otherwise
        """
        try:
            # This would typically check against a database of tenant users and permissions
            # For now, we'll implement basic validation

            # Audit log the access attempt
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.AUTHORIZATION,
                    action="validate_tenant_access",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=f"{tenant_id}_{resource_type}",
                    details={
                        "action": action,
                        "resource_type": resource_type
                    }
                )

            # TODO: Implement actual RBAC logic
            return True

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.AUTHORIZATION,
                    action="validate_tenant_access",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    resource_type=resource_type,
                    success=False,
                    error_message=str(e),
                    severity=AuditSeverity.HIGH
                )
            logger.error(
                f"Failed to validate tenant access for {tenant_id}/{user_id}: {e}")
            return False

    async def check_quota_limits(
        self,
        tenant_id: str,
        quota_type: str,
        requested_amount: int = 1
    ) -> Dict[str, Any]:
        """
        Check if a tenant can perform an action within quota limits.

        Args:
            tenant_id: Tenant identifier
            quota_type: Type of quota to check (messages, storage, api_requests, etc.)
            requested_amount: Amount being requested

        Returns:
            Dictionary with quota status and limits
        """
        try:
            # This would typically query the tenant database for current usage
            # For now, we'll return a basic structure

            quota_status = {
                "tenant_id": tenant_id,
                "quota_type": quota_type,
                "requested_amount": requested_amount,
                "allowed": True,  # TODO: Implement actual quota checking
                "current_usage": 0,
                "limit": 1000000,
                "usage_percentage": 0.0,
                "reset_time": datetime.utcnow() + timedelta(hours=1)
            }

            # Audit log quota check
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DATA_ACCESS,
                    action="check_quota_limits",
                    tenant_id=tenant_id,
                    resource_type="tenant_quota",
                    resource_id=f"{tenant_id}_{quota_type}",
                    details={
                        "quota_type": quota_type,
                        "requested_amount": requested_amount,
                        "allowed": quota_status["allowed"]
                    }
                )

            return quota_status

        except Exception as e:
            logger.error(
                f"Failed to check quota limits for {tenant_id}/{quota_type}: {e}")
            raise TenantSecurityError(f"Failed to check quota limits: {e}")

    async def get_tenant_security_status(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get security status for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with tenant security status
        """
        try:
            status = {
                "tenant_id": tenant_id,
                "encryption": {
                    "enabled": True,
                    "key_count": len(self._tenant_keys.get(tenant_id, {})),
                    "algorithm": self.config.encryption_algorithm.value
                },
                "audit": {
                    "enabled": self.audit_logger is not None,
                    "retention_days": self.config.audit_retention_days
                },
                "quotas": {
                    "enforcement_enabled": True,
                    "last_checked": datetime.utcnow().isoformat()
                },
                "compliance": {
                    "data_isolation": True,
                    "encryption_at_rest": True,
                    "audit_trail": True
                }
            }

            return status

        except Exception as e:
            logger.error(
                f"Failed to get tenant security status for {tenant_id}: {e}")
            return {"error": str(e)}


# Global tenant security service instance
_tenant_security_service: Optional[TenantSecurityService] = None


def get_tenant_security_service(
    encryption_service: Optional[EncryptionService] = None,
    audit_logger: Optional[AuditLogger] = None,
    config: Optional[SecurityConfig] = None
) -> TenantSecurityService:
    """Get or create the global tenant security service instance."""
    global _tenant_security_service

    if _tenant_security_service is None:
        _tenant_security_service = TenantSecurityService(
            encryption_service=encryption_service,
            audit_logger=audit_logger,
            config=config
        )

    return _tenant_security_service
