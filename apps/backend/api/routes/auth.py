"""
Authentication API Endpoints

Provides authentication and authorization endpoints:
- User registration
- User login
- Token refresh
- Password management
- User profile
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from api.dependencies.auth import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user,
)
from db.models.user import User
from services.auth.jwt_service import get_jwt_service

logger = logging.getLogger(__name__)

router = APIRouter()

__all__ = ["router"]


# =============================================================================
# Request/Response Models
# =============================================================================


class UserRegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")


class UserLoginRequest(BaseModel):
    """User login request."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., description="Refresh token")


class UserResponse(BaseModel):
    """User response model."""

    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    role: str
    permissions: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, description="New password (min 8 characters)"
    )


class UserUpdateRequest(BaseModel):
    """User profile update request."""

    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None


# =============================================================================
# Authentication Endpoints
# =============================================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Register a new user account",
)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    """
    Register a new user.

    Args:
        request: User registration data
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email already exists
    email_query = select(User).where(User.email == request.email)
    email_result = await db.execute(email_query)
    if email_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username already exists
    username_query = select(User).where(User.username == request.username)
    username_result = await db.execute(username_query)
    if username_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Hash password
    jwt_service = get_jwt_service()
    hashed_password = jwt_service.hash_password(request.password)

    # Create user
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role="user",
        permissions=[],
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User registered: {user.username} ({user.email})")

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticate user and get access tokens",
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_database_session),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by username or email
    query = select(User).where(
        (User.username == request.username) | (User.email == request.username)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    jwt_service = get_jwt_service()
    if not jwt_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # Generate tokens
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    refresh_token = jwt_service.create_refresh_token(
        user_id=user.id,
        email=user.email,
    )

    logger.info(f"User logged in: {user.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=jwt_service.access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
    description="Get a new access token using a refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_database_session),
) -> TokenResponse:
    """
    Refresh access token.

    Args:
        request: Refresh token
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    jwt_service = get_jwt_service()

    # Decode refresh token
    claims = jwt_service.verify_token(request.refresh_token)

    if not claims or claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    try:
        user_id = UUID(claims.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    user = await db.get(User, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new tokens
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    new_refresh_token = jwt_service.create_refresh_token(
        user_id=user.id,
        email=user.email,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=jwt_service.access_token_expire_minutes * 60,
    )


# =============================================================================
# User Profile Endpoints
# =============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get current authenticated user's profile",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get current user profile.

    Args:
        current_user: Current authenticated user

    Returns:
        User profile
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update Current User",
    description="Update current user's profile",
)
async def update_current_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    """
    Update current user profile.

    Args:
        request: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user profile

    Raises:
        HTTPException: If email already exists
    """
    # Update fields
    if request.full_name is not None:
        current_user.full_name = request.full_name

    if request.email is not None and request.email != current_user.email:
        # Check if email already exists
        email_query = select(User).where(User.email == request.email)
        email_result = await db.execute(email_query)
        if email_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = request.email

    await db.commit()
    await db.refresh(current_user)

    logger.info(f"User profile updated: {current_user.username}")

    return UserResponse.model_validate(current_user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change Password",
    description="Change current user's password",
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
) -> None:
    """
    Change user password.

    Args:
        request: Password change data
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If current password is incorrect
    """
    jwt_service = get_jwt_service()

    # Verify current password
    if not jwt_service.verify_password(
        request.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    # Hash new password
    current_user.hashed_password = jwt_service.hash_password(request.new_password)

    await db.commit()

    logger.info(f"Password changed for user: {current_user.username}")


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List Users (Admin Only)",
    description="Get list of all users (admin only)",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_database_session),
) -> list[UserResponse]:
    """
    List all users (admin only).

    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        current_user: Current admin user
        db: Database session

    Returns:
        List of users
    """
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get User (Admin Only)",
    description="Get user by ID (admin only)",
)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    """
    Get user by ID (admin only).

    Args:
        user_id: User ID
        current_user: Current admin user
        db: Database session

    Returns:
        User

    Raises:
        HTTPException: If user not found
    """
    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.model_validate(user)
