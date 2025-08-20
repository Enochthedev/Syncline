"""
Blob storage integration (backward compatibility wrapper).

This module provides backward compatibility imports for the blob storage
functionality that has been reorganized into the services.storage package.

For new code, use:
    from services.storage import BlobStorageManager, get_default_storage_manager

This file maintains backward compatibility for existing imports.
"""

# Import everything from the organized structure for backward compatibility
from .storage import (
    BlobStorageManager,
    get_default_storage_manager,
    LocalStorageClient,
    S3StorageClient
)

# Re-export the main classes
__all__ = [
    'BlobStorageManager',
    'get_default_storage_manager',
    'LocalStorageClient',
    'S3StorageClient'
]
