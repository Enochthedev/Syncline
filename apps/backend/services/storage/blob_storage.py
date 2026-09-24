"""
Blob storage manager for handling message attachments.

Provides a high-level interface for storing and retrieving
message attachments with support for downloading from URLs.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import aiohttp

from config.config import settings

from .backends import (
    BlobNotFoundError,
    BlobStorageClient,
    BlobStorageError,
    LocalStorageClient,
)

logger = logging.getLogger(__name__)


class BlobStorageManager:
    """
    High-level manager for blob storage operations.

    Provides a unified interface for storing and retrieving blobs
    with features like URL downloading and integrity checking.
    """

    def __init__(
        self,
        client: BlobStorageClient,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB default
    ):
        """
        Initialize blob storage manager.

        Args:
            client: Storage backend client
            max_file_size: Maximum file size in bytes
        """
        self.client = client
        self.max_file_size = max_file_size

        # Statistics
        self.stats = {
            "uploads": 0,
            "downloads": 0,
            "bytes_uploaded": 0,
            "bytes_downloaded": 0,
            "errors": 0,
        }

        logger.info(f"BlobStorageManager initialized with {type(client).__name__}")

    async def store(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Store content in blob storage.

        Args:
            path: Storage path for the blob
            content: Content to store as bytes
            content_type: MIME type of the content
            metadata: Additional metadata

        Returns:
            Storage path of the stored blob

        Raises:
            BlobStorageError: If storage fails or file too large
        """
        try:
            # Validate file size
            if len(content) > self.max_file_size:
                raise BlobStorageError(
                    f"File too large: {len(content)} bytes (max: {self.max_file_size})"
                )

            # Generate content hash for integrity
            content_hash = hashlib.sha256(content).hexdigest()
            if metadata is None:
                metadata = {}
            metadata["content_hash"] = content_hash

            # Store in storage backend
            stored_path = await self.client.upload(
                path, content, content_type, metadata
            )

            # Update statistics
            self.stats["uploads"] += 1
            self.stats["bytes_uploaded"] += len(content)

            logger.debug(f"Stored blob: {path} ({len(content)} bytes)")
            return stored_path

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to store blob {path}: {e}")
            raise

    async def retrieve(self, path: str) -> bytes:
        """
        Retrieve content from blob storage.

        Args:
            path: Storage path of the blob

        Returns:
            Content of the blob

        Raises:
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If retrieval fails
        """
        try:
            content = await self.client.download(path)

            # Verify content integrity if hash is available
            try:
                metadata = await self.get_metadata(path)
                if "content_hash" in metadata:
                    content_hash = hashlib.sha256(content).hexdigest()
                    if content_hash != metadata["content_hash"]:
                        raise BlobStorageError(
                            f"Content integrity check failed for {path}"
                        )
            except BlobNotFoundError:
                pass  # Metadata not found, skip integrity check

            # Update statistics
            self.stats["downloads"] += 1
            self.stats["bytes_downloaded"] += len(content)

            logger.debug(f"Retrieved blob: {path} ({len(content)} bytes)")
            return content

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to retrieve blob {path}: {e}")
            raise

    async def store_from_url(
        self, url: str, storage_path: str, timeout: int = 30
    ) -> str:
        """
        Download content from URL and store in blob storage.

        Args:
            url: URL to download from
            storage_path: Path to store the content
            timeout: Download timeout in seconds

        Returns:
            Storage path of the stored blob

        Raises:
            BlobStorageError: If download or storage fails
        """
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(url) as response:
                    response.raise_for_status()

                    content = await response.read()
                    content_type = response.headers.get("content-type")

                    metadata = {
                        "source_url": url,
                        "download_time": datetime.utcnow().isoformat(),
                    }

                    return await self.store(
                        storage_path, content, content_type, metadata
                    )

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

        Raises:
            BlobStorageError: If deletion fails
        """
        try:
            deleted = await self.client.delete(path)
            if deleted:
                logger.debug(f"Deleted blob: {path}")
            return deleted

        except Exception as e:
            self.stats["errors"] += 1
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
            return await self.client.exists(path)
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

        Raises:
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If metadata retrieval fails
        """
        try:
            return await self.client.get_metadata(path)
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

        Raises:
            BlobStorageError: If listing fails
        """
        try:
            return await self.client.list_blobs(prefix)
        except Exception as e:
            logger.error(f"Failed to list blobs with prefix {prefix}: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Statistics dictionary
        """
        total_operations = self.stats["uploads"] + self.stats["downloads"]

        return {
            **self.stats,
            "error_rate": (self.stats["errors"] / max(total_operations, 1)),
            "backend": type(self.client).__name__,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on storage backend.

        Returns:
            Health status dictionary
        """
        try:
            # Test storage with a small file
            test_path = f"health_check_{datetime.utcnow().timestamp()}"
            test_content = b"health check"

            await self.client.upload(test_path, test_content)
            retrieved = await self.client.download(test_path)
            await self.client.delete(test_path)

            healthy = retrieved == test_content

            return {
                "status": "healthy" if healthy else "unhealthy",
                "backend": type(self.client).__name__,
                "stats": self.get_stats(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "backend": type(self.client).__name__,
            }


# Global storage manager instance
_default_storage_manager: Optional[BlobStorageManager] = None


def get_default_storage_manager() -> BlobStorageManager:
    """
    Get the default storage manager instance.

    Returns:
        BlobStorageManager instance
    """
    global _default_storage_manager

    if _default_storage_manager is None:
        # Initialize with local storage by default
        storage_path = settings.STORAGE_LOCAL_PATH
        client = LocalStorageClient(base_path=storage_path)

        # Parse max file size from config
        max_size_str = settings.STORAGE_MAX_FILE_SIZE
        if max_size_str.endswith("MB"):
            max_size = int(max_size_str[:-2]) * 1024 * 1024
        elif max_size_str.endswith("GB"):
            max_size = int(max_size_str[:-2]) * 1024 * 1024 * 1024
        else:
            max_size = int(max_size_str)

        _default_storage_manager = BlobStorageManager(
            client=client, max_file_size=max_size
        )

    return _default_storage_manager


# Export exceptions for convenience
__all__ = [
    "BlobStorageManager",
    "get_default_storage_manager",
    "BlobStorageError",
    "BlobNotFoundError",
]
