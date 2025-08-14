"""
Tests for blob storage functionality.

Tests local filesystem storage, storage manager, and blob operations.
"""

import pytest
import tempfile
import asyncio
from datetime import timedelta

from services.blob_storage import (
    LocalFileSystemStorage, BlobStorageManager, BlobStorageError, BlobNotFoundError,
    create_blob_storage_client, get_default_storage_manager, set_default_storage_manager
)


class TestLocalFileSystemStorage:
    """Test local filesystem storage implementation."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def local_storage(self, temp_storage_dir):
        """Create a local filesystem storage instance."""
        return LocalFileSystemStorage(temp_storage_dir)

    @pytest.mark.asyncio
    async def test_upload_download(self, local_storage):
        """Test local storage upload and download."""
        content = b"Hello, world!"
        path = "test/file.txt"

        # Upload
        url = await local_storage.upload(
            path=path,
            content=content,
            content_type="text/plain",
            metadata={"test": "value"}
        )

        assert url.startswith("file://")

        # Download
        downloaded = await local_storage.download(path)
        assert downloaded == content

    @pytest.mark.asyncio
    async def test_existence_check(self, local_storage):
        """Test file existence checking."""
        content = b"Test content"
        path = "test/exists.txt"

        # Should not exist initially
        assert await local_storage.exists(path) is False

        # Upload file
        await local_storage.upload(path, content)

        # Should exist now
        assert await local_storage.exists(path) is True

        # Non-existent file should return False
        assert await local_storage.exists("nonexistent/file.txt") is False

    @pytest.mark.asyncio
    async def test_metadata_storage(self, local_storage):
        """Test metadata storage and retrieval."""
        content = b"Test content with metadata"
        path = "test/metadata.txt"
        metadata = {"custom": "value", "type": "test"}

        await local_storage.upload(
            path=path,
            content=content,
            content_type="text/plain",
            metadata=metadata
        )

        # Get metadata
        stored_metadata = await local_storage.get_metadata(path)
        assert stored_metadata["content_type"] == "text/plain"
        assert stored_metadata["custom"] == "value"
        assert stored_metadata["type"] == "test"
        assert stored_metadata["size"] == len(content)
        assert "uploaded_at" in stored_metadata
        assert "hash" in stored_metadata

    @pytest.mark.asyncio
    async def test_delete_operations(self, local_storage):
        """Test file deletion."""
        content = b"Test content"
        path = "test/delete_me.txt"

        # Upload first
        await local_storage.upload(path, content)
        assert await local_storage.exists(path) is True

        # Delete
        result = await local_storage.delete(path)
        assert result is True
        assert await local_storage.exists(path) is False

        # Delete non-existent file
        result = await local_storage.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_signed_url_generation(self, local_storage):
        """Test signed URL generation (file:// for local storage)."""
        content = b"Test content"
        path = "test/signed.txt"

        await local_storage.upload(path, content)

        url = await local_storage.get_signed_url(path)
        assert url.startswith("file://")

        # Test with custom expiration
        url_with_expiry = await local_storage.get_signed_url(
            path, expires_in=timedelta(hours=2)
        )
        assert url_with_expiry.startswith("file://")

        # Test non-existent file
        with pytest.raises(BlobNotFoundError):
            await local_storage.get_signed_url("nonexistent")

    @pytest.mark.asyncio
    async def test_directory_creation(self, local_storage):
        """Test automatic directory creation."""
        content = b"Test content"
        nested_path = "deep/nested/directory/file.txt"

        # Should create directories automatically
        url = await local_storage.upload(nested_path, content)
        assert url.startswith("file://")

        # Verify file exists
        assert await local_storage.exists(nested_path) is True

        # Verify content
        downloaded = await local_storage.download(nested_path)
        assert downloaded == content

    @pytest.mark.asyncio
    async def test_path_security(self, local_storage):
        """Test path security validation."""
        content = b"Test content"

        # Test path traversal attempts
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/absolute/path/file.txt",
            "normal/../../../dangerous.txt"
        ]

        # Test one dangerous path to verify security
        dangerous_path = "../../../etc/passwd"

        try:
            await local_storage.upload(dangerous_path, content)
            # If we get here, the test should fail
            assert False, "Expected BlobStorageError to be raised"
        except BlobStorageError as e:
            # This is expected
            assert "Invalid path" in str(e) or "Upload failed" in str(e)

    @pytest.mark.asyncio
    async def test_error_handling(self, local_storage):
        """Test error handling in storage operations."""
        # Test download of non-existent file
        with pytest.raises(BlobNotFoundError):
            await local_storage.download("nonexistent/file.txt")

        # Test metadata of non-existent file
        with pytest.raises(BlobNotFoundError):
            await local_storage.get_metadata("nonexistent/file.txt")


class TestBlobStorageManager:
    """Test blob storage manager functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create a blob storage manager."""
        client = LocalFileSystemStorage(temp_storage_dir)
        return BlobStorageManager(client)

    @pytest.mark.asyncio
    async def test_store_attachment(self, storage_manager):
        """Test attachment storage."""
        content = b"Attachment content"
        filename = "test_attachment.txt"
        message_id = "msg123"

        result = await storage_manager.store_attachment(
            content=content,
            filename=filename,
            message_id=message_id,
            content_type="text/plain",
            metadata={"custom": "value"}
        )

        assert "storage_path" in result
        assert "storage_url" in result
        assert "content_hash" in result
        assert result["size"] == len(content)

        # Verify storage path format
        storage_path = result["storage_path"]
        assert storage_path.startswith("attachments/")
        assert message_id[:2] in storage_path
        assert message_id in storage_path

    @pytest.mark.asyncio
    async def test_retrieve_attachment(self, storage_manager):
        """Test attachment retrieval."""
        content = b"Attachment content"
        filename = "test_attachment.txt"
        message_id = "msg123"

        # Store attachment
        result = await storage_manager.store_attachment(
            content=content,
            filename=filename,
            message_id=message_id
        )

        storage_path = result["storage_path"]

        # Retrieve attachment
        retrieved = await storage_manager.retrieve_attachment(storage_path)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_delete_attachment(self, storage_manager):
        """Test attachment deletion."""
        content = b"Attachment content"
        filename = "test_attachment.txt"
        message_id = "msg123"

        # Store attachment
        result = await storage_manager.store_attachment(
            content=content,
            filename=filename,
            message_id=message_id
        )

        storage_path = result["storage_path"]

        # Delete attachment
        deleted = await storage_manager.delete_attachment(storage_path)
        assert deleted is True

        # Verify deletion
        with pytest.raises(BlobNotFoundError):
            await storage_manager.retrieve_attachment(storage_path)

    @pytest.mark.asyncio
    async def test_get_attachment_url(self, storage_manager):
        """Test attachment URL generation."""
        content = b"Attachment content"
        filename = "test_attachment.txt"
        message_id = "msg123"

        # Store attachment
        result = await storage_manager.store_attachment(
            content=content,
            filename=filename,
            message_id=message_id
        )

        storage_path = result["storage_path"]

        # Get URL
        url = await storage_manager.get_attachment_url(storage_path)
        assert url.startswith("file://")

        # Test with custom expiration
        url_with_expiry = await storage_manager.get_attachment_url(
            storage_path, expires_in=timedelta(minutes=30)
        )
        assert url_with_expiry.startswith("file://")

    @pytest.mark.asyncio
    async def test_content_hashing(self, storage_manager):
        """Test content hashing for deduplication."""
        content1 = b"Same content"
        content2 = b"Same content"
        content3 = b"Different content"

        # Store same content twice
        result1 = await storage_manager.store_attachment(
            content=content1,
            filename="file1.txt",
            message_id="msg1"
        )

        result2 = await storage_manager.store_attachment(
            content=content2,
            filename="file2.txt",
            message_id="msg2"
        )

        result3 = await storage_manager.store_attachment(
            content=content3,
            filename="file3.txt",
            message_id="msg3"
        )

        # Same content should have same hash
        assert result1["content_hash"] == result2["content_hash"]
        assert result1["content_hash"] != result3["content_hash"]

    @pytest.mark.asyncio
    async def test_file_extension_handling(self, storage_manager):
        """Test file extension handling in storage paths."""
        test_cases = [
            ("document.pdf", ".pdf"),
            ("image.JPG", ".jpg"),
            ("archive.tar.gz", ".gz"),
            ("noextension", ""),
            ("file.with.multiple.dots.txt", ".txt"),
        ]

        for filename, expected_ext in test_cases:
            content = b"Test content"
            result = await storage_manager.store_attachment(
                content=content,
                filename=filename,
                message_id="msg123"
            )

            storage_path = result["storage_path"]
            if expected_ext:
                assert storage_path.endswith(expected_ext)
            else:
                # Should not have an extension
                assert "." not in storage_path.split("/")[-1]

    @pytest.mark.asyncio
    async def test_error_handling(self, storage_manager):
        """Test error handling in storage manager."""
        # Test retrieval of non-existent attachment
        with pytest.raises(BlobNotFoundError):
            await storage_manager.retrieve_attachment("nonexistent/path")

        # Test URL generation for non-existent attachment
        with pytest.raises(BlobNotFoundError):
            await storage_manager.get_attachment_url("nonexistent/path")

        # Test deletion of non-existent attachment (should return False, not error)
        result = await storage_manager.delete_attachment("nonexistent/path")
        assert result is False


class TestBlobStorageFactory:
    """Test blob storage factory functions."""

    def test_create_local_storage_client(self):
        """Test creating local storage client."""
        client = create_blob_storage_client('local', base_path='/tmp/test')
        assert isinstance(client, LocalFileSystemStorage)

    def test_create_s3_storage_client(self):
        """Test creating S3 storage client (placeholder)."""
        # This will create the client but it's not fully implemented
        client = create_blob_storage_client(
            's3',
            bucket_name='test-bucket',
            region_name='us-west-2'
        )
        # Just verify it doesn't crash - actual S3 functionality not implemented
        assert client is not None

    def test_create_supabase_storage_client(self):
        """Test creating Supabase storage client (placeholder)."""
        # This will create the client but it's not fully implemented
        client = create_blob_storage_client(
            'supabase',
            url='https://test.supabase.co',
            key='test-key'
        )
        # Just verify it doesn't crash - actual Supabase functionality not implemented
        assert client is not None

    def test_unsupported_storage_type(self):
        """Test error handling for unsupported storage types."""
        with pytest.raises(ValueError, match="Unsupported storage type"):
            create_blob_storage_client('unsupported_type')

    def test_default_storage_manager(self):
        """Test default storage manager functionality."""
        # Get default manager
        manager1 = get_default_storage_manager()
        assert isinstance(manager1, BlobStorageManager)

        # Should return same instance
        manager2 = get_default_storage_manager()
        assert manager1 is manager2

        # Test setting custom default
        custom_client = LocalFileSystemStorage('/tmp/custom')
        custom_manager = BlobStorageManager(custom_client)
        set_default_storage_manager(custom_manager)

        # Should return custom manager
        manager3 = get_default_storage_manager()
        assert manager3 is custom_manager
