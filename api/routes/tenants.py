"""
Tenant management API routes.

Provides endpoints for tenant provisioning, configuration,
quota management, and user access control.
"""

from fastapi import Request
from api.middleware.tenant_context import (
    get_current_tenant_context, require_tenant_access, require_admin_access,
    tenant_validator
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from services.tenant_service import TenantService, TenantServiceError, TenantNotFoundError, QuotaExceededError
from services.security.tenant_security import TenantSecurityService, get_tenant_security_service
from db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tenants", tags=["tenants"])
security = HTTPBearer()


# Pydantic models for request/response
class TenantCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, regex="^[a-z0-9-]+$")
    display_name: str = Field(..., min_length=1, max_length=500)
    admin_email: str = Field(..., regex="^[^@]+@[^@]+\.[^@]+$")
    tier: str = Field(default="standard",
                      regex="^(free|standard|premium|enterprise)$")
    description: Optional[str] = Field(None, max_length=1000)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    custom_quotas: Optional[Dict[str, int]] = None


class TenantUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    tier: Optional[str] = Field(
        None, regex="^(free|standard|premium|enterprise)$")
    admin_email: Optional[str] = Field(None, regex="^[^@]+@[^@]+\.[^@]+$")
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_messages_per_month: Optional[int] = Field(None, ge=1000)
    max_storage_gb: Optional[int] = Field(None, ge=1)
    max_api_requests_per_hour: Optional[int] = Field(None, ge=100)
    max_ai_requests_per_day: Optional[int] = Field(None, ge=10)
    data_retention_days: Optional[int] = Field(None, ge=30, le=2555)
    pii_redaction_enabled: Optional[bool] = None
    audit_logging_enabled: Optional[bool] = None


class TenantUserAdd(BaseModel):
    user_id: str = Field(..., regex="^[0-9a-f-]{36}$")
    role: str = Field(default="member", regex="^(admin|member|viewer)$")
    permissions: Optional[List[str]] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    tier: str
    is_active: bool
    admin_email: str
    contact_name: Optional[str]
    contact_phone: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime]
    current_users: int
    max_users: int
    encryption_key_id: Optional[str]


class QuotaStatus(BaseModel):
    tenant_id: str
    quota_type: str
    current_usage: int
    limit: int
    usage_percentage: float
    allowed: bool
    remaining: int


class TenantStatistics(BaseModel):
    tenant_id: str
    name: str
    display_name: str
    tier: str
    is_active: bool
    created_at: str
    last_activity_at: Optional[str]
    quotas: Dict[str, float]
    current_usage: Dict[str, int]
    limits: Dict[str, int]
    security: Dict[str, Any]


# Dependency to get tenant service
async def get_tenant_service(db: AsyncSession = Depends(get_db_session)) -> TenantService:
    return TenantService(db)


# Import tenant context dependencies

# Dependency to validate tenant access

async def validate_tenant_access(request: Request, tenant_id: str):
    """Validate tenant access for the current user."""
    context = await get_current_tenant_context(request)

    # Check if user has access to this tenant
    if not context["is_system_admin"] and context["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )

    return context


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    request: Request,
    tenant_service: TenantService = Depends(get_tenant_service),
    admin_context: dict = Depends(require_admin_access)
):
    """
    Create a new tenant with default configuration.

    Requires system admin privileges.
    """
    try:
        tenant = await tenant_service.create_tenant(
            name=tenant_data.name,
            display_name=tenant_data.display_name,
            admin_email=tenant_data.admin_email,
            tier=tenant_data.tier,
            description=tenant_data.description,
            contact_name=tenant_data.contact_name,
            contact_phone=tenant_data.contact_phone,
            custom_quotas=tenant_data.custom_quotas
        )

        return TenantResponse(
            id=str(tenant.id),
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            tier=tenant.tier,
            is_active=tenant.is_active,
            admin_email=tenant.admin_email,
            contact_name=tenant.contact_name,
            contact_phone=tenant.contact_phone,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            last_activity_at=tenant.last_activity_at,
            current_users=tenant.current_users,
            max_users=tenant.max_users,
            encryption_key_id=tenant.encryption_key_id
        )

    except TenantServiceError as e:
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant"
        )


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    active_only: bool = Query(True, description="Only return active tenants"),
    tier: Optional[str] = Query(
        None, regex="^(free|standard|premium|enterprise)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request: Request,
    tenant_service: TenantService = Depends(get_tenant_service),
    admin_context: dict = Depends(require_admin_access)
):
    """
    List tenants with optional filtering.

    Requires system admin privileges.
    """
    try:
        tenants = await tenant_service.list_tenants(
            active_only=active_only,
            tier=tier,
            limit=limit,
            offset=offset
        )

        return [
            TenantResponse(
                id=str(tenant.id),
                name=tenant.name,
                display_name=tenant.display_name,
                description=tenant.description,
                tier=tenant.tier,
                is_active=tenant.is_active,
                admin_email=tenant.admin_email,
                contact_name=tenant.contact_name,
                contact_phone=tenant.contact_phone,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                last_activity_at=tenant.last_activity_at,
                current_users=tenant.current_users,
                max_users=tenant.max_users,
                encryption_key_id=tenant.encryption_key_id
            )
            for tenant in tenants
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants"
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Get tenant details by ID."""
    try:
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        return TenantResponse(
            id=str(tenant.id),
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            tier=tenant.tier,
            is_active=tenant.is_active,
            admin_email=tenant.admin_email,
            contact_name=tenant.contact_name,
            contact_phone=tenant.contact_phone,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            last_activity_at=tenant.last_activity_at,
            current_users=tenant.current_users,
            max_users=tenant.max_users,
            encryption_key_id=tenant.encryption_key_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant"
        )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Update tenant configuration."""
    try:
        # Convert to dict and remove None values
        updates = {k: v for k, v in tenant_data.dict().items()
                   if v is not None}

        tenant = await tenant_service.update_tenant(tenant_id, updates)

        return TenantResponse(
            id=str(tenant.id),
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            tier=tenant.tier,
            is_active=tenant.is_active,
            admin_email=tenant.admin_email,
            contact_name=tenant.contact_name,
            contact_phone=tenant.contact_phone,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            last_activity_at=tenant.last_activity_at,
            current_users=tenant.current_users,
            max_users=tenant.max_users,
            encryption_key_id=tenant.encryption_key_id
        )

    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    except TenantServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant"
        )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service),
    token: str = Depends(security)  # Requires system admin
):
    """
    Delete a tenant and all associated data.

    Requires system admin privileges.
    """
    try:
        await tenant_service.delete_tenant(tenant_id)

    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    except TenantServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant"
        )


@router.post("/{tenant_id}/users", status_code=status.HTTP_201_CREATED)
async def add_user_to_tenant(
    tenant_id: str,
    user_data: TenantUserAdd,
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Add a user to a tenant with specified role."""
    try:
        tenant_user = await tenant_service.add_user_to_tenant(
            tenant_id=tenant_id,
            user_id=user_data.user_id,
            role=user_data.role,
            permissions=user_data.permissions
        )

        return {
            "id": str(tenant_user.id),
            "tenant_id": str(tenant_user.tenant_id),
            "user_id": str(tenant_user.user_id),
            "role": tenant_user.role,
            "permissions": tenant_user.permissions,
            "is_active": tenant_user.is_active,
            "created_at": tenant_user.created_at.isoformat()
        }

    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except TenantServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user to tenant"
        )


@router.delete("/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_tenant(
    tenant_id: str,
    user_id: str,
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Remove a user from a tenant."""
    try:
        await tenant_service.remove_user_from_tenant(tenant_id, user_id)

    except TenantServiceError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove user from tenant"
        )


@router.get("/{tenant_id}/quotas/{quota_type}", response_model=QuotaStatus)
async def check_quota(
    tenant_id: str,
    quota_type: str,
    requested_amount: int = Query(1, ge=1),
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Check quota status for a specific resource type."""
    try:
        if quota_type not in ["messages", "storage", "api_requests", "ai_requests", "users"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid quota type"
            )

        quota_status = await tenant_service.check_quota(
            tenant_id, quota_type, requested_amount
        )

        return QuotaStatus(**quota_status)

    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    except TenantServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check quota"
        )


@router.post("/{tenant_id}/quotas/{quota_type}/usage")
async def update_quota_usage(
    tenant_id: str,
    quota_type: str,
    amount: int,
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Update quota usage for a tenant."""
    try:
        if quota_type not in ["messages", "storage", "api_requests", "ai_requests"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid quota type"
            )

        success = await tenant_service.update_quota_usage(
            tenant_id, quota_type, amount
        )

        return {"success": success, "updated_quota": quota_type, "amount": amount}

    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    except TenantServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update quota usage"
        )


@router.get("/{tenant_id}/statistics", response_model=TenantStatistics)
async def get_tenant_statistics(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service),
    access: dict = Depends(validate_tenant_access)
):
    """Get comprehensive statistics for a tenant."""
    try:
        stats = await tenant_service.get_tenant_statistics(tenant_id)

        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=stats["error"]
            )

        return TenantStatistics(**stats)

    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant statistics"
        )


@router.post("/{tenant_id}/security/rotate-keys")
async def rotate_tenant_keys(
    tenant_id: str,
    key_type: Optional[str] = Query(
        None, regex="^(data_encryption_key|token_encryption_key)$"),
    security_service: TenantSecurityService = Depends(
        get_tenant_security_service),
    access: dict = Depends(validate_tenant_access)
):
    """Rotate encryption keys for a tenant."""
    try:
        from services.security.types import KeyType

        key_type_enum = None
        if key_type:
            key_type_enum = KeyType.DATA_ENCRYPTION_KEY if key_type == "data_encryption_key" else KeyType.TOKEN_ENCRYPTION_KEY

        results = await security_service.rotate_tenant_keys(tenant_id, key_type_enum)

        return {
            "tenant_id": tenant_id,
            "rotation_results": results,
            "rotated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate tenant keys: {str(e)}"
        )


@router.get("/{tenant_id}/security/status")
async def get_tenant_security_status(
    tenant_id: str,
    security_service: TenantSecurityService = Depends(
        get_tenant_security_service),
    access: dict = Depends(validate_tenant_access)
):
    """Get security status for a tenant."""
    try:
        status_info = await security_service.get_tenant_security_status(tenant_id)
        return status_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant security status: {str(e)}"
        )
