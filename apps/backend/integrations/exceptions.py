"""
Custom Exception Types for WhatsApp Integration

Provides granular error types for better error handling and debugging.
"""

from typing import Any, Dict, Optional


class WhatsAppError(Exception):
    """
    Base exception for all WhatsApp integration errors.

    All WhatsApp-specific exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        connection_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize WhatsApp error.

        Args:
            message: Human-readable error message
            connection_id: Optional connection UUID
            details: Optional dict with additional error context
        """
        super().__init__(message)
        self.message = message
        self.connection_id = connection_id
        self.details = details or {}

    def __str__(self) -> str:
        """String representation with context."""
        parts = [self.message]
        if self.connection_id:
            parts.append(f"(connection_id={self.connection_id})")
        if self.details:
            parts.append(f"details={self.details}")
        return " ".join(parts)


class BridgeError(WhatsAppError):
    """
    Error communicating with Matrix/WhatsApp bridge.

    Raised when the bridge is unreachable or returns an error.
    """

    def __init__(self, message: str, bridge_command: Optional[str] = None, **kwargs):
        """
        Initialize bridge error.

        Args:
            message: Error message
            bridge_command: The bridge command that failed (e.g., "login", "logout")
            **kwargs: Additional context passed to WhatsAppError
        """
        super().__init__(message, **kwargs)
        self.bridge_command = bridge_command


class BridgeTimeoutError(BridgeError):
    """
    Timeout waiting for bridge response.

    Raised when bridge doesn't respond within expected timeframe.
    """

    def __init__(
        self,
        message: str = "Bridge response timed out",
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        """
        Initialize bridge timeout error.

        Args:
            message: Error message
            timeout_seconds: How long we waited before timing out
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds


class RoomNotFoundError(WhatsAppError):
    """
    Matrix room not found.

    Raised when expected Matrix room doesn't exist or isn't accessible.
    """

    def __init__(
        self,
        message: str = "Matrix room not found",
        room_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize room not found error.

        Args:
            message: Error message
            room_id: The Matrix room ID that wasn't found
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.room_id = room_id


class AuthenticationError(WhatsAppError):
    """
    WhatsApp authentication failed.

    Raised when login fails or session is invalid.
    """

    def __init__(
        self,
        message: str = "WhatsApp authentication failed",
        phone_number: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize authentication error.

        Args:
            message: Error message
            phone_number: Phone number that failed to authenticate (sanitized)
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.phone_number = phone_number


class SessionExpiredError(AuthenticationError):
    """
    WhatsApp session has expired.

    Raised when a previously valid session is no longer active.
    """

    pass


class QRCodeError(WhatsAppError):
    """
    QR code generation or scanning failed.

    Raised when QR code cannot be generated or has expired.
    """

    def __init__(self, message: str = "QR code error", expired: bool = False, **kwargs):
        """
        Initialize QR code error.

        Args:
            message: Error message
            expired: Whether the QR code expired
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.expired = expired


class MessageSendError(WhatsAppError):
    """
    Failed to send WhatsApp message.

    Raised when message sending fails.
    """

    def __init__(
        self,
        message: str = "Failed to send message",
        recipient: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize message send error.

        Args:
            message: Error message
            recipient: Message recipient (sanitized)
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.recipient = recipient


class MessageSyncError(WhatsAppError):
    """
    Failed to sync messages from WhatsApp.

    Raised when message synchronization fails.
    """

    def __init__(
        self,
        message: str = "Failed to sync messages",
        sync_type: Optional[str] = None,  # "full", "incremental", etc.
        **kwargs,
    ):
        """
        Initialize message sync error.

        Args:
            message: Error message
            sync_type: Type of sync that failed
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.sync_type = sync_type


class ConfigurationError(WhatsAppError):
    """
    Invalid WhatsApp configuration.

    Raised when required configuration is missing or invalid.
    """

    def __init__(
        self,
        message: str = "Invalid WhatsApp configuration",
        config_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: The configuration key that's invalid
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.config_key = config_key


class RateLimitError(WhatsAppError):
    """
    Rate limit exceeded.

    Raised when too many requests are made to WhatsApp/bridge.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,  # Seconds until retry allowed
        **kwargs,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConnectionError(WhatsAppError):
    """
    Network connection error.

    Raised when network connection to Matrix/WhatsApp fails.
    """

    def __init__(
        self, message: str = "Connection failed", host: Optional[str] = None, **kwargs
    ):
        """
        Initialize connection error.

        Args:
            message: Error message
            host: The host that couldn't be reached
            **kwargs: Additional context
        """
        super().__init__(message, **kwargs)
        self.host = host
