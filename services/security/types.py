"""
Type definitions for security services.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "AES-256-GCM"
    AES_256_CBC = "AES-256-CBC"


class KeyType(Enum):
    """Types of encryption keys."""
    MASTER_KEY = "master"
    DATA_ENCRYPTION_KEY = "dek"
    TOKEN_ENCRYPTION_KEY = "tek"


class AuditEventType(Enum):
    """Types of audit events."""
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    KEY_ROTATION = "key_rotation"
    TOKEN_ACCESS = "token_access"
    ENCRYPTION_OPERATION = "encryption_operation"
    DECRYPTION_OPERATION = "decryption_operation"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata."""
    key_id: str
    key_type: KeyType
    algorithm: EncryptionAlgorithm
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptedData:
    """Represents encrypted data with metadata."""
    encrypted_value: bytes
    key_id: str
    algorithm: EncryptionAlgorithm
    iv: bytes
    tag: Optional[bytes] = None  # For GCM mode
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenMetadata:
    """Metadata for stored tokens."""
    token_id: str
    platform: str
    user_id: str
    token_type: str  # access_token, refresh_token, etc.
    created_at: datetime
    expires_at: Optional[datetime] = None
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """Represents an audit event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.DATA_ACCESS
    severity: AuditSeverity = AuditSeverity.LOW
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class KeyRotationPolicy:
    """Policy for key rotation."""
    key_type: KeyType
    rotation_interval_days: int
    advance_notice_days: int = 7
    auto_rotate: bool = True
    notification_emails: List[str] = field(default_factory=list)


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    kms_key_id: Optional[str] = None
    encryption_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_rotation_enabled: bool = True
    audit_retention_days: int = 2555  # 7 years for compliance
    pii_encryption_enabled: bool = True
    token_encryption_enabled: bool = True
    immutable_audit_logs: bool = True
