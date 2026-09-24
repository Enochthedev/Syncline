"""
User Model

Represents system users who own platform connections and messages.
"""

from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from db.base import Base


class User(Base):
    """
    User model for authentication and ownership.

    Attributes:
        email: User's email address (unique)
        username: User's username (unique)
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        is_active: Whether the user account is active
        is_superuser: Whether the user has admin privileges
        platform_connections: Related platform connections
    """

    __tablename__ = "users"

    # User credentials
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # User profile
    full_name = Column(String(255), nullable=True)

    # User status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Role-based access control
    role = Column(String(50), default="user", nullable=False, index=True)
    permissions = Column(ARRAY(String), default=list, nullable=True)

    # Relationships
    platform_connections = relationship(
        "PlatformConnection", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
