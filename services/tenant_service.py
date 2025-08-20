"""
Tenant management service for multi-tenant architecture.

This service handles tenant provisioning, configuration, quota management,
and lifecycle operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from db.models.tenant import Tenant, TenantUser, TenantQuotaUsage
from db.models.user import User
from services.security.tenant_security import TenantSecurityService, get_tenant_security_service
from services.security.types import KeyType, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)


class TenantServiceError(Exception):
    """Base exception for tenant service operations."""
    pass


class TenantAlreadyExistsError(TenantServiceError):
    """Raised when trying to create a tenant that already exists."""
    pass


class TenantNotFoundError(TenantServiceError):
    """Raised when a tenant is not found."""
    pass


class QuotaExceededError(TenantServiceError):
    """Raised when a tenant quota is exceeded."""
    pass


class TenantService:
    """
    Tenant management service for multi-tenant operations.

    Handles tenant provisioning, configuration, quota management,
    and user access control.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        security_service: Optional[TenantSecurityService] = None
    ):
        self.db = db_session
        self.security_service = security_service or get_tenant_security_service()

        logger.info("Tenant Service initialized")

    async def create_tenant(
        self,
        name: str,
        display_name: str,
        admin_email: str,
        tier: str = "standard",
        description: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None,
        custom_quotas: Optional[Dict[str, int]] = None
    ) -> Tenant:
        """
        Create a new tenant with default configuration.

        Args:
            name: Unique tenant name (slug)
            display_name: Human-readable tenant name
            admin_email: Admin email address
            tier: Tenant tier (free, standard, premium, enterprise)
            description: Optional description
            contact_name: Contact person name
            contact_phone: Contact phone number
            custom_quotas: Custom quota overrides

        Returns:
            Created Tenant object
        """
        try:
            # Check if tenant already exists
            existing = await self.db.execute(
                select(Tenant).where(Tenant.name == name)
            )
            if existing.scalar_one_or_none():
                raise TenantAlreadyExistsError(
                    f"Tenant '{name}' already exists")

            # Set default quotas based on tier
            quotas = self._get_default_quotas(tier)
            if custom_quotas:
                quotas.update(custom_quotas)

            # Create tenant
            tenant = Tenant(
                name=name,
                display_name=display_name,
                description=description,
                tier=tier,
                admin_email=admin_email,
                contact_name=contact_name,
                contact_phone=contact_phone,
                max_users=quotas.get("max_users", 10),
                max_messages_per_month=quotas.get(
                    "max_messages_per_month", 100000),
                max_storage_gb=quotas.get("max_storage_gb", 10),
                max_api_requests_per_hour=quotas.get(
                    "max_api_requests_per_hour", 1000),
                max_ai_requests_per_day=quotas.get(
                    "max_ai_requests_per_day", 1000),
                settings={
                    "created_by": "system",
                    "tier": tier,
                    "auto_provisioned": True
                }
            )

            self.db.add(tenant)
            await self.db.flush()  # Get the ID

            # Create tenant-specific encryption keys
            tenant_keys = await self.security_service.create_tenant_encryption_keys(
                str(tenant.id),
                [KeyType.DATA_ENCRYPTION_KEY, KeyType.TOKEN_ENCRYPTION_KEY]
            )

            # Store the primary encryption key ID
            tenant.encryption_key_id = tenant_keys[KeyType.DATA_ENCRYPTION_KEY.value].key_id

            await self.db.commit()

            logger.info(f"Created tenant: {name} (ID: {tenant.id})")
            return tenant

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create tenant '{name}': {e}")
            raise TenantServiceError(f"Failed to create tenant: {e}")

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        try:
            result = await self.db.execute(
                select(Tenant)
                .options(selectinload(Tenant.users))
                .where(Tenant.id == tenant_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            return None

    async def get_tenant_by_name(self, name: str) -> Optional[Tenant]:
        """Get tenant by name."""
        try:
            result = await self.db.execute(
                select(Tenant)
                .options(selectinload(Tenant.users))
                .where(Tenant.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get tenant by name '{name}': {e}")
            return None

    async def update_tenant(
        self,
        tenant_id: str,
        updates: Dict[str, Any]
    ) -> Tenant:
        """
        Update tenant configuration.

        Args:
            tenant_id: Tenant identifier
            updates: Dictionary of fields to update

        Returns:
            Updated Tenant object
        """
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # Update allowed fields
            allowed_fields = {
                'display_name', 'description', 'tier', 'admin_email',
                'contact_name', 'contact_phone', 'is_active',
                'max_users', 'max_messages_per_month', 'max_storage_gb',
                'max_api_requests_per_hour', 'max_ai_requests_per_day',
                'data_retention_days', 'pii_redaction_enabled',
                'audit_logging_enabled', 'settings'
            }

            for field, value in updates.items():
                if field in allowed_fields and hasattr(tenant, field):
                    setattr(tenant, field, value)

            tenant.updated_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Updated tenant {tenant_id}: {list(updates.keys())}")
            return tenant

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update tenant {tenant_id}: {e}")
            raise TenantServiceError(f"Failed to update tenant: {e}")

    async def delete_tenant(self, tenant_id: str) -> bool:
        """
        Delete a tenant and all associated data.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if deleted successfully
        """
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # TODO: Implement cascade deletion of all tenant data
            # This should include messages, threads, participants, etc.

            await self.db.delete(tenant)
            await self.db.commit()

            logger.info(f"Deleted tenant {tenant_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise TenantServiceError(f"Failed to delete tenant: {e}")

    async def add_user_to_tenant(
        self,
        tenant_id: str,
        user_id: str,
        role: str = "member",
        permissions: Optional[List[str]] = None
    ) -> TenantUser:
        """
        Add a user to a tenant with specified role.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            role: User role (admin, member, viewer)
            permissions: Specific permissions

        Returns:
            Created TenantUser object
        """
        try:
            # Check if tenant exists
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # Check user quota
            if tenant.current_users >= tenant.max_users:
                raise QuotaExceededError(
                    f"User quota exceeded for tenant {tenant_id}")

            # Check if user already exists in tenant
            existing = await self.db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id
                )
            )
            if existing.scalar_one_or_none():
                raise TenantServiceError(
                    f"User {user_id} already exists in tenant {tenant_id}")

            # Create tenant user association
            tenant_user = TenantUser(
                tenant_id=tenant_id,
                user_id=user_id,
                role=role,
                permissions=permissions or []
            )

            self.db.add(tenant_user)

            # Update tenant user count
            tenant.current_users += 1

            await self.db.commit()

            logger.info(
                f"Added user {user_id} to tenant {tenant_id} with role {role}")
            return tenant_user

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to add user {user_id} to tenant {tenant_id}: {e}")
            raise TenantServiceError(f"Failed to add user to tenant: {e}")

    async def remove_user_from_tenant(
        self,
        tenant_id: str,
        user_id: str
    ) -> bool:
        """
        Remove a user from a tenant.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            True if removed successfully
        """
        try:
            # Find tenant user association
            result = await self.db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id
                )
            )
            tenant_user = result.scalar_one_or_none()

            if not tenant_user:
                raise TenantServiceError(
                    f"User {user_id} not found in tenant {tenant_id}")

            await self.db.delete(tenant_user)

            # Update tenant user count
            tenant = await self.get_tenant(tenant_id)
            if tenant:
                tenant.current_users = max(0, tenant.current_users - 1)

            await self.db.commit()

            logger.info(f"Removed user {user_id} from tenant {tenant_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to remove user {user_id} from tenant {tenant_id}: {e}")
            raise TenantServiceError(f"Failed to remove user from tenant: {e}")

    async def check_quota(
        self,
        tenant_id: str,
        quota_type: str,
        requested_amount: int = 1
    ) -> Dict[str, Any]:
        """
        Check if tenant can perform action within quota limits.

        Args:
            tenant_id: Tenant identifier
            quota_type: Type of quota (messages, storage, api_requests, ai_requests)
            requested_amount: Amount being requested

        Returns:
            Dictionary with quota status
        """
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # Check specific quota
            quota_exceeded = False
            current_usage = 0
            limit = 0

            if quota_type == "messages":
                current_usage = tenant.current_messages_this_month
                limit = tenant.max_messages_per_month
                quota_exceeded = (current_usage + requested_amount) > limit
            elif quota_type == "storage":
                current_usage = tenant.current_storage_gb
                limit = tenant.max_storage_gb
                quota_exceeded = (current_usage + requested_amount) > limit
            elif quota_type == "api_requests":
                current_usage = tenant.current_api_requests_this_hour
                limit = tenant.max_api_requests_per_hour
                quota_exceeded = (current_usage + requested_amount) > limit
            elif quota_type == "ai_requests":
                current_usage = tenant.current_ai_requests_today
                limit = tenant.max_ai_requests_per_day
                quota_exceeded = (current_usage + requested_amount) > limit
            elif quota_type == "users":
                current_usage = tenant.current_users
                limit = tenant.max_users
                quota_exceeded = (current_usage + requested_amount) > limit

            return {
                "tenant_id": tenant_id,
                "quota_type": quota_type,
                "current_usage": current_usage,
                "limit": limit,
                "requested_amount": requested_amount,
                "allowed": not quota_exceeded,
                "usage_percentage": (current_usage / max(limit, 1)) * 100,
                "remaining": max(0, limit - current_usage)
            }

        except Exception as e:
            logger.error(
                f"Failed to check quota for {tenant_id}/{quota_type}: {e}")
            raise TenantServiceError(f"Failed to check quota: {e}")

    async def update_quota_usage(
        self,
        tenant_id: str,
        quota_type: str,
        amount: int
    ) -> bool:
        """
        Update quota usage for a tenant.

        Args:
            tenant_id: Tenant identifier
            quota_type: Type of quota to update
            amount: Amount to add to current usage

        Returns:
            True if updated successfully
        """
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # Update specific quota usage
            if quota_type == "messages":
                tenant.current_messages_this_month += amount
            elif quota_type == "storage":
                tenant.current_storage_gb += amount
            elif quota_type == "api_requests":
                tenant.current_api_requests_this_hour += amount
            elif quota_type == "ai_requests":
                tenant.current_ai_requests_today += amount

            # Update last activity
            tenant.last_activity_at = datetime.utcnow()

            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to update quota usage for {tenant_id}/{quota_type}: {e}")
            return False

    async def list_tenants(
        self,
        active_only: bool = True,
        tier: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tenant]:
        """
        List tenants with optional filtering.

        Args:
            active_only: Only return active tenants
            tier: Filter by tier
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Tenant objects
        """
        try:
            query = select(Tenant).options(selectinload(Tenant.users))

            if active_only:
                query = query.where(Tenant.is_active == True)

            if tier:
                query = query.where(Tenant.tier == tier)

            query = query.order_by(Tenant.created_at.desc()).limit(
                limit).offset(offset)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to list tenants: {e}")
            return []

    async def get_tenant_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with tenant statistics
        """
        try:
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")

            # Get quota usage percentages
            quotas = {
                "users": tenant.get_quota_usage_percentage("users"),
                "messages": tenant.get_quota_usage_percentage("messages"),
                "storage": tenant.get_quota_usage_percentage("storage"),
                "api_requests": tenant.get_quota_usage_percentage("api_requests"),
                "ai_requests": tenant.get_quota_usage_percentage("ai_requests")
            }

            # Get security status
            security_status = await self.security_service.get_tenant_security_status(tenant_id)

            return {
                "tenant_id": tenant_id,
                "name": tenant.name,
                "display_name": tenant.display_name,
                "tier": tenant.tier,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat(),
                "last_activity_at": tenant.last_activity_at.isoformat() if tenant.last_activity_at else None,
                "quotas": quotas,
                "current_usage": {
                    "users": tenant.current_users,
                    "messages_this_month": tenant.current_messages_this_month,
                    "storage_gb": tenant.current_storage_gb,
                    "api_requests_this_hour": tenant.current_api_requests_this_hour,
                    "ai_requests_today": tenant.current_ai_requests_today
                },
                "limits": {
                    "max_users": tenant.max_users,
                    "max_messages_per_month": tenant.max_messages_per_month,
                    "max_storage_gb": tenant.max_storage_gb,
                    "max_api_requests_per_hour": tenant.max_api_requests_per_hour,
                    "max_ai_requests_per_day": tenant.max_ai_requests_per_day
                },
                "security": security_status
            }

        except Exception as e:
            logger.error(
                f"Failed to get tenant statistics for {tenant_id}: {e}")
            return {"error": str(e)}

    def _get_default_quotas(self, tier: str) -> Dict[str, int]:
        """Get default quotas based on tenant tier."""
        quotas = {
            "free": {
                "max_users": 3,
                "max_messages_per_month": 10000,
                "max_storage_gb": 1,
                "max_api_requests_per_hour": 100,
                "max_ai_requests_per_day": 100
            },
            "standard": {
                "max_users": 10,
                "max_messages_per_month": 100000,
                "max_storage_gb": 10,
                "max_api_requests_per_hour": 1000,
                "max_ai_requests_per_day": 1000
            },
            "premium": {
                "max_users": 50,
                "max_messages_per_month": 1000000,
                "max_storage_gb": 100,
                "max_api_requests_per_hour": 10000,
                "max_ai_requests_per_day": 10000
            },
            "enterprise": {
                "max_users": 1000,
                "max_messages_per_month": 10000000,
                "max_storage_gb": 1000,
                "max_api_requests_per_hour": 100000,
                "max_ai_requests_per_day": 100000
            }
        }

        return quotas.get(tier, quotas["standard"])
