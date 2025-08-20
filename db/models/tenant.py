"""
Tenant model for multi-tenant architecture.

This model provides tenant isolation and management capabilities
with support for quotas, encryption keys, and resource limits.
"""

import uuid
from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


class Tenant(Base):
    """
    Tenant model for multi-tenant architecture.

    Provides tenant isolation, quotas, and configuration management.
    """
    __tablename__ = "tenants"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tenant identification
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(500), nullable=False)
    description = Column(Text)

    # Status and configuration
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    # free, standard, premium, enterprise
    tier = Column(String(50), default="standard", nullable=False)

    # Contact information
    admin_email = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    contact_phone = Column(String(50))

    # Quotas and limits
    max_users = Column(Integer, default=10)
    max_messages_per_month = Column(Integer, default=100000)
    max_storage_gb = Column(Integer, default=10)
    max_api_requests_per_hour = Column(Integer, default=1000)
    max_ai_requests_per_day = Column(Integer, default=1000)

    # Current usage (updated by background jobs)
    current_users = Column(Integer, default=0)
    current_messages_this_month = Column(Integer, default=0)
    current_storage_gb = Column(Integer, default=0)
    current_api_requests_this_hour = Column(Integer, default=0)
    current_ai_requests_today = Column(Integer, default=0)

    # Security settings
    encryption_key_id = Column(String(255))  # Tenant-specific encryption key
    data_retention_days = Column(Integer, default=365)
    pii_redaction_enabled = Column(Boolean, default=True)
    audit_logging_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime(timezone=True))

    # Metadata
    settings = Column(JSON, default=dict)  # Tenant-specific settings
    tenant_metadata = Column(JSON, default=dict)  # Additional metadata

    # Relationships
    users = relationship("TenantUser", back_populates="tenant",
                         cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_tenants_tier_active', 'tier', 'is_active'),
        Index('ix_tenants_created_at', 'created_at'),
        Index('ix_tenants_last_activity', 'last_activity_at'),
    )

    def __repr__(self):
        return f"<Tenant(id='{self.id}', name='{self.name}', tier='{self.tier}')>"

    def is_quota_exceeded(self, quota_type: str) -> bool:
        """Check if a specific quota is exceeded."""
        quota_checks = {
            'users': self.current_users >= self.max_users,
            'messages': self.current_messages_this_month >= self.max_messages_per_month,
            'storage': self.current_storage_gb >= self.max_storage_gb,
            'api_requests': self.current_api_requests_this_hour >= self.max_api_requests_per_hour,
            'ai_requests': self.current_ai_requests_today >= self.max_ai_requests_per_day,
        }
        return quota_checks.get(quota_type, False)

    def get_quota_usage_percentage(self, quota_type: str) -> float:
        """Get quota usage as a percentage."""
        usage_calculations = {
            'users': (self.current_users / max(self.max_users, 1)) * 100,
            'messages': (self.current_messages_this_month / max(self.max_messages_per_month, 1)) * 100,
            'storage': (self.current_storage_gb / max(self.max_storage_gb, 1)) * 100,
            'api_requests': (self.current_api_requests_this_hour / max(self.max_api_requests_per_hour, 1)) * 100,
            'ai_requests': (self.current_ai_requests_today / max(self.max_ai_requests_per_day, 1)) * 100,
        }
        return min(usage_calculations.get(quota_type, 0), 100.0)


class TenantUser(Base):
    """
    Association between tenants and users with role-based access.
    """
    __tablename__ = "tenant_users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Role and permissions
    role = Column(String(50), default="member",
                  nullable=False)  # admin, member, viewer
    permissions = Column(JSON, default=list)  # Specific permissions

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", back_populates="tenant_memberships")

    __table_args__ = (
        Index('ix_tenant_users_tenant_id', 'tenant_id'),
        Index('ix_tenant_users_user_id', 'user_id'),
        Index('ix_tenant_users_role', 'role'),
        Index('ix_tenant_users_active', 'is_active'),
    )

    def __repr__(self):
        return f"<TenantUser(tenant_id='{self.tenant_id}', user_id='{self.user_id}', role='{self.role}')>"


class TenantQuotaUsage(Base):
    """
    Historical quota usage tracking for analytics and billing.
    """
    __tablename__ = "tenant_quota_usage"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Usage metrics
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Usage counts
    messages_processed = Column(Integer, default=0)
    storage_used_gb = Column(Integer, default=0)
    api_requests_made = Column(Integer, default=0)
    ai_requests_made = Column(Integer, default=0)
    active_users = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index('ix_quota_usage_tenant_period',
              'tenant_id', 'period_start', 'period_end'),
        Index('ix_quota_usage_period_start', 'period_start'),
    )

    def __repr__(self):
        return f"<TenantQuotaUsage(tenant_id='{self.tenant_id}', period='{self.period_start}' to '{self.period_end}')>"
