"""
Audit Log Model

The audit trail table. Lives here, with the other models, so Alembic's
autogenerate sees it — it used to be declared inside
`services/audit/audit_logger.py`, where `db.models` never imported it and
`services/retention/data_retention.py` could not import it either.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from db.base import Base


class AuditLog(Base):
    """
    Audit log entry model.

    Tracks all significant actions in the system for compliance and debugging.
    """

    __tablename__ = "audit_logs"

    # User information
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(100), nullable=True)

    # Action details
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True)

    # Status
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)

    # Details
    details = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    # Correlation
    correlation_id = Column(String(100), nullable=True, index=True)
    request_id = Column(String(100), nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )
