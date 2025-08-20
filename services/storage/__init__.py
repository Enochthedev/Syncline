"""
Storage services for the MESH ingestion system.

This package provides blob storage abstraction and backend implementations
for handling message attachments and file storage.
"""

from .blob_storage import BlobStorageManager, get_default_storage_manager
from .backends import LocalStorageClient, S3StorageClient

__all__ = [
    'BlobStorageManager',
    'get_default_storage_manager',
    'LocalStorageClient',
    'S3StorageClient'
]
