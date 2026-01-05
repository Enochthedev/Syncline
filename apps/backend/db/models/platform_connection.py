"""
Platform Connection Model

Represents authenticated connections to communication platforms.

Credentials are automatically encrypted at rest using Fernet symmetric encryption.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone

from db.base import Base


class PlatformType(str, enum.Enum):
    """Supported communication platforms."""
    GMAIL = "gmail"
    SLACK = "slack"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    TWITTER = "twitter"
    TELEGRAM = "telegram"
    LINKEDIN = "linkedin"
    GOOGLE_CHAT = "google_chat"


class ConnectionStatus(str, enum.Enum):
    """Connection status states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    FAILED = "failed"
    REVOKED = "revoked"


class PlatformConnection(Base):
    """
    Platform connection model for OAuth and authentication.
    
    Attributes:
        user_id: Foreign key to User
        platform: Platform type (gmail, slack, etc.)
        credentials: Encrypted OAuth credentials (JSONB)
        status: Connection status
        last_sync_at: Last successful sync timestamp
        platform_metadata: Additional platform-specific metadata
        user: Related user
        raw_messages: Related raw messages
    """
    
    __tablename__ = "platform_connections"
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Platform information
    platform = Column(
        SQLEnum(PlatformType, name="platform_type"),
        nullable=False,
        index=True
    )
    
    # Encrypted credentials (OAuth tokens, API keys, etc.)
    # Stored as encrypted text using Fernet encryption
    # Decrypted structure: {
    #   "access_token": "...",
    #   "refresh_token": "...",
    #   "expires_at": "...",
    #   "token_type": "Bearer",
    #   ...
    # }
    # NOTE: For backward compatibility, supports both encrypted (Text) and
    # unencrypted (JSONB) formats. New connections use encrypted format.
    _credentials_encrypted = Column("credentials_encrypted", Text, nullable=True)
    _credentials_legacy = Column("credentials", JSONB, nullable=True)
    
    # Connection status
    status = Column(
        SQLEnum(ConnectionStatus, name="connection_status"),
        default=ConnectionStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    # Sync tracking
    last_sync_at = Column(DateTime, nullable=True)

    # Credential rotation tracking
    credentials_rotated_at = Column(DateTime, nullable=True)
    credentials_version = Column(String(50), default="v1", nullable=False)

    # Platform-specific metadata
    # Structure: {
    #   "platform_user_id": "...",
    #   "platform_username": "...",
    #   "scopes": [...],
    #   ...
    # }
    platform_metadata = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="platform_connections")
    raw_messages = relationship(
        "RawMessage",
        back_populates="connection",
        cascade="all, delete-orphan"
    )

    @property
    def credentials(self) -> Dict[str, Any]:
        """
        Get decrypted credentials.

        Automatically decrypts if encrypted format is used, otherwise
        returns legacy JSONB credentials for backward compatibility.

        Returns:
            Dictionary of credentials
        """
        # Try encrypted credentials first (new format)
        if self._credentials_encrypted:
            from services.encryption_service import get_encryption_service
            try:
                return get_encryption_service().decrypt_credentials(
                    self._credentials_encrypted
                )
            except Exception as e:
                # Log error but don't crash - fall through to legacy
                import logging
                logging.warning(
                    f"Failed to decrypt credentials for connection {self.id}: {e}"
                )

        # Fall back to legacy unencrypted JSONB
        if self._credentials_legacy:
            return dict(self._credentials_legacy)

        return {}

    @credentials.setter
    def credentials(self, value: Dict[str, Any]) -> None:
        """
        Set credentials with automatic encryption.

        New credentials are always encrypted. Legacy field is cleared.

        Args:
            value: Dictionary of credentials to encrypt and store
        """
        from services.encryption_service import get_encryption_service

        # Encrypt and store in new format
        self._credentials_encrypted = get_encryption_service().encrypt_credentials(value)

        # Clear legacy field to save space
        self._credentials_legacy = None

    def get_credential(self, key: str, default: Any = None) -> Any:
        """
        Safely get a single credential value.

        Args:
            key: Credential key to retrieve
            default: Default value if key not found

        Returns:
            Credential value or default
        """
        creds = self.credentials
        return creds.get(key, default)

    def migrate_to_encrypted(self) -> bool:
        """
        Migrate legacy unencrypted credentials to encrypted format.

        This is idempotent - safe to call multiple times.

        Returns:
            True if migration occurred, False if already encrypted
        """
        if self._credentials_encrypted:
            return False  # Already encrypted

        if self._credentials_legacy:
            # Migrate by setting through property (triggers encryption)
            self.credentials = dict(self._credentials_legacy)
            return True

        return False

    def rotate_credentials(self, new_credentials: Dict[str, Any]) -> None:
        """
        Rotate credentials with new values.

        This updates the credentials and tracks the rotation timestamp
        and version for audit purposes.

        Args:
            new_credentials: New credential dictionary to encrypt and store

        Example:
            connection.rotate_credentials({
                "access_token": "new_token_123",
                "refresh_token": "new_refresh_456",
                "expires_at": "2025-12-31T23:59:59Z"
            })
        """
        # Update credentials (triggers encryption)
        self.credentials = new_credentials

        # Track rotation
        self.credentials_rotated_at = datetime.now(timezone.utc)

        # Increment version
        if self.credentials_version:
            # Extract version number and increment
            try:
                current_version = int(self.credentials_version.lstrip('v'))
                self.credentials_version = f"v{current_version + 1}"
            except (ValueError, AttributeError):
                self.credentials_version = "v2"
        else:
            self.credentials_version = "v2"

    def needs_rotation(self, max_age_days: int = 90) -> bool:
        """
        Check if credentials need rotation based on age.

        Args:
            max_age_days: Maximum credential age in days before rotation needed

        Returns:
            True if credentials should be rotated

        Example:
            if connection.needs_rotation(max_age_days=30):
                # Rotate credentials
                connection.rotate_credentials(new_creds)
        """
        if not self.credentials_rotated_at:
            # Never rotated - check creation time
            from datetime import timedelta
            age = datetime.now(timezone.utc) - self.created_at
            return age.days > max_age_days

        # Check rotation age
        from datetime import timedelta
        age_since_rotation = datetime.now(timezone.utc) - self.credentials_rotated_at
        return age_since_rotation.days > max_age_days

    def __repr__(self) -> str:
        return f"<PlatformConnection(id={self.id}, platform={self.platform}, status={self.status})>"
