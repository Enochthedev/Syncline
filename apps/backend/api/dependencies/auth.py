"""
Authentication Dependencies

Provides FastAPI dependencies for authentication and authorization:
- JWT token validation
- User extraction from token
- Role-based access control
- Permission checking
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from db.models.user import User
from services.auth.jwt_service import get_jwt_service

logger = logging.getLogger(__name__)

# Security scheme for JWT bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database_session),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    jwt_service = get_jwt_service()
    claims = jwt_service.verify_token(token)

    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if claims.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    try:
        user_id = UUID(claims.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    Args:
        current_user: Current user from token

    Returns:
        Current active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current user if they are an admin.

    Args:
        current_user: Current user from token

    Returns:
        Current user if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.

    Args:
        *allowed_roles: Roles that are allowed access

    Returns:
        Dependency function that checks user role

    Example:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint():
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


def require_permission(*required_permissions: str):
    """
    Dependency factory for permission-based access control.

    Args:
        *required_permissions: Permissions required for access

    Returns:
        Dependency function that checks user permissions

    Example:
        @router.post(
            "/messages",
            dependencies=[Depends(require_permission("messages:write"))]
        )
        async def create_message():
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Admin has all permissions
        if current_user.role == "admin":
            return current_user

        # Check user permissions
        user_permissions = current_user.permissions or []

        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permission: {permission}"
                )

        return current_user

    return permission_checker


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_database_session),
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.

    Args:
        credentials: Optional HTTP authorization credentials
        db: Database session

    Returns:
        Current user or None
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_optional_current_user",
    "require_role",
    "require_permission",
    "security",
]
