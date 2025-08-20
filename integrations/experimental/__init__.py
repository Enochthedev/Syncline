"""
Experimental platform connectors package.

This package contains experimental connectors for platforms that are in development
or proof-of-concept stage. These connectors have limited functionality and may not
be production-ready.
"""

from .base_experimental import (
    ExperimentalConnector,
    ExperimentalStatus,
    ExperimentalCapabilities,
    ExperimentalError,
    UnsupportedFeatureError,
    APILimitationError
)
from .tiktok_connector import TikTokConnector
from .snapchat_connector import SnapchatConnector
from .framework import ExperimentalFramework

__all__ = [
    'ExperimentalConnector',
    'ExperimentalStatus',
    'ExperimentalCapabilities',
    'ExperimentalError',
    'UnsupportedFeatureError',
    'APILimitationError',
    'TikTokConnector',
    'SnapchatConnector',
    'ExperimentalFramework'
]
