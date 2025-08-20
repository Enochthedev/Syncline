import uuid
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255))
    last_name = Column(String(255))
    email = Column(String(255), unique=True, nullable=False, index=True)

    # Authentication and status
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_admin = Column(Boolean, default=False, nullable=False)

    # Profile information
    avatar_url = Column(String(1000))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True),
                        default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))

    # Metadata
    preferences = Column(JSON, default=dict)
    user_metadata = Column(JSON, default=dict)

    # Relationships
    tenant_memberships = relationship("TenantUser", back_populates="user")

    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_active', 'is_active'),
        Index('ix_users_system_admin', 'is_system_admin'),
    )

    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"
