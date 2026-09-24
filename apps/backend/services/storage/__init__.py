"""
Storage services for blob and attachment management.

This package provides storage backends and managers for handling
file attachments from messages across different platforms.
"""

from .backends import BlobStorageClient, LocalStorageClient, MemoryStorageClient
from .blob_storage import (
    BlobNotFoundError,
    BlobStorageError,
    BlobStorageManager,
    get_default_storage_manager,
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
