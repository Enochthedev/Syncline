"""
Matrix bridge hub for managing multiple Matrix bridges.

This package provides a unified interface for managing multiple Matrix bridges
including WhatsApp (mautrix-whatsapp), Instagram/Facebook Messenger (mautrix-meta),
and other mautrix-based integrations.
"""

from .hub import MatrixBridgeHub
from .bridge_manager import BridgeManager
from .auth_manager import MatrixAuthManager
from .types import BridgeType, BridgeStatus, BridgeConfig, BridgeInstance, AuthMethod

__all__ = [
    'MatrixBridgeHub',
    'BridgeManager',
    'MatrixAuthManager',
    'BridgeType',
    'BridgeStatus',
    'BridgeConfig',
    'BridgeInstance',
    'AuthMethod'
]
