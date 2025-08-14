"""
Blob storage integration for handling message attachments.

This module provides an abstraction layer for storing and retrieving
message attachments using various blob storage backends.
"""

import hashlib
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
import logging
from urllib.parse import urlparse
import asyncio

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
        """
        Upload content to blob storage.

        Args:
            path: Storage path for the blob
            content: Binary content to upload
            content_type: MIME type of the content
            metadata: Additional metadata to store with the blob

        Returns:
            Public URL of the uploaded blob

        Raises:
            BlobStorageError: If upload fails
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """
        Download content from blob storage.

        Args:
            path: Storage path of the blob

        Returns:
            Binary content of the blob

        Raises:
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If download fails
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a blob from storage.

        Args:
            path: Storage path of the blob

        Returns:
            True if deleted, False if not found

        Raises:
            BlobStorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a blob exists.

        Args:
            path: Storage path of the blob

        Returns:
            True if blob exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_signed_url(
        self,
        path: str,
        expires_in: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Get a signed URL for temporary access to a blob.

        Args:
            path: Storage path of the blob
            expires_in: How long the URL should be valid

        Returns:
            Signed URL for the blob

        Raises:
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If URL generation fails
        """
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for a blob.

        Args:
            path: Storage path of the blob

        Returns:
            Metadata dictionary

        Raises:
            BlobNotFoundError: If blob doesn't exist
        """
        pass


class LocalFileSystemStorage(BlobStorageClient):
    """Local filesystem implementation of blob storage (for development/testing)."""

    def __init__(self, base_path: str = "./storage"):
        """
        Initialize local filesystem storage.

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(
            f"Initialized local filesystem storage at {self.base_path}")

    def _get_full_path(self, path: str) -> str:
        """Get full filesystem path for a storage path."""
        # Ensure path is relative and safe
        path = path.lstrip('/')
        full_path = os.path.join(self.base_path, path)

        # Security check: ensure path is within base directory
        if not os.path.abspath(full_path).startswith(self.base_path):
            raise BlobStorageError(f"Invalid path: {path}")

        return full_path

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to local filesystem."""
        try:
            full_path = self._get_full_path(path)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write content
            with open(full_path, 'wb') as f:
                f.write(content)

            # Store metadata in a separate file
            if metadata or content_type:
                metadata_dict = metadata or {}
                if content_type:
                    metadata_dict['content_type'] = content_type
                metadata_dict['uploaded_at'] = datetime.utcnow().isoformat()
                metadata_dict['size'] = len(content)
                metadata_dict['hash'] = hashlib.sha256(content).hexdigest()

                metadata_path = full_path + '.metadata'
                import json
                with open(metadata_path, 'w') as f:
                    json.dump(metadata_dict, f)

            # Return a file:// URL
            return f"file://{full_path}"

        except Exception as e:
            logger.error(f"Failed to upload to local storage: {e}")
            raise BlobStorageError(f"Upload failed: {e}")

    async def download(self, path: str) -> bytes:
        """Download content from local filesystem."""
        try:
            full_path = self._get_full_path(path)

            if not os.path.exists(full_path):
                raise BlobNotFoundError(f"Blob not found: {path}")

            with open(full_path, 'rb') as f:
                return f.read()

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download from local storage: {e}")
            raise BlobStorageError(f"Download failed: {e}")

    async def delete(self, path: str) -> bool:
        """Delete a blob from local filesystem."""
        try:
            full_path = self._get_full_path(path)

            if not os.path.exists(full_path):
                return False

            os.remove(full_path)

            # Also remove metadata file if it exists
            metadata_path = full_path + '.metadata'
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            return True

        except Exception as e:
            logger.error(f"Failed to delete from local storage: {e}")
            raise BlobStorageError(f"Delete failed: {e}")

    async def exists(self, path: str) -> bool:
        """Check if a blob exists in local filesystem."""
        try:
            full_path = self._get_full_path(path)
            return os.path.exists(full_path)
        except Exception:
            return False

    async def get_signed_url(
        self,
        path: str,
        expires_in: timedelta = timedelta(hours=1)
    ) -> str:
        """Get a file:// URL (no signing needed for local files)."""
        if not await self.exists(path):
            raise BlobNotFoundError(f"Blob not found: {path}")

        full_path = self._get_full_path(path)
        return f"file://{full_path}"

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for a blob."""
        full_path = self._get_full_path(path)

        if not os.path.exists(full_path):
            raise BlobNotFoundError(f"Blob not found: {path}")

        metadata = {}
        metadata_path = full_path + '.metadata'

        if os.path.exists(metadata_path):
            import json
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read metadata for {path}: {e}")

        # Add basic file info
        stat = os.stat(full_path)
        metadata.update({
            'size': stat.st_size,
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        })

        return metadata


class S3BlobStorage(BlobStorageClient):
    """AWS S3 implementation of blob storage."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = 'us-east-1',
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize S3 blob storage.

        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key (optional, can use IAM roles)
            aws_secret_access_key: AWS secret key (optional, can use IAM roles)
            region_name: AWS region
            endpoint_url: Custom S3 endpoint (for S3-compatible services)
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url

        # This would require boto3 to be installed
        # For now, this is a placeholder implementation
        logger.warning(
            "S3BlobStorage is not fully implemented - requires boto3")

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to S3."""
        # Placeholder implementation
        raise NotImplementedError("S3 storage requires boto3 implementation")

    async def download(self, path: str) -> bytes:
        """Download content from S3."""
        raise NotImplementedError("S3 storage requires boto3 implementation")

    async def delete(self, path: str) -> bool:
        """Delete a blob from S3."""
        raise NotImplementedError("S3 storage requires boto3 implementation")

    async def exists(self, path: str) -> bool:
        """Check if a blob exists in S3."""
        raise NotImplementedError("S3 storage requires boto3 implementation")

    async def get_signed_url(
        self,
        path: str,
        expires_in: timedelta = timedelta(hours=1)
    ) -> str:
        """Get a signed URL for S3 object."""
        raise NotImplementedError("S3 storage requires boto3 implementation")

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for S3 object."""
        raise NotImplementedError("S3 storage requires boto3 implementation")


class SupabaseBlobStorage(BlobStorageClient):
    """Supabase Storage implementation of blob storage."""

    def __init__(
        self,
        url: str,
        key: str,
        bucket_name: str = 'attachments'
    ):
        """
        Initialize Supabase blob storage.

        Args:
            url: Supabase project URL
            key: Supabase service key
            bucket_name: Storage bucket name
        """
        self.url = url
        self.key = key
        self.bucket_name = bucket_name

        # This would require supabase-py to be installed
        logger.warning(
            "SupabaseBlobStorage is not fully implemented - requires supabase-py")

    async def upload(
        self,
        path: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload content to Supabase Storage."""
        raise NotImplementedError(
            "Supabase storage requires supabase-py implementation")

    async def download(self, path: str) -> bytes:
        """Download content from Supabase Storage."""
        raise NotImplementedError(
            "Supabase storage requires supabase-py implementation")

    async def delete(self, path: str) -> bool:
        """Delete a blob from Supabase Storage."""
        raise NotImplementedError(
            "Supabase storage requires supabase-py implementation")

    async def exists(self, path: str) -> bool:
        """Check if a blob exists in Supabase Storage."""
        raise NotImplementedError(
            "Supabase storage requires supabase-py implementation")

    async def get_signed_url(
        self,
        path: str,
        expires_in: timedelta = timedelta(hours=1)
    ) -> str:
        """Get a signed URL for Supabase Storage object."""
        raise NotImplementedError(
            "Supabase storage requires supabase-py implementation")

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get metadata for Supabase Storage object."""
        raise NotImplementedError(
            "Supabase storage requires supabase-py implementation")


class BlobStorageManager:
    """Manager for blob storage operations with multiple backend support."""

    def __init__(self, client: BlobStorageClient):
        """
        Initialize blob storage manager.

        Args:
            client: Blob storage client implementation
        """
        self.client = client
        logger.info(
            f"Initialized blob storage manager with {type(client).__name__}")

    async def store_attachment(
        self,
        content: bytes,
        filename: str,
        message_id: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Store an attachment and return storage information.

        Args:
            content: Binary content of the attachment
            filename: Original filename
            message_id: ID of the message this attachment belongs to
            content_type: MIME type of the content
            metadata: Additional metadata

        Returns:
            Dictionary with storage information
        """
        # Generate storage path
        content_hash = hashlib.sha256(content).hexdigest()
        file_extension = self._get_file_extension(filename)
        storage_path = f"attachments/{message_id[:2]}/{message_id}/{content_hash}{file_extension}"

        # Prepare metadata
        storage_metadata = {
            'original_filename': filename,
            'message_id': message_id,
            'content_hash': content_hash,
            'size': len(content),
            'uploaded_at': datetime.utcnow().isoformat(),
        }

        if metadata:
            storage_metadata.update(metadata)

        try:
            # Upload to storage
            storage_url = await self.client.upload(
                path=storage_path,
                content=content,
                content_type=content_type,
                metadata=storage_metadata
            )

            logger.info(f"Stored attachment {filename} at {storage_path}")

            return {
                'storage_path': storage_path,
                'storage_url': storage_url,
                'content_hash': content_hash,
                'size': len(content),
                'metadata': storage_metadata
            }

        except Exception as e:
            logger.error(f"Failed to store attachment {filename}: {e}")
            raise BlobStorageError(f"Failed to store attachment: {e}")

    async def retrieve_attachment(self, storage_path: str) -> bytes:
        """
        Retrieve attachment content by storage path.

        Args:
            storage_path: Path where the attachment is stored

        Returns:
            Binary content of the attachment
        """
        try:
            return await self.client.download(storage_path)
        except Exception as e:
            logger.error(
                f"Failed to retrieve attachment from {storage_path}: {e}")
            raise

    async def delete_attachment(self, storage_path: str) -> bool:
        """
        Delete an attachment from storage.

        Args:
            storage_path: Path where the attachment is stored

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.client.delete(storage_path)
            if result:
                logger.info(f"Deleted attachment at {storage_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete attachment at {storage_path}: {e}")
            raise

    async def get_attachment_url(
        self,
        storage_path: str,
        expires_in: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Get a URL for accessing an attachment.

        Args:
            storage_path: Path where the attachment is stored
            expires_in: How long the URL should be valid

        Returns:
            URL for accessing the attachment
        """
        try:
            return await self.client.get_signed_url(storage_path, expires_in)
        except Exception as e:
            logger.error(
                f"Failed to get URL for attachment at {storage_path}: {e}")
            raise

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if not filename or '.' not in filename:
            return ''
        return '.' + filename.split('.')[-1].lower()


def create_blob_storage_client(storage_type: str, **kwargs) -> BlobStorageClient:
    """
    Factory function to create blob storage clients.

    Args:
        storage_type: Type of storage ('local', 's3', 'supabase')
        **kwargs: Configuration parameters for the storage client

    Returns:
        Configured blob storage client

    Raises:
        ValueError: If storage type is not supported
    """
    if storage_type.lower() == 'local':
        return LocalFileSystemStorage(
            base_path=kwargs.get('base_path', './storage')
        )
    elif storage_type.lower() == 's3':
        return S3BlobStorage(
            bucket_name=kwargs['bucket_name'],
            aws_access_key_id=kwargs.get('aws_access_key_id'),
            aws_secret_access_key=kwargs.get('aws_secret_access_key'),
            region_name=kwargs.get('region_name', 'us-east-1'),
            endpoint_url=kwargs.get('endpoint_url')
        )
    elif storage_type.lower() == 'supabase':
        return SupabaseBlobStorage(
            url=kwargs['url'],
            key=kwargs['key'],
            bucket_name=kwargs.get('bucket_name', 'attachments')
        )
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


# Default storage manager (can be configured at startup)
_default_storage_manager: Optional[BlobStorageManager] = None


def get_default_storage_manager() -> BlobStorageManager:
    """Get the default blob storage manager."""
    global _default_storage_manager

    if _default_storage_manager is None:
        # Create default local storage for development
        client = LocalFileSystemStorage()
        _default_storage_manager = BlobStorageManager(client)

    return _default_storage_manager


def set_default_storage_manager(manager: BlobStorageManager) -> None:
    """Set the default blob storage manager."""
    global _default_storage_manager
    _default_storage_manager = manager
