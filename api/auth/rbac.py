"""Role-Based Access Control (RBAC) implementation."""

import logging
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import User, Role, Permission

logger = logging.getLogger(__name__)


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_role(self, name: str, description: str = None, tenant_id: str = "default") -> Role:
        """Create a new role."""
        role = Role(
            name=name,
            description=description,
            tenant_id=tenant_id
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def create_permission(self, name: str, resource: str, action: str, description: str = None) -> Permission:
        """Create a new permission."""
        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description
        )
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Assign a role to a user."""
        try:
            # Get user and role
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()

            role_result = await self.db.execute(
                select(Role).where(Role.id == role_id)
            )
            role = role_result.scalar_one_or_none()

            if not user or not role:
                return False

            # Check if role is already assigned
            if role not in user.roles:
                user.roles.append(role)
                await self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Error assigning role to user: {e}")
            await self.db.rollback()
            return False

    async def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """Assign a permission to a role."""
        try:
            # Get role and permission
            role_result = await self.db.execute(
                select(Role).where(Role.id == role_id)
            )
            role = role_result.scalar_one_or_none()

            permission_result = await self.db.execute(
                select(Permission).where(Permission.id == permission_id)
            )
            permission = permission_result.scalar_one_or_none()

            if not role or not permission:
                return False

            # Check if permission is already assigned
            if permission not in role.permissions:
                role.permissions.append(permission)
                await self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Error assigning permission to role: {e}")
            await self.db.rollback()
            return False

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user."""
        try:
            result = await self.db.execute(
                select(User)
                .options(selectinload(User.roles).selectinload(Role.permissions))
                .where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return []

            permissions = set()
            for role in user.roles:
                for permission in role.permissions:
                    permissions.add(
                        f"{permission.resource}:{permission.action}")

            return list(permissions)

        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return []

    async def check_user_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has specific permission."""
        permissions = await self.get_user_permissions(user_id)
        required_permission = f"{resource}:{action}"
        return required_permission in permissions

    async def initialize_default_roles_and_permissions(self):
        """Initialize default roles and permissions."""
        try:
            # Create default permissions
            permissions_data = [
                ("messages:read", "messages", "read", "Read messages"),
                ("messages:write", "messages", "write", "Write messages"),
                ("messages:delete", "messages", "delete", "Delete messages"),
                ("threads:read", "threads", "read", "Read threads"),
                ("threads:write", "threads", "write", "Write threads"),
                ("threads:delete", "threads", "delete", "Delete threads"),
                ("participants:read", "participants", "read", "Read participants"),
                ("participants:write", "participants",
                 "write", "Write participants"),
                ("search:read", "search", "read", "Perform searches"),
                ("summaries:read", "summaries", "read", "Read summaries"),
                ("summaries:write", "summaries", "write", "Generate summaries"),
                ("contact_dossiers:read", "contact_dossiers",
                 "read", "Read contact dossiers"),
                ("contact_dossiers:write", "contact_dossiers",
                 "write", "Write contact dossiers"),
                ("file_references:read", "file_references",
                 "read", "Read file references"),
                ("admin:read", "admin", "read", "Admin read access"),
                ("admin:write", "admin", "write", "Admin write access"),
            ]

            created_permissions = {}
            for name, resource, action, description in permissions_data:
                # Check if permission already exists
                result = await self.db.execute(
                    select(Permission).where(Permission.name == name)
                )
                permission = result.scalar_one_or_none()

                if not permission:
                    permission = await self.create_permission(name, resource, action, description)

                created_permissions[name] = permission

            # Create default roles
            roles_data = [
                ("admin", "Administrator with full access", [
                    "messages:read", "messages:write", "messages:delete",
                    "threads:read", "threads:write", "threads:delete",
                    "participants:read", "participants:write",
                    "search:read", "summaries:read", "summaries:write",
                    "contact_dossiers:read", "contact_dossiers:write",
                    "file_references:read", "admin:read", "admin:write"
                ]),
                ("user", "Regular user with read access", [
                    "messages:read", "threads:read", "participants:read",
                    "search:read", "summaries:read", "contact_dossiers:read",
                    "file_references:read"
                ]),
                ("api_user", "API user with search and read access", [
                    "messages:read", "threads:read", "participants:read",
                    "search:read", "summaries:read", "contact_dossiers:read",
                    "file_references:read"
                ]),
                ("analyst", "Analyst with extended read access", [
                    "messages:read", "threads:read", "participants:read",
                    "search:read", "summaries:read", "summaries:write",
                    "contact_dossiers:read", "contact_dossiers:write",
                    "file_references:read"
                ])
            ]

            for role_name, role_description, permission_names in roles_data:
                # Check if role already exists
                result = await self.db.execute(
                    select(Role).where(Role.name == role_name)
                )
                role = result.scalar_one_or_none()

                if not role:
                    role = await self.create_role(role_name, role_description)

                # Assign permissions to role
                for permission_name in permission_names:
                    if permission_name in created_permissions:
                        await self.assign_permission_to_role(
                            str(role.id),
                            str(created_permissions[permission_name].id)
                        )

            logger.info(
                "Default roles and permissions initialized successfully")

        except Exception as e:
            logger.error(
                f"Error initializing default roles and permissions: {e}")
            await self.db.rollback()
            raise


async def check_permission(user: User, resource: str, action: str) -> bool:
    """Check if user has permission for resource and action."""
    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Check user roles and permissions
    for role in user.roles:
        for permission in role.permissions:
            if permission.resource == resource and permission.action == action:
                return True

    return False


def require_permission(resource: str, action: str):
    """Decorator to require specific permission."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs or function signature
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if not await check_permission(current_user, resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {resource}:{action}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
