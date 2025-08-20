"""
Tenant context middleware for multi-tenant architecture.

This middleware extracts tenant information from JWT tokens or headers
and sets the appropriate database session context.
"""

import logging
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import uuid

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context from requests.

    This middleware:
    1. Extracts tenant information from JWT tokens or headers
    2. Validates tenant access permissions
    3. Sets tenant context for database sessions
    4. Handles system admin privileges
    """

    def __init__(self, app, jwt_secret: Optional[str] = None):
        super().__init__(app)
        # TODO: Use proper secret from config
        self.jwt_secret = jwt_secret or "your-secret-key"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set tenant context."""
        try:
            # Extract tenant context from request
            tenant_context = await self._extract_tenant_context(request)

            # Set tenant context in request state
            request.state.tenant_id = tenant_context.get("tenant_id")
            request.state.user_id = tenant_context.get("user_id")
            request.state.is_system_admin = tenant_context.get(
                "is_system_admin", False)
            request.state.user_roles = tenant_context.get("roles", [])

            # Process the request
            response = await call_next(request)

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant context middleware error: {e}")
            # Continue without tenant context for public endpoints
            request.state.tenant_id = None
            request.state.user_id = None
            request.state.is_system_admin = False
            request.state.user_roles = []

            response = await call_next(request)
            return response

    async def _extract_tenant_context(self, request: Request) -> dict:
        """
        Extract tenant context from JWT token or headers.

        Args:
            request: FastAPI request object

        Returns:
            Dictionary with tenant context information
        """
        # Try to get tenant context from JWT token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token, self.jwt_secret, algorithms=["HS256"])
                return {
                    "tenant_id": payload.get("tenant_id"),
                    "user_id": payload.get("user_id"),
                    "is_system_admin": payload.get("is_system_admin", False),
                    "roles": payload.get("roles", [])
                }
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {e}")
                # Continue to check headers

        # Try to get tenant context from headers (for development/testing)
        tenant_id = request.headers.get("x-tenant-id")
        user_id = request.headers.get("x-user-id")
        is_system_admin = request.headers.get(
            "x-system-admin", "false").lower() == "true"

        # Validate tenant_id format if provided
        if tenant_id:
            try:
                uuid.UUID(tenant_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tenant ID format"
                )

        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "is_system_admin": is_system_admin,
            "roles": []
        }


def get_tenant_context(request: Request) -> dict:
    """
    Get tenant context from request state.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with tenant context
    """
    return {
        "tenant_id": getattr(request.state, "tenant_id", None),
        "user_id": getattr(request.state, "user_id", None),
        "is_system_admin": getattr(request.state, "is_system_admin", False),
        "roles": getattr(request.state, "user_roles", [])
    }


def require_tenant_context(request: Request) -> dict:
    """
    Require tenant context to be present in request.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with tenant context

    Raises:
        HTTPException: If tenant context is missing
    """
    context = get_tenant_context(request)

    if not context["tenant_id"] and not context["is_system_admin"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required"
        )

    return context


def require_system_admin(request: Request) -> dict:
    """
    Require system admin privileges.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with tenant context

    Raises:
        HTTPException: If not system admin
    """
    context = get_tenant_context(request)

    if not context["is_system_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin privileges required"
        )

    return context


def check_tenant_access(request: Request, required_tenant_id: str) -> bool:
    """
    Check if user has access to a specific tenant.

    Args:
        request: FastAPI request object
        required_tenant_id: Tenant ID to check access for

    Returns:
        True if access is allowed
    """
    context = get_tenant_context(request)

    # System admin has access to all tenants
    if context["is_system_admin"]:
        return True

    # User must have matching tenant ID
    return context["tenant_id"] == required_tenant_id


# FastAPI dependencies
async def get_current_tenant_context(request: Request) -> dict:
    """FastAPI dependency to get current tenant context."""
    return get_tenant_context(request)


async def require_tenant_access(request: Request) -> dict:
    """FastAPI dependency that requires tenant context."""
    return require_tenant_context(request)


async def require_admin_access(request: Request) -> dict:
    """FastAPI dependency that requires system admin access."""
    return require_system_admin(request)


class TenantAccessValidator:
    """
    Validator for tenant-specific access control.

    This class provides methods to validate tenant access
    and enforce security policies.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def validate_tenant_access(
        self,
        request: Request,
        tenant_id: str,
        required_role: Optional[str] = None
    ) -> bool:
        """
        Validate if user has access to a tenant with optional role requirement.

        Args:
            request: FastAPI request object
            tenant_id: Tenant ID to validate access for
            required_role: Required role (admin, member, viewer)

        Returns:
            True if access is valid
        """
        context = get_tenant_context(request)

        # System admin bypasses all checks
        if context["is_system_admin"]:
            return True

        # Check tenant access
        if not check_tenant_access(request, tenant_id):
            return False

        # Check role requirement if specified
        if required_role:
            user_roles = context.get("roles", [])
            if required_role not in user_roles and "admin" not in user_roles:
                return False

        return True

    async def validate_resource_access(
        self,
        request: Request,
        resource_tenant_id: str,
        action: str = "read"
    ) -> bool:
        """
        Validate access to a specific resource.

        Args:
            request: FastAPI request object
            resource_tenant_id: Tenant ID that owns the resource
            action: Action being performed (read, write, delete)

        Returns:
            True if access is valid
        """
        context = get_tenant_context(request)

        # System admin has full access
        if context["is_system_admin"]:
            return True

        # User must belong to the same tenant as the resource
        if context["tenant_id"] != resource_tenant_id:
            self.logger.warning(
                f"Cross-tenant access attempt: user_tenant={context['tenant_id']}, "
                f"resource_tenant={resource_tenant_id}, action={action}"
            )
            return False

        # TODO: Implement fine-grained permission checking based on action
        return True


# Global validator instance
tenant_validator = TenantAccessValidator()
