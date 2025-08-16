"""
Blob storage manager for handling message attachments.

This module provides a high-level interface for storing and retrieving
message attachments using various storage backends.
"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO, Union
import logging
from urllib.parse import urlparse
import asyncio
from pathlib import Path

from .backends import BlobStorageClient, LocalStorageBackend, S3StorageBackend, BlobStorageError, BlobNotFoundError
from config.config import settings

logger = logging.getLogger(__name__)


class BlobStorageManager:
    """
    High-level blob storage manager.

    Provides a unified interface for storing and retrieving blobs
    across different storage backends.
    """

    def __init__(self, client: BlobStorageClient):
        """Initialize blob storage manager with a storage client."""
        self.client = client
        self.stats = {
            'uploads': 0,
            'downloads': 0,
            'deletes': 0,
            'errors': 0,
            'total_bytes_uploaded': 0,
            'total_bytes_downloaded': 0
        }

    async def store_blob(
        self,
        data: Union[bytes, BinaryIO],
        filename: str,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a blob and return its storage path.

        Args:
            data: Binary data or file-like object to store
            filename: Original filename
            mime_type: MIME type of the content
            metadata: Additional metadata to store

        Returns:
            Storage path of the stored blob
        """
        try:
            # Read data if it's a file-like object
            if hasattr(data, 'read'):
                content = data.read()
            else:
                content = data

            # Generate storage path
            storage_path = self._generate_storage_path(filename, content)

            # Prepare metadata
            blob_metadata = {
                'original_filename': filename,
                'size': len(content),
                'uploaded_at': datetime.utcnow().isoformat(),
                'content_hash': hashlib.sha256(content).hexdigest()
            }
            if metadata:
                blob_metadata.update(metadata)

            # Upload to storage
            url = await self.client.upload(
                path=storage_path,
                content=content,
                content_type=mime_type,
                metadata=blob_metadata
            )

            # Update stats
            self.stats['uploads'] += 1
            self.stats['total_bytes_uploaded'] += len(content)

            logger.debug(f"Stored blob {filename} at {storage_path}")
            return storage_path

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to store blob {filename}: {e}")
            raise BlobStorageError(f"Failed to store blob: {e}")

    async def retrieve_blob(self, storage_path: str) -> bytes:
        """
        Retrieve a blob by its storage path.

        Args:
            storage_path: Storage path of the blob

        Returns:
            Binary content of the blob
        """
        try:
            content = await self.client.download(storage_path)

            # Update stats
            self.stats['downloads'] += 1
            self.stats['total_bytes_downloaded'] += len(content)

            logger.debug(f"Retrieved blob from {storage_path}")
            return content

        except BlobNotFoundError:
            logger.warning(f"Blob not found: {storage_path}")
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to retrieve blob {storage_path}: {e}")
            raise BlobStorageError(f"Failed to retrieve blob: {e}")

    async def delete_blob(self, storage_path: str) -> bool:
        """
        Delete a blob by its storage path.

        Args:
            storage_path: Storage path of the blob

        Returns:
            True if deleted, False if not found
        """
        try:
            deleted = await self.client.delete(storage_path)

            if deleted:
                self.stats['deletes'] += 1
                logger.debug(f"Deleted blob at {storage_path}")

            return deleted

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to delete blob {storage_path}: {e}")
            raise BlobStorageError(f"Failed to delete blob: {e}")

    async def blob_exists(self, storage_path: str) -> bool:
        """Check if a blob exists."""
        try:
            return await self.client.exists(storage_path)
        except Exception as e:
            logger.error(f"Failed to check blob existence {storage_path}: {e}")
            return False

    async def get_blob_metadata(self, storage_path: str) -> Dict[str, Any]:
        """Get metadata for a blob."""
        try:
            return await self.client.get_metadata(storage_path)
        except Exception as e:
            logger.error(f"Failed to get blob metadata {storage_path}: {e}")
            raise BlobStorageError(f"Failed to get metadata: {e}")

    async def generate_access_url(
        self,
        storage_path: str,
        expiration: timedelta = timedelta(hours=1)
    ) -> str:
        """Generate a temporary access URL for a blob."""
        try:
            return await self.client.generate_presigned_url(
                storage_path, expiration
            )
        except Exception as e:
            logger.error(
                f"Failed to generate access URL for {storage_path}: {e}")
            raise BlobStorageError(f"Failed to generate access URL: {e}")

    def _generate_storage_path(self, filename: str, content: bytes) -> str:
        """Generate a unique storage path for a blob."""
        # Create hash of content for deduplication
        content_hash = hashlib.sha256(content).hexdigest()

        # Extract file extension
        file_ext = Path(filename).suffix.lower()

        # Generate path: year/month/day/hash[0:2]/hash[2:4]/hash.ext
        now = datetime.utcnow()
        date_path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}"
        hash_path = f"{content_hash[:2]}/{content_hash[2:4]}"

        storage_path = f"{date_path}/{hash_path}/{content_hash}{file_ext}"
        return storage_path

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.stats.copy()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage backend."""
        try:
            # Test upload/download/delete cycle
            test_content = b"health check test"
            test_path = "health_check/test.txt"

            # Upload
            await self.client.upload(test_path, test_content, "text/plain")

            # Download
            downloaded = await self.client.download(test_path)

            # Verify content
            if downloaded != test_content:
                raise Exception("Content mismatch in health check")

            # Delete
            await self.client.delete(test_path)

            return {
                'status': 'healthy',
                'backend': self.client.__class__.__name__,
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'backend': self.client.__class__.__name__,
                'stats': self.get_stats()
            }


def create_storage_manager(backend_type: str = "local", **kwargs) -> BlobStorageManager:
    """
    Create a blob storage manager with the specified backend.

    Args:
        backend_type: Type of storage backend ('local' or 's3')
        **kwargs: Backend-specific configuration

    Returns:
        Configured BlobStorageManager instance
    """
    if backend_type.lower() == "local":
        base_path = kwargs.get('base_path', 'data/attachments')
        client = LocalStorageBackend(base_path)
    elif backend_type.lower() == "s3":
        client = S3StorageBackend(**kwargs)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")

    return BlobStorageManager(client)


# Global storage manager instance
_default_storage_manager = None


def get_default_storage_manager() -> BlobStorageManager:
    """Get the default storage manager instance."""
    global _default_storage_manager
    if _default_storage_manager is None:
        # Use local storage by default
        _default_storage_manager = create_storage_manager("local")
    return _default_storage_manager
