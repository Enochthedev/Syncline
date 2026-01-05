"""
FastAPI Dependency Injection

Provides reusable dependencies for:
- Database sessions
- Redis connections
- Authentication
- Configuration
- Service instances
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import Settings, settings
from db.session import get_db


# =============================================================================
# Database Dependencies
# =============================================================================

async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database session.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_database_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async for session in get_db():
        yield session


# =============================================================================
# Configuration Dependencies
# =============================================================================

def get_settings() -> Settings:
    """
    Dependency for application settings.
    
    Returns:
        Settings: Application configuration
        
    Example:
        @app.get("/config")
        async def get_config(config: Settings = Depends(get_settings)):
            return {"environment": config.ENV}
    """
    return settings


# =============================================================================
# Redis Dependencies (TODO)
# =============================================================================

# async def get_redis_client() -> AsyncGenerator[Redis, None]:
#     """
#     Dependency for Redis client.
#     
#     Yields:
#         Redis: Redis client instance
#     """
#     # TODO: Implement Redis client dependency
#     pass


# =============================================================================
# Event Bus Dependencies (TODO)
# =============================================================================

# async def get_event_bus() -> EventBus:
#     """
#     Dependency for event bus.
#     
#     Returns:
#         EventBus: Event bus instance
#     """
#     # TODO: Implement event bus dependency
#     pass


# =============================================================================
# Authentication Dependencies (TODO)
# =============================================================================

# async def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     db: AsyncSession = Depends(get_database_session)
# ) -> User:
#     """
#     Dependency for current authenticated user.
#     
#     Args:
#         token: JWT token from request
#         db: Database session
#         
#     Returns:
#         User: Current authenticated user
#         
#     Raises:
#         HTTPException: If authentication fails
#     """
#     # TODO: Implement JWT authentication
#     pass


# async def require_admin(
#     current_user: User = Depends(get_current_user)
# ) -> User:
#     """
#     Dependency that requires admin role.
#     
#     Args:
#         current_user: Current authenticated user
#         
#     Returns:
#         User: Current user if admin
#         
#     Raises:
#         HTTPException: If user is not admin
#     """
#     # TODO: Implement role-based access control
#     pass


# =============================================================================
# Service Dependencies (TODO)
# =============================================================================

# async def get_collection_service(
#     db: AsyncSession = Depends(get_database_session)
# ) -> CollectionService:
#     """
#     Dependency for collection service.
#     
#     Args:
#         db: Database session
#         
#     Returns:
#         CollectionService: Collection service instance
#     """
#     # TODO: Implement collection service dependency
#     pass


# async def get_ai_service(
#     db: AsyncSession = Depends(get_database_session)
# ) -> AIService:
#     """
#     Dependency for AI service.
#     
#     Args:
#         db: Database session
#         
#     Returns:
#         AIService: AI service instance
#     """
#     # TODO: Implement AI service dependency
#     pass


# =============================================================================
# Pagination Dependencies
# =============================================================================

class PaginationParams:
    """
    Pagination parameters for list endpoints.
    
    Attributes:
        skip: Number of records to skip
        limit: Maximum number of records to return
    """
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
    ):
        """
        Initialize pagination parameters.
        
        Args:
            skip: Number of records to skip (default: 0)
            limit: Maximum number of records to return (default: 100, max: 1000)
        """
        self.skip = max(0, skip)
        self.limit = min(1000, max(1, limit))


def get_pagination_params(
    skip: int = 0,
    limit: int = 100,
) -> PaginationParams:
    """
    Dependency for pagination parameters.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        PaginationParams: Pagination parameters
        
    Example:
        @app.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(get_pagination_params)
        ):
            return {"skip": pagination.skip, "limit": pagination.limit}
    """
    return PaginationParams(skip=skip, limit=limit)


# =============================================================================
# Validation Dependencies
# =============================================================================

def validate_uuid(uuid_str: str) -> str:
    """
    Validate UUID format.
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        str: Validated UUID string
        
    Raises:
        HTTPException: If UUID is invalid
    """
    import uuid
    
    try:
        uuid.UUID(uuid_str)
        return uuid_str
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {uuid_str}"
        )


# =============================================================================
# Export all dependencies
# =============================================================================

__all__ = [
    "get_database_session",
    "get_settings",
    "get_pagination_params",
    "validate_uuid",
    "PaginationParams",
]
