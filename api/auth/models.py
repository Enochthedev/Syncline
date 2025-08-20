"""Authentication and authorization models."""

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey(
        'auth_users.id', ondelete='CASCADE')),
    Column('role_id', UUID(as_uuid=True), ForeignKey(
        'auth_roles.id', ondelete='CASCADE'))
)

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey(
        'auth_roles.id', ondelete='CASCADE')),
    Column('permission_id', UUID(as_uuid=True), ForeignKey(
        'auth_permissions.id', ondelete='CASCADE'))
)


class User(Base):
    """User model for authentication."""
    __tablename__ = "auth_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Status fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Multi-tenant support
    tenant_id = Column(String(255), nullable=False,
                       default="default", index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # API key for programmatic access
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    api_key_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")


class Role(Base):
    """Role model for RBAC."""
    __tablename__ = "auth_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Multi-tenant support
    tenant_id = Column(String(255), nullable=False,
                       default="default", index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    """Permission model for RBAC."""
    __tablename__ = "auth_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    # e.g., "messages", "threads", "search"
    resource = Column(String(100), nullable=False)
    # e.g., "read", "write", "delete"
    action = Column(String(50), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, nullable=False)

    # Relationships
    roles = relationship("Role", secondary=role_permissions,
                         back_populates="permissions")


class APIKey(Base):
    """API key model for programmatic access."""
    __tablename__ = "auth_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Owner
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        'auth_users.id', ondelete='CASCADE'), nullable=False)

    # Status and limits
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=100, nullable=False)
    rate_limit_per_hour = Column(Integer, default=1000, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    total_requests = Column(Integer, default=0, nullable=False)


class UserRole(Base):
    """Extended user-role relationship with additional metadata."""
    __tablename__ = "auth_user_roles_extended"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        'auth_users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey(
        'auth_roles.id', ondelete='CASCADE'), nullable=False)

    # Additional metadata
    granted_by = Column(UUID(as_uuid=True), ForeignKey(
        'auth_users.id'), nullable=True)
    granted_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
