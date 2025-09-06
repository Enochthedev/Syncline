"""
Security and OAuth Type Definitions

Defines data models for OAuth flows, security configurations,
and authentication-related structures.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class OAuthConfig(BaseModel):
    """OAuth 2.0 configuration for a platform."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str]
    auth_url: str
    token_url: str
    revoke_url: Optional[str] = None

    # Additional OAuth parameters
    response_type: str = "code"
    access_type: str = "offline"
    prompt: str = "consent"

    # Platform-specific settings
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class OAuthState(BaseModel):
    """OAuth state for CSRF protection."""

    user_id: str
    platform: str
    state: str
    created_at: datetime

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SecurityConfig(BaseModel):
    """Security configuration settings."""

    # Token settings
    token_expiry_minutes: int = 60
    refresh_token_expiry_days: int = 30

    # OAuth settings
    oauth_state_expiry_minutes: int = 10
    csrf_protection_enabled: bool = True

    # Encryption settings
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"

    # Rate limiting
    rate_limit_enabled: bool = True
    max_requests_per_minute: int = 100

    # Session settings
    session_timeout_minutes: int = 480  # 8 hours
    concurrent_sessions_limit: int = 5


class SecurityEvent(BaseModel):
    """Security event for audit logging."""

    event_id: str
    event_type: str
    user_id: Optional[str] = None
    platform: Optional[str] = None
    timestamp: datetime

    # Event details
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    error_message: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuthenticationResult(BaseModel):
    """Result of an authentication attempt."""

    success: bool
    user_id: Optional[str] = None
    platform: Optional[str] = None

    # Token information
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Security context
    requires_mfa: bool = False
    security_warnings: List[str] = Field(default_factory=list)


class PlatformPermissions(BaseModel):
    """Permissions granted by a platform."""

    platform: str
    scopes: List[str]
    granted_at: datetime
    expires_at: Optional[datetime] = None

    # Permission details
    read_permissions: List[str] = Field(default_factory=list)
    write_permissions: List[str] = Field(default_factory=list)
    admin_permissions: List[str] = Field(default_factory=list)

    # User consent
    user_consented: bool = True
    consent_timestamp: Optional[datetime] = None


class SecurityAuditLog(BaseModel):
    """Security audit log entry."""

    log_id: str
    timestamp: datetime
    event_type: str

    # User context
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Request context
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None

    # Security details
    authentication_method: Optional[str] = None
    platform: Optional[str] = None
    success: bool

    # Risk assessment
    risk_level: str = "low"  # low, medium, high, critical
    risk_factors: List[str] = Field(default_factory=list)

    # Additional data
    details: Dict[str, Any] = Field(default_factory=dict)


class TokenValidationResult(BaseModel):
    """Result of token validation."""

    valid: bool
    token_type: str
    platform: Optional[str] = None

    # Token details
    expires_at: Optional[datetime] = None
    scopes: List[str] = Field(default_factory=list)

    # Validation details
    validation_timestamp: datetime
    validation_method: str

    # Issues found
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BiometricAuthConfig(BaseModel):
    """Biometric authentication configuration."""

    enabled: bool = False
    supported_methods: List[str] = Field(
        default_factory=list)  # fingerprint, face_id, voice

    # Security settings
    require_device_lock: bool = True
    fallback_to_password: bool = True
    max_failed_attempts: int = 3

    # Device requirements
    secure_enclave_required: bool = True
    jailbreak_detection_enabled: bool = True


class DeviceSecurityInfo(BaseModel):
    """Device security information."""

    device_id: str
    device_type: str  # ios, android, web

    # Security status
    is_secure: bool
    is_jailbroken: bool = False
    is_rooted: bool = False

    # Security features
    has_secure_enclave: bool = False
    has_biometric_auth: bool = False
    screen_lock_enabled: bool = False

    # Device info
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    last_security_check: Optional[datetime] = None

    # Risk assessment
    security_score: int = 0  # 0-100
    risk_factors: List[str] = Field(default_factory=list)


class PrivacySettings(BaseModel):
    """Privacy and data protection settings."""

    # Data processing
    enable_ai_analysis: bool = True
    enable_pii_redaction: bool = True
    data_minimization: bool = True

    # Data retention
    data_retention_days: int = 365
    auto_delete_enabled: bool = False

    # Data sharing
    allow_analytics: bool = False
    allow_crash_reporting: bool = True
    allow_performance_monitoring: bool = True

    # Compliance
    gdpr_compliance: bool = True
    ccpa_compliance: bool = True

    # User rights
    data_portability_enabled: bool = True
    right_to_deletion_enabled: bool = True
    consent_management_enabled: bool = True


class EncryptionConfig(BaseModel):
    """Encryption configuration settings."""

    # Encryption algorithms
    symmetric_algorithm: str = "AES-256-GCM"
    asymmetric_algorithm: str = "RSA-4096"
    hash_algorithm: str = "SHA-256"

    # Key management
    key_rotation_days: int = 90
    key_derivation_iterations: int = 100000

    # Field-level encryption
    encrypt_tokens: bool = True
    encrypt_messages: bool = True
    encrypt_contacts: bool = True
    encrypt_files: bool = True

    # Transport security
    tls_version: str = "1.3"
    certificate_pinning: bool = True
    hsts_enabled: bool = True


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    # Basic rate limits
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000

    # Burst limits
    burst_size: int = 20
    burst_window_seconds: int = 60

    # Platform-specific limits
    platform_limits: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    # Enforcement
    block_on_limit: bool = True
    retry_after_seconds: int = 60

    # Whitelist/blacklist
    whitelisted_ips: List[str] = Field(default_factory=list)
    blacklisted_ips: List[str] = Field(default_factory=list)


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    # Failure thresholds
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 60

    # Time windows
    failure_window_seconds: int = 300  # 5 minutes
    recovery_timeout_seconds: int = 30

    # Monitoring
    monitor_response_time: bool = True
    slow_response_threshold_ms: int = 5000

    # Fallback behavior
    enable_fallback: bool = True
    fallback_response: Optional[Dict[str, Any]] = None


class SecurityMetrics(BaseModel):
    """Security metrics and monitoring data."""

    # Authentication metrics
    successful_logins: int = 0
    failed_logins: int = 0
    oauth_flows_completed: int = 0
    oauth_flows_failed: int = 0

    # Token metrics
    tokens_issued: int = 0
    tokens_refreshed: int = 0
    tokens_revoked: int = 0
    token_validation_failures: int = 0

    # Security events
    security_incidents: int = 0
    suspicious_activities: int = 0
    blocked_requests: int = 0

    # Platform metrics
    platform_connections: Dict[str, int] = Field(default_factory=dict)
    platform_errors: Dict[str, int] = Field(default_factory=dict)

    # Time period
    period_start: datetime
    period_end: datetime

    # Additional metrics
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)
