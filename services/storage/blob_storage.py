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
import aiohttp

from .backends import BlobStorageClient, LocalStorageClient, S3StorageClient, MemoryStorageClient, BlobStorageError, BlobNotFoundError

logger = logging.getLogger(__name__)


class BlobStorageManager:
    """
    High-level manager for blob storage operations.

    Provides a unified interface for storing and retrieving blobs
    across different storage backends with features like caching,
    compression, and automatic cleanup.
    """

    def __init__(
        self,
        primary_client: BlobStorageClient,
        cache_client: Optional[BlobStorageClient] = None,
        enable_compression: bool = False,
        max_file_size: int = 100 * 1024 * 1024  # 100MB
    ):
        """
        Initialize blob storage manager.

        Args:
            primary_client: Primary storage backend
            cache_client: Optional cache storage backend
            enable_compression: Whether to compress blobs before storage
            max_file_size: Maximum file size in bytes
        """
        self.primary_client = primary_client
        self.cache_client = cache_client
        self.enable_compression = enable_compression
        self.max_file_size = max_file_size

        # Statistics
        self.stats = {
            'uploads': 0,
            'downloads': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'bytes_uploaded': 0,
            'bytes_downloaded': 0,
            'errors': 0
        }

        logger.info(
            f"BlobStorageManager initialized with {type(primary_client).__name__}")

    async def store(
        self,
        path: str,
        content: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store content in blob storage.

        Args:
            path: Storage path for the blob
            content: Content to store (bytes or file-like object)
            content_type: MIME type of the content
            metadata: Additional metadata

        Returns:
            Storage path of the stored blob
        """
        try:
            # Convert content to bytes if needed
            if hasattr(content, 'read'):
                content_bytes = content.read()
                if hasattr(content, 'seek'):
                    content.seek(0)  # Reset file pointer
            else:
                content_bytes = content

            # Validate file size
            if len(content_bytes) > self.max_file_size:
                raise BlobStorageError(
                    f"File too large: {len(content_bytes)} bytes (max: {self.max_file_size})")

            # Compress if enabled
            if self.enable_compression:
                content_bytes = await self._compress_content(content_bytes)
                if metadata is None:
                    metadata = {}
                metadata['compressed'] = 'true'

            # Generate content hash for integrity
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            if metadata is None:
                metadata = {}
            metadata['content_hash'] = content_hash

            # Store in primary storage
            stored_path = await self.primary_client.upload(path, content_bytes, content_type, metadata)

            # Store in cache if available
            if self.cache_client:
                try:
                    await self.cache_client.upload(path, content_bytes, content_type, metadata)
                except Exception as e:
                    logger.warning(f"Failed to cache blob {path}: {e}")

            # Update statistics
            self.stats['uploads'] += 1
            self.stats['bytes_uploaded'] += len(content_bytes)

            logger.debug(f"Stored blob: {path} ({len(content_bytes)} bytes)")
            return stored_path

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to store blob {path}: {e}")
            raise

    async def retrieve(self, path: str) -> bytes:
        """
        Retrieve content from blob storage.

        Args:
            path: Storage path of the blob

        Returns:
            Content of the blob
        """
        try:
            content = None

            # Try cache first if available
            if self.cache_client:
                try:
                    if await self.cache_client.exists(path):
                        content = await self.cache_client.download(path)
                        self.stats['cache_hits'] += 1
                        logger.debug(f"Cache hit for blob: {path}")
                except Exception as e:
                    logger.warning(f"Cache retrieval failed for {path}: {e}")

            # Fallback to primary storage
            if content is None:
                content = await self.primary_client.download(path)
                self.stats['cache_misses'] += 1

                # Store in cache for future use
                if self.cache_client:
                    try:
                        metadata = await self.primary_client.get_metadata(path)
                        content_type = metadata.get('content_type')
                        await self.cache_client.upload(path, content, content_type, metadata)
                    except Exception as e:
                        logger.warning(f"Failed to cache blob {path}: {e}")

            # Decompress if needed
            if self.enable_compression:
                metadata = await self.get_metadata(path)
                if metadata.get('compressed') == 'true':
                    content = await self._decompress_content(content)

            # Verify content integrity if hash is available
            metadata = await self.get_metadata(path)
            if 'content_hash' in metadata:
                content_hash = hashlib.sha256(content).hexdigest()
                if content_hash != metadata['content_hash']:
                    raise BlobStorageError(
                        f"Content integrity check failed for {path}")

            # Update statistics
            self.stats['downloads'] += 1
            self.stats['bytes_downloaded'] += len(content)

            logger.debug(f"Retrieved blob: {path} ({len(content)} bytes)")
            return content

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to retrieve blob {path}: {e}")
            raise

    async def store_from_url(
        self,
        url: str,
        storage_path: str,
        timeout: int = 30
    ) -> str:
        """
        Download content from URL and store in blob storage.

        Args:
            url: URL to download from
            storage_path: Path to store the content
            timeout: Download timeout in seconds

        Returns:
            Storage path of the stored blob
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    response.raise_for_status()

                    content = await response.read()
                    content_type = response.headers.get('content-type')

                    # Extract filename from URL if not in storage_path
                    if not os.path.basename(storage_path):
                        parsed_url = urlparse(url)
                        filename = os.path.basename(
                            parsed_url.path) or 'download'
                        storage_path = os.path.join(storage_path, filename)

                    metadata = {
                        'source_url': url,
                        'download_time': datetime.utcnow().isoformat()
                    }

                    return await self.store(storage_path, content, content_type, metadata)

        except Exception as e:
            logger.error(f"Failed to store from URL {url}: {e}")
            raise BlobStorageError(f"Store from URL failed: {e}") from e

    async def delete(self, path: str) -> bool:
        """
        Delete content from blob storage.

        Args:
            path: Storage path of the blob to delete

        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # Delete from primary storage
            primary_deleted = await self.primary_client.delete(path)

            # Delete from cache if available
            if self.cache_client:
                try:
                    await self.cache_client.delete(path)
                except Exception as e:
                    logger.warning(f"Failed to delete from cache {path}: {e}")

            logger.debug(f"Deleted blob: {path}")
            return primary_deleted

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Failed to delete blob {path}: {e}")
            raise

    async def exists(self, path: str) -> bool:
        """
        Check if content exists in blob storage.

        Args:
            path: Storage path to check

        Returns:
            True if exists, False otherwise
        """
        try:
            return await self.primary_client.exists(path)
        except Exception as e:
            logger.error(f"Failed to check existence of {path}: {e}")
            return False

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for stored content.

        Args:
            path: Storage path of the blob

        Returns:
            Metadata dictionary
        """
        try:
            return await self.primary_client.get_metadata(path)
        except Exception as e:
            logger.error(f"Failed to get metadata for {path}: {e}")
            raise

    async def list_blobs(self, prefix: str = "") -> list:
        """
        List blobs with optional prefix filter.

        Args:
            prefix: Optional prefix to filter blobs

        Returns:
            List of blob paths
        """
        try:
            return await self.primary_client.list_blobs(prefix)
        except Exception as e:
            logger.error(f"Failed to list blobs with prefix {prefix}: {e}")
            raise

    async def cleanup_old_blobs(self, max_age_days: int = 30) -> int:
        """
        Clean up old blobs based on age.

        Args:
            max_age_days: Maximum age in days before deletion

        Returns:
            Number of blobs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            deleted_count = 0

            blobs = await self.list_blobs()

            for blob_path in blobs:
                try:
                    metadata = await self.get_metadata(blob_path)
                    upload_time_str = metadata.get('upload_time')

                    if upload_time_str:
                        upload_time = datetime.fromisoformat(upload_time_str)
                        if upload_time < cutoff_date:
                            await self.delete(blob_path)
                            deleted_count += 1
                            logger.debug(f"Cleaned up old blob: {blob_path}")

                except Exception as e:
                    logger.warning(
                        f"Failed to process blob {blob_path} during cleanup: {e}")
                    continue

            logger.info(f"Cleanup completed: {deleted_count} blobs deleted")
            return deleted_count

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise

    async def _compress_content(self, content: bytes) -> bytes:
        """Compress content using gzip."""
        import gzip
        return gzip.compress(content)

    async def _decompress_content(self, content: bytes) -> bytes:
        """Decompress gzip content."""
        import gzip
        return gzip.decompress(content)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_operations = self.stats['uploads'] + self.stats['downloads']
        cache_operations = self.stats['cache_hits'] + \
            self.stats['cache_misses']

        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(cache_operations, 1)
            ) if self.cache_client else 0.0,
            'error_rate': (
                self.stats['errors'] / max(total_operations, 1)
            ),
            'primary_backend': type(self.primary_client).__name__,
            'cache_backend': type(self.cache_client).__name__ if self.cache_client else None
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage backends."""
        try:
            # Test primary storage
            test_path = f"health_check_{datetime.utcnow().timestamp()}"
            test_content = b"health check"

            await self.primary_client.upload(test_path, test_content)
            retrieved = await self.primary_client.download(test_path)
            await self.primary_client.delete(test_path)

            primary_healthy = retrieved == test_content

            # Test cache if available
            cache_healthy = True
            if self.cache_client:
                try:
                    await self.cache_client.upload(test_path, test_content)
                    cache_retrieved = await self.cache_client.download(test_path)
                    await self.cache_client.delete(test_path)
                    cache_healthy = cache_retrieved == test_content
                except Exception:
                    cache_healthy = False

            return {
                'status': 'healthy' if primary_healthy else 'unhealthy',
                'primary_storage': 'healthy' if primary_healthy else 'unhealthy',
                'cache_storage': 'healthy' if cache_healthy else 'unhealthy' if self.cache_client else 'disabled',
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global storage manager instance
_default_storage_manager = None


def get_default_storage_manager() -> BlobStorageManager:
    """Get the default storage manager instance."""
    global _default_storage_manager

    if _default_storage_manager is None:
        # Initialize with local storage by default
        primary_client = LocalStorageClient()
        _default_storage_manager = BlobStorageManager(primary_client)

    return _default_storage_manager
