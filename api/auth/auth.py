"""Authentication utilities and dependencies."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import jwt
import hashlib
import secrets

from config.config import settings
from db.session import get_db
from .models import User, APIKey

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# JWT settings
SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY',
                     'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


class AuthorizationError(Exception):
    """Custom authorization error."""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid token")


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID with roles and permissions."""
    try:
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {e}")
        return None


async def get_user_by_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """Get user by API key."""
    try:
        key_hash = hash_api_key(api_key)
        result = await db.execute(
            select(APIKey)
            .where(APIKey.key_hash == key_hash)
            .where(APIKey.is_active == True)
            .where(APIKey.expires_at > datetime.utcnow())
        )
        api_key_obj = result.scalar_one_or_none()

        if not api_key_obj:
            return None

        # Update last used timestamp
        api_key_obj.last_used_at = datetime.utcnow()
        api_key_obj.total_requests += 1
        await db.commit()

        # Get user
        return await get_user_by_id(db, str(api_key_obj.user_id))

    except Exception as e:
        logger.error(f"Error getting user by API key: {e}")
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from JWT token or API key."""

    # Try API key first (from header)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        user = await get_user_by_api_key(db, api_key)
        if user and user.is_active:
            return user

    # Try JWT token
    if credentials:
        try:
            payload = verify_token(credentials.credentials)
            user_id = payload.get("sub")
            if user_id:
                user = await get_user_by_id(db, user_id)
                if user and user.is_active:
                    return user
        except AuthenticationError:
            pass

    # For development, allow requests without authentication
    if getattr(settings, 'DEBUG', False):
        # Create a default user for development
        return User(
            id="00000000-0000-0000-0000-000000000000",
            username="dev_user",
            email="dev@example.com",
            full_name="Development User",
            is_active=True,
            is_superuser=True,
            tenant_id="default"
        )

    return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user or raise authentication error."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return current_user


def verify_permissions(required_permissions: list):
    """Decorator to verify user permissions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs or dependencies
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check if user is superuser (has all permissions)
            if current_user.is_superuser:
                return await func(*args, **kwargs)

            # Check specific permissions
            user_permissions = set()
            for role in current_user.roles:
                for permission in role.permissions:
                    user_permissions.add(
                        f"{permission.resource}:{permission.action}")

            for required_permission in required_permissions:
                if required_permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {required_permission}"
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
