"""
Storage services for blob and attachment management.

This package provides storage backends and managers for handling
file attachments from messages across different platforms.
"""

from .blob_storage import (
    BlobStorageManager,
    get_default_storage_manager,
    BlobStorageError,
    BlobNotFoundError
)
from .backends import (
    BlobStorageClient,
    LocalStorageClient,
    MemoryStorageClient
)

__all__ = [
    "BlobStorageManager",
    "get_default_storage_manager",
    "BlobStorageError",
    "BlobNotFoundError",
    "BlobStorageClient",
    "LocalStorageClient",
    "MemoryStorageClient",
]
