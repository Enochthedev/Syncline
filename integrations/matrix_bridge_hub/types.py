"""
Type definitions for Matrix bridge hub.
"""

import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field


class BridgeType(Enum):
    """Supported Matrix bridge types."""
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"


class BridgeStatus(Enum):
    """Matrix bridge status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class AuthMethod(Enum):
    """Authentication methods for bridges."""
    QR_CODE = "qr_code"
    LOGIN_PASSWORD = "login_password"
    TOKEN = "token"
    OAUTH = "oauth"


@dataclass
class BridgeConfig:
    """Configuration for a Matrix bridge."""
    bridge_type: BridgeType
    bridge_name: str
    executable_path: str
    config_path: str
    database_path: str
    homeserver_url: str
    access_token: str
    user_id: str
    device_id: str
    enabled: bool = True
    auto_restart: bool = True
    restart_delay: int = 5
    max_restart_attempts: int = 3
    environment: Dict[str, str] = field(default_factory=dict)
    extra_args: List[str] = field(default_factory=list)
    auth_method: AuthMethod = AuthMethod.QR_CODE


@dataclass
class BridgeInstance:
    """Runtime instance of a Matrix bridge."""
    config: BridgeConfig
    process: Optional[subprocess.Popen] = None
    status: BridgeStatus = BridgeStatus.STOPPED
    last_status_check: Optional[datetime] = None
    restart_attempts: int = 0
    last_error: Optional[str] = None
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    auth_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QRCodeData:
    """QR code authentication data."""
    qr_code: str
    expires_at: datetime
    bridge_name: str
    auth_url: Optional[str] = None


@dataclass
class BridgeAuthSession:
    """Bridge authentication session."""
    bridge_name: str
    session_id: str
    auth_method: AuthMethod
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    qr_data: Optional[QRCodeData] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MatrixBridgeHubError(Exception):
    """Matrix bridge hub specific errors."""
    pass


class BridgeAuthError(Exception):
    """Bridge authentication specific errors."""
    pass


class BridgeConfigError(Exception):
    """Bridge configuration specific errors."""
    pass
