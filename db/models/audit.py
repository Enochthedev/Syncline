"""
Audit log database model for security and compliance tracking.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from ..base import Base


class AuditLog(Base):
    """
    Audit log model for tracking all security-related operations.

    This model stores immutable audit records with integrity hashes
    for compliance and security monitoring.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event identification
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)

    # Tenant and user information
    tenant_id = Column(UUID(as_uuid=True), nullable=True,
                       index=True)  # Multi-tenant isolation
    user_id = Column(String(255), nullable=True, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)

    # Event metadata
    severity = Column(String(20), nullable=False, default="low", index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    details = Column(JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Operation result
    success = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)

    # Integrity and compliance
    integrity_hash = Column(String(64), nullable=False)  # SHA-256 hash

    def __repr__(self):
        return (
            f"<AuditLog(event_id='{self.event_id}', "
            f"event_type='{self.event_type}', "
            f"action='{self.action}', "
            f"timestamp='{self.timestamp}')>"
        )
