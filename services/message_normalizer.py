"""
Message normalization service (backward compatibility wrapper).

This module provides backward compatibility imports for the message normalization
functionality that has been reorganized into the services.message package.

For new code, use:
    from services.message import MessageNormalizer, get_message_normalizer

This file maintains backward compatibility for existing imports.
"""

# Import everything from the organized structure for backward compatibility
from .message import (
    MessageNormalizer,
    get_message_normalizer,
    ContentProcessor,
    PlatformHandlerRegistry
)

# Re-export the main classes
__all__ = [
    'MessageNormalizer',
    'get_message_normalizer',
    'ContentProcessor',
    'PlatformHandlerRegistry'
]
