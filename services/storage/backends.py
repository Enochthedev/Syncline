"""
Storage backend implementations for different storage providers.

This module contains concrete implementations of storage backends
including local filesystem and cloud storage providers.
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
from pathlib import Path

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
        """Delete a blob from storage."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a blob exists."""
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get blob metadata."""
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> str:
        """Generate a presigned URL for blob access."""
        pass


class LocalStorageBackend(BlobStorageClient):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str = "data/attachments"):
        """Initialize local storage backend."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at {self.base_path}")

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to local filesystem."""
        try:
            file_path = self.base_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, 'wb') as f:
                f.write(content)

            # Store metadata if provided
            if metadata:
                metadata_path = file_path.with_suffix(
                    file_path.suffix + '.meta')
                metadata_with_content_type = metadata.copy()
                if content_type:
                    metadata_with_content_type['content_type'] = content_type

                import json
                with open(metadata_path, 'w') as f:
                    json.dump(metadata_with_content_type, f)

            logger.debug(f"Uploaded {len(content)} bytes to {path}")
            return f"file://{file_path.absolute()}"

        except Exception as e:
            logger.error(f"Failed to upload to {path}: {e}")
            raise BlobStorageError(f"Upload failed: {e}")

    async def download(self, path: str) -> bytes:
        """Download content from local filesystem."""
        try:
            file_path = self.base_path / path

            if not file_path.exists():
                raise BlobNotFoundError(f"Blob not found: {path}")

            with open(file_path, 'rb') as f:
                content = f.read()

            logger.debug(f"Downloaded {len(content)} bytes from {path}")
            return content

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download from {path}: {e}")
            raise BlobStorageError(f"Download failed: {e}")

    async def delete(self, path: str) -> bool:
        """Delete a blob from local filesystem."""
        try:
            file_path = self.base_path / path

            if not file_path.exists():
                return False

            file_path.unlink()

            # Also delete metadata file if it exists
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            if metadata_path.exists():
                metadata_path.unlink()

            logger.debug(f"Deleted blob at {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            raise BlobStorageError(f"Delete failed: {e}")

    async def exists(self, path: str) -> bool:
        """Check if a blob exists in local filesystem."""
        file_path = self.base_path / path
        return file_path.exists()

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get blob metadata from local filesystem."""
        try:
            file_path = self.base_path / path

            if not file_path.exists():
                raise BlobNotFoundError(f"Blob not found: {path}")

            # Get file stats
            stat = file_path.stat()
            metadata = {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            }

            # Load stored metadata if available
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            if metadata_path.exists():
                import json
                with open(metadata_path, 'r') as f:
                    stored_metadata = json.load(f)
                    metadata.update(stored_metadata)

            return metadata

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get metadata for {path}: {e}")
            raise BlobStorageError(f"Get metadata failed: {e}")

    async def generate_presigned_url(
        self,
        path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> str:
        """Generate a presigned URL for local file access."""
        # For local storage, return file:// URL
        file_path = self.base_path / path
        if not file_path.exists():
            raise BlobNotFoundError(f"Blob not found: {path}")

        return f"file://{file_path.absolute()}"


class S3StorageBackend(BlobStorageClient):
    """Amazon S3 storage backend."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None
    ):
        """Initialize S3 storage backend."""
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url

        # Initialize S3 client (would use boto3 in real implementation)
        logger.info(f"S3 storage initialized for bucket {bucket_name}")

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to S3."""
        # This would use boto3 in a real implementation
        raise NotImplementedError("S3 backend not fully implemented")

    async def download(self, path: str) -> bytes:
        """Download content from S3."""
        raise NotImplementedError("S3 backend not fully implemented")

    async def delete(self, path: str) -> bool:
        """Delete a blob from S3."""
        raise NotImplementedError("S3 backend not fully implemented")

    async def exists(self, path: str) -> bool:
        """Check if a blob exists in S3."""
        raise NotImplementedError("S3 backend not fully implemented")

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get blob metadata from S3."""
        raise NotImplementedError("S3 backend not fully implemented")

    async def generate_presigned_url(
        self,
        path: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> str:
        """Generate a presigned URL for S3 access."""
        raise NotImplementedError("S3 backend not fully implemented")
