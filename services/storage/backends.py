"""
Storage backend implementations for blob storage.

This module provides concrete implementations of storage backends
including local filesystem and cloud storage options.
"""

import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
import logging
from urllib.parse import urlparse
import asyncio
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


class BlobStorageError(Exception):
    """Base exception for blob storage operations."""
    pass


class BlobNotFoundError(BlobStorageError):
    """Raised when a blob is not found."""
    pass


class BlobStorageClient(ABC):
    """Abstract base class for blob storage clients."""

    @abstractmethod
    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to blob storage."""
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download content from blob storage."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete content from blob storage."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if content exists in blob storage."""
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for stored content."""
        pass

    @abstractmethod
    async def list_blobs(self, prefix: str = "") -> list:
        """List blobs with optional prefix filter."""
        pass

    async def store(self, key: str, data: str) -> None:
        """Store string data."""
        await self.upload(key, data.encode('utf-8'), content_type='text/plain')

    async def retrieve(self, key: str) -> Optional[str]:
        """Retrieve string data."""
        try:
            content = await self.download(key)
            return content.decode('utf-8')
        except BlobNotFoundError:
            return None

    async def append(self, key: str, data: str) -> None:
        """Append string data to existing content."""
        try:
            existing = await self.retrieve(key) or ""
            new_content = existing + data
            await self.store(key, new_content)
        except Exception as e:
            logger.error(f"Failed to append to {key}: {e}")
            raise BlobStorageError(f"Append failed: {e}")


class LocalStorageClient(BlobStorageClient):
    """Local filesystem storage client."""

    def __init__(self, base_path: str = "./storage"):
        """Initialize local storage client."""
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(
            f"LocalStorageClient initialized with base_path: {self.base_path}")

    def _get_full_path(self, path: str) -> str:
        """Get full filesystem path for a storage path."""
        # Normalize path and prevent directory traversal
        normalized_path = os.path.normpath(path.lstrip('/'))
        if '..' in normalized_path:
            raise BlobStorageError(f"Invalid path: {path}")

        return os.path.join(self.base_path, normalized_path)

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to local storage."""
        try:
            full_path = self._get_full_path(path)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write content to file
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)

            # Store metadata in a separate file
            if metadata or content_type:
                metadata_dict = metadata or {}
                if content_type:
                    metadata_dict['content_type'] = content_type
                metadata_dict['upload_time'] = datetime.utcnow().isoformat()
                metadata_dict['size'] = len(content)

                metadata_path = full_path + '.metadata'
                async with aiofiles.open(metadata_path, 'w') as f:
                    import json
                    await f.write(json.dumps(metadata_dict))

            logger.debug(f"Uploaded {len(content)} bytes to {path}")
            return path

        except Exception as e:
            logger.error(f"Failed to upload to {path}: {e}")
            raise BlobStorageError(f"Upload failed: {e}") from e

    async def download(self, path: str) -> bytes:
        """Download content from local storage."""
        try:
            full_path = self._get_full_path(path)

            if not os.path.exists(full_path):
                raise BlobNotFoundError(f"Blob not found: {path}")

            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()

            logger.debug(f"Downloaded {len(content)} bytes from {path}")
            return content

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download from {path}: {e}")
            raise BlobStorageError(f"Download failed: {e}") from e

    async def delete(self, path: str) -> bool:
        """Delete content from local storage."""
        try:
            full_path = self._get_full_path(path)

            if not os.path.exists(full_path):
                return False

            # Delete main file
            os.remove(full_path)

            # Delete metadata file if it exists
            metadata_path = full_path + '.metadata'
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            logger.debug(f"Deleted blob: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            raise BlobStorageError(f"Delete failed: {e}") from e

    async def exists(self, path: str) -> bool:
        """Check if content exists in local storage."""
        try:
            full_path = self._get_full_path(path)
            return os.path.exists(full_path)
        except Exception as e:
            logger.error(f"Failed to check existence of {path}: {e}")
            return False

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for stored content."""
        try:
            full_path = self._get_full_path(path)

            if not os.path.exists(full_path):
                raise BlobNotFoundError(f"Blob not found: {path}")

            # Get file stats
            stat = os.stat(full_path)
            metadata = {
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat()
            }

            # Load stored metadata if available
            metadata_path = full_path + '.metadata'
            if os.path.exists(metadata_path):
                try:
                    async with aiofiles.open(metadata_path, 'r') as f:
                        import json
                        stored_metadata = json.loads(await f.read())
                        metadata.update(stored_metadata)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {path}: {e}")

            return metadata

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get metadata for {path}: {e}")
            raise BlobStorageError(f"Get metadata failed: {e}") from e

    async def list_blobs(self, prefix: str = "") -> list:
        """List blobs with optional prefix filter."""
        try:
            blobs = []
            prefix_path = self._get_full_path(
                prefix) if prefix else self.base_path

            if not os.path.exists(prefix_path):
                return blobs

            for root, dirs, files in os.walk(prefix_path):
                for file in files:
                    if file.endswith('.metadata'):
                        continue  # Skip metadata files

                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.base_path)

                    # Convert to forward slashes for consistency
                    relative_path = relative_path.replace(os.sep, '/')

                    blobs.append(relative_path)

            return sorted(blobs)

        except Exception as e:
            logger.error(f"Failed to list blobs with prefix {prefix}: {e}")
            raise BlobStorageError(f"List blobs failed: {e}") from e


class S3StorageClient(BlobStorageClient):
    """Amazon S3 storage client."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None
    ):
        """Initialize S3 storage client."""
        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.endpoint_url = endpoint_url

        # Initialize S3 client (would need boto3 in real implementation)
        logger.info(f"S3StorageClient initialized for bucket: {bucket_name}")

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to S3."""
        # This is a placeholder implementation
        # In a real implementation, you would use boto3 or aioboto3
        raise NotImplementedError("S3 storage client not fully implemented")

    async def download(self, path: str) -> bytes:
        """Download content from S3."""
        raise NotImplementedError("S3 storage client not fully implemented")

    async def delete(self, path: str) -> bool:
        """Delete content from S3."""
        raise NotImplementedError("S3 storage client not fully implemented")

    async def exists(self, path: str) -> bool:
        """Check if content exists in S3."""
        raise NotImplementedError("S3 storage client not fully implemented")

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for S3 object."""
        raise NotImplementedError("S3 storage client not fully implemented")

    async def list_blobs(self, prefix: str = "") -> list:
        """List S3 objects with prefix."""
        raise NotImplementedError("S3 storage client not fully implemented")


class MemoryStorageClient(BlobStorageClient):
    """In-memory storage client for testing."""

    def __init__(self):
        """Initialize memory storage client."""
        self._storage: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        logger.info("MemoryStorageClient initialized")

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to memory storage."""
        self._storage[path] = content

        # Store metadata
        meta_dict = metadata or {}
        if content_type:
            meta_dict['content_type'] = content_type
        meta_dict['upload_time'] = datetime.utcnow().isoformat()
        meta_dict['size'] = len(content)

        self._metadata[path] = meta_dict

        logger.debug(
            f"Uploaded {len(content)} bytes to memory storage: {path}")
        return path

    async def download(self, path: str) -> bytes:
        """Download content from memory storage."""
        if path not in self._storage:
            raise BlobNotFoundError(f"Blob not found: {path}")

        content = self._storage[path]
        logger.debug(
            f"Downloaded {len(content)} bytes from memory storage: {path}")
        return content

    async def delete(self, path: str) -> bool:
        """Delete content from memory storage."""
        if path not in self._storage:
            return False

        del self._storage[path]
        self._metadata.pop(path, None)

        logger.debug(f"Deleted from memory storage: {path}")
        return True

    async def exists(self, path: str) -> bool:
        """Check if content exists in memory storage."""
        return path in self._storage

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for memory storage content."""
        if path not in self._storage:
            raise BlobNotFoundError(f"Blob not found: {path}")

        return self._metadata.get(path, {})

    async def list_blobs(self, prefix: str = "") -> list:
        """List blobs in memory storage with prefix."""
        if not prefix:
            return list(self._storage.keys())

        return [path for path in self._storage.keys() if path.startswith(prefix)]


def get_storage_backend(backend_type: str = "local", **kwargs) -> BlobStorageClient:
    """
    Get a storage backend instance.

    Args:
        backend_type: Type of backend ('local', 's3', 'memory')
        **kwargs: Backend-specific configuration

    Returns:
        BlobStorageClient instance
    """
    if backend_type == "local":
        base_path = kwargs.get("base_path", "./storage")
        return LocalStorageClient(base_path=base_path)
    elif backend_type == "s3":
        return S3StorageClient(**kwargs)
    elif backend_type == "memory":
        return MemoryStorageClient()
    else:
        raise ValueError(f"Unknown storage backend type: {backend_type}")
