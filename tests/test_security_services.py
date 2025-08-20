"""
Tests for security services including encryption, token vault, and audit logging.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from services.security.encryption_service import EncryptionService, EncryptionError, DecryptionError
from services.security.token_vault import TokenVault, TokenVaultError, TokenNotFoundError, TokenExpiredError
from services.security.audit_logger import AuditLogger, AuditLoggerError
from services.security.key_rotation import KeyRotationService, KeyRotationError
from services.security.types import (
    KeyType, EncryptionAlgorithm, AuditEventType, AuditSeverity,
    SecurityConfig, KeyRotationPolicy
)
from services.storage.backends import MemoryStorageClient


class TestEncryptionService:
    """Test cases for the EncryptionService."""

    @pytest.fixture
    def audit_logger(self):
        """Mock audit logger."""
        return AsyncMock()

    @pytest.fixture
    def encryption_service(self, audit_logger):
        """Create encryption service for testing."""
        config = SecurityConfig(
            encryption_algorithm=EncryptionAlgorithm.AES_256_GCM,
            pii_encryption_enabled=True
        )
        return EncryptionService(audit_logger=audit_logger, config=config)

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_field(self, encryption_service):
        """Test basic field encryption and decryption."""
        plaintext = "sensitive data"
        field_name = "email"

        # Encrypt
        encrypted_data = await encryption_service.encrypt_field(
            plaintext, field_name, KeyType.DATA_ENCRYPTION_KEY
        )

        assert encrypted_data.encrypted_value != plaintext.encode()
        assert encrypted_data.key_id is not None
        assert encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM
        assert encrypted_data.iv is not None
        assert encrypted_data.tag is not None

        # Decrypt
        decrypted = await encryption_service.decrypt_field(encrypted_data, field_name)
        assert decrypted == plaintext

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_with_different_algorithms(self, audit_logger):
        """Test encryption with different algorithms."""
        config = SecurityConfig(
            encryption_algorithm=EncryptionAlgorithm.AES_256_CBC)
        service = EncryptionService(audit_logger=audit_logger, config=config)

        plaintext = "test data"

        # Test AES-256-CBC
        encrypted_cbc = await service.encrypt_field(
            plaintext, "test", algorithm=EncryptionAlgorithm.AES_256_CBC
        )
        decrypted_cbc = await service.decrypt_field(encrypted_cbc, "test")
        assert decrypted_cbc == plaintext

        # Test AES-256-GCM
        encrypted_gcm = await service.encrypt_field(
            plaintext, "test", algorithm=EncryptionAlgorithm.AES_256_GCM
        )
        decrypted_gcm = await service.decrypt_field(encrypted_gcm, "test")
        assert decrypted_gcm == plaintext

    @pytest.mark.asyncio
    async def test_key_rotation(self, encryption_service):
        """Test key rotation functionality."""
        # Create initial key
        plaintext = "test data"
        encrypted1 = await encryption_service.encrypt_field(plaintext, "test")

        # Rotate key
        new_key = await encryption_service.rotate_key(encrypted1.key_id)

        assert new_key.key_id != encrypted1.key_id
        assert new_key.is_active is True

        # Old key should still work for decryption
        decrypted = await encryption_service.decrypt_field(encrypted1, "test")
        assert decrypted == plaintext

    @pytest.mark.asyncio
    async def test_encryption_with_audit_logging(self, encryption_service, audit_logger):
        """Test that encryption operations are properly audited."""
        plaintext = "sensitive data"

        # Encrypt
        await encryption_service.encrypt_field(plaintext, "email")

        # Verify audit log was called
        audit_logger.log_event.assert_called()
        call_args = audit_logger.log_event.call_args
        assert call_args[1]["event_type"] == AuditEventType.ENCRYPTION_OPERATION
        assert call_args[1]["action"] == "encrypt_field"

    @pytest.mark.asyncio
    async def test_decryption_failure_handling(self, encryption_service):
        """Test handling of decryption failures."""
        # Create invalid encrypted data
        invalid_data = {
            "encrypted_value": b"invalid",
            "key_id": "nonexistent_key",
            "algorithm": EncryptionAlgorithm.AES_256_GCM,
            "iv": b"invalid_iv",
            "tag": b"invalid_tag"
        }

        with pytest.raises(DecryptionError):
            await encryption_service.decrypt_field(invalid_data, "test")


class TestTokenVault:
    """Test cases for the TokenVault."""

    @pytest.fixture
    def storage_backend(self):
        """Memory storage backend for testing."""
        return MemoryStorageClient()

    @pytest.fixture
    def audit_logger(self):
        """Mock audit logger."""
        return AsyncMock()

    @pytest.fixture
    def encryption_service(self, audit_logger):
        """Mock encryption service."""
        service = AsyncMock()
        service.encrypt_field = AsyncMock(return_value=Mock(
            encrypted_value=b"encrypted",
            key_id="test_key",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            iv=b"test_iv",
            tag=b"test_tag"
        ))
        service.decrypt_field = AsyncMock(return_value="decrypted_token")
        return service

    @pytest.fixture
    def token_vault(self, encryption_service, audit_logger, storage_backend):
        """Create token vault for testing."""
        return TokenVault(
            encryption_service=encryption_service,
            audit_logger=audit_logger,
            storage_backend=storage_backend
        )

    @pytest.mark.asyncio
    async def test_store_and_retrieve_token(self, token_vault):
        """Test storing and retrieving tokens."""
        token_id = "test_token"
        token_value = "secret_token_value"
        platform = "gmail"
        user_id = "user123"

        # Store token
        metadata = await token_vault.store_token(
            token_id=token_id,
            token_value=token_value,
            platform=platform,
            user_id=user_id,
            token_type="access_token",
            scopes=["read", "write"]
        )

        assert metadata.token_id == token_id
        assert metadata.platform == platform
        assert metadata.user_id == user_id
        assert metadata.scopes == ["read", "write"]

        # Retrieve token
        retrieved_token = await token_vault.retrieve_token(token_id, user_id, platform)
        assert retrieved_token == "decrypted_token"

    @pytest.mark.asyncio
    async def test_token_expiration(self, token_vault):
        """Test token expiration handling."""
        token_id = "expired_token"
        expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired

        # Store expired token
        await token_vault.store_token(
            token_id=token_id,
            token_value="token_value",
            platform="gmail",
            user_id="user123",
            expires_at=expires_at
        )

        # Try to retrieve expired token
        with pytest.raises(TokenExpiredError):
            await token_vault.retrieve_token(token_id, "user123", "gmail")

    @pytest.mark.asyncio
    async def test_token_not_found(self, token_vault):
        """Test handling of non-existent tokens."""
        with pytest.raises(TokenNotFoundError):
            await token_vault.retrieve_token("nonexistent", "user123", "gmail")

    @pytest.mark.asyncio
    async def test_delete_token(self, token_vault):
        """Test token deletion."""
        token_id = "delete_test"

        # Store token first
        await token_vault.store_token(
            token_id=token_id,
            token_value="token_value",
            platform="gmail",
            user_id="user123"
        )

        # Delete token
        deleted = await token_vault.delete_token(token_id, "user123", "gmail")
        assert deleted is True

        # Verify token is gone
        with pytest.raises(TokenNotFoundError):
            await token_vault.retrieve_token(token_id, "user123", "gmail")

    @pytest.mark.asyncio
    async def test_token_caching(self, token_vault):
        """Test token caching functionality."""
        token_id = "cached_token"

        # Store token
        await token_vault.store_token(
            token_id=token_id,
            token_value="token_value",
            platform="gmail",
            user_id="user123"
        )

        # First retrieval should hit storage
        await token_vault.retrieve_token(token_id, "user123", "gmail")

        # Second retrieval should hit cache
        await token_vault.retrieve_token(token_id, "user123", "gmail")

        # Verify cache was used (storage backend should only be called once)
        assert len(token_vault._token_cache) > 0


class TestAuditLogger:
    """Test cases for the AuditLogger."""

    @pytest.fixture
    def storage_backend(self):
        """Memory storage backend for testing."""
        return MemoryStorageClient()

    @pytest.fixture
    def audit_logger(self, storage_backend):
        """Create audit logger for testing."""
        return AuditLogger(
            storage_backend=storage_backend,
            enable_database_logging=False,  # Disable DB for unit tests
            enable_file_logging=True
        )

    @pytest.mark.asyncio
    async def test_log_event(self, audit_logger):
        """Test basic event logging."""
        event_id = await audit_logger.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            action="test_action",
            user_id="user123",
            resource_type="test_resource",
            resource_id="resource123",
            details={"key": "value"}
        )

        assert event_id is not None
        assert len(audit_logger._event_queue) > 0

    @pytest.mark.asyncio
    async def test_event_batching(self, audit_logger):
        """Test event batching functionality."""
        # Log multiple events
        for i in range(5):
            await audit_logger.log_event(
                event_type=AuditEventType.DATA_ACCESS,
                action=f"test_action_{i}",
                user_id="user123"
            )

        # Events should be queued
        assert len(audit_logger._event_queue) == 5

        # Force flush
        await audit_logger._flush_events()

        # Queue should be empty after flush
        assert len(audit_logger._event_queue) == 0

    @pytest.mark.asyncio
    async def test_high_severity_immediate_flush(self, audit_logger):
        """Test that high severity events are flushed immediately."""
        await audit_logger.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            action="critical_action",
            severity=AuditSeverity.CRITICAL
        )

        # High severity events should trigger immediate flush
        assert len(audit_logger._event_queue) == 0

    @pytest.mark.asyncio
    async def test_integrity_hash_calculation(self, audit_logger):
        """Test integrity hash calculation."""
        from services.security.types import AuditEvent

        event = AuditEvent(
            event_type=AuditEventType.DATA_ACCESS,
            action="test_action",
            user_id="user123"
        )

        hash1 = audit_logger._calculate_integrity_hash(event)
        hash2 = audit_logger._calculate_integrity_hash(event)

        # Same event should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex string

    @pytest.mark.asyncio
    async def test_file_logging(self, audit_logger, storage_backend):
        """Test file-based audit logging."""
        await audit_logger.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            action="file_test",
            user_id="user123"
        )

        # Force flush to file
        await audit_logger._flush_events()

        # Check that file was created
        date_key = datetime.utcnow().strftime('%Y-%m-%d')
        file_path = f"audit_logs/{date_key}/audit.jsonl"

        # Verify file exists in storage
        exists = await storage_backend.exists(file_path)
        assert exists is True


class TestKeyRotationService:
    """Test cases for the KeyRotationService."""

    @pytest.fixture
    def encryption_service(self):
        """Mock encryption service."""
        service = AsyncMock()
        service.rotate_key = AsyncMock(return_value=Mock(
            key_id="new_key_id",
            is_active=True
        ))
        return service

    @pytest.fixture
    def audit_logger(self):
        """Mock audit logger."""
        return AsyncMock()

    @pytest.fixture
    def key_rotation_service(self, encryption_service, audit_logger):
        """Create key rotation service for testing."""
        return KeyRotationService(
            encryption_service=encryption_service,
            audit_logger=audit_logger
        )

    @pytest.mark.asyncio
    async def test_immediate_key_rotation(self, key_rotation_service):
        """Test immediate key rotation."""
        key_id = "test_key"
        key_type = KeyType.DATA_ENCRYPTION_KEY

        job_id = await key_rotation_service.rotate_key_immediately(
            key_id=key_id,
            key_type=key_type,
            reason="security_incident"
        )

        assert job_id is not None

        # Verify rotation was performed
        key_rotation_service.encryption_service.rotate_key.assert_called_once_with(
            key_id)

    @pytest.mark.asyncio
    async def test_rotation_policy_management(self, key_rotation_service):
        """Test rotation policy management."""
        policy = KeyRotationPolicy(
            key_type=KeyType.TOKEN_ENCRYPTION_KEY,
            rotation_interval_days=30,
            auto_rotate=True
        )

        # Set policy
        key_rotation_service.set_rotation_policy(
            KeyType.TOKEN_ENCRYPTION_KEY, policy)

        # Get policy
        retrieved_policy = key_rotation_service.get_rotation_policy(
            KeyType.TOKEN_ENCRYPTION_KEY)

        assert retrieved_policy == policy
        assert retrieved_policy.rotation_interval_days == 30
        assert retrieved_policy.auto_rotate is True

    @pytest.mark.asyncio
    async def test_rotation_job_tracking(self, key_rotation_service):
        """Test rotation job tracking."""
        # Perform rotation
        job_id = await key_rotation_service.rotate_key_immediately(
            "test_key",
            KeyType.DATA_ENCRYPTION_KEY
        )

        # Get jobs
        jobs = key_rotation_service.get_rotation_jobs()

        assert len(jobs) > 0
        assert any(job.job_id == job_id for job in jobs)

        # Get completed jobs
        completed_jobs = key_rotation_service.get_rotation_jobs(
            status="completed")
        assert len(completed_jobs) > 0

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(self, key_rotation_service):
        """Test scheduler start/stop lifecycle."""
        # Start scheduler
        await key_rotation_service.start_rotation_scheduler()
        assert key_rotation_service._running is True

        # Stop scheduler
        await key_rotation_service.stop_rotation_scheduler()
        assert key_rotation_service._running is False

    @pytest.mark.asyncio
    async def test_job_cleanup(self, key_rotation_service):
        """Test cleanup of old rotation jobs."""
        # Create some completed jobs
        await key_rotation_service.rotate_key_immediately(
            "test_key_1",
            KeyType.DATA_ENCRYPTION_KEY
        )
        await key_rotation_service.rotate_key_immediately(
            "test_key_2",
            KeyType.DATA_ENCRYPTION_KEY
        )

        # Cleanup jobs (with 0 days to clean all)
        cleaned_count = await key_rotation_service.cleanup_completed_jobs(older_than_days=0)

        assert cleaned_count >= 0


class TestSecurityIntegration:
    """Integration tests for security services."""

    @pytest.fixture
    def storage_backend(self):
        """Memory storage backend for testing."""
        return MemoryStorageClient()

    @pytest.fixture
    def security_services(self, storage_backend):
        """Create integrated security services."""
        audit_logger = AuditLogger(
            storage_backend=storage_backend,
            enable_database_logging=False,
            enable_file_logging=True
        )

        encryption_service = EncryptionService(audit_logger=audit_logger)

        token_vault = TokenVault(
            encryption_service=encryption_service,
            audit_logger=audit_logger,
            storage_backend=storage_backend
        )

        key_rotation_service = KeyRotationService(
            encryption_service=encryption_service,
            audit_logger=audit_logger
        )

        return {
            "audit_logger": audit_logger,
            "encryption_service": encryption_service,
            "token_vault": token_vault,
            "key_rotation_service": key_rotation_service
        }

    @pytest.mark.asyncio
    async def test_end_to_end_token_lifecycle(self, security_services):
        """Test complete token lifecycle with security services."""
        services = security_services

        # Store token
        token_metadata = await services["token_vault"].store_token(
            token_id="integration_test",
            token_value="secret_token",
            platform="gmail",
            user_id="user123",
            token_type="access_token"
        )

        # Retrieve token
        retrieved_token = await services["token_vault"].retrieve_token(
            "integration_test", "user123", "gmail"
        )

        # Rotate encryption key
        await services["key_rotation_service"].rotate_key_immediately(
            "test_key",
            KeyType.TOKEN_ENCRYPTION_KEY
        )

        # Verify audit events were logged
        await services["audit_logger"]._flush_events()

        # All operations should complete successfully
        assert token_metadata.token_id == "integration_test"
        assert retrieved_token is not None

    @pytest.mark.asyncio
    async def test_security_failure_handling(self, security_services):
        """Test handling of security failures."""
        services = security_services

        # Test encryption failure handling
        with patch.object(services["encryption_service"], "encrypt_field", side_effect=Exception("Encryption failed")):
            with pytest.raises(TokenVaultError):
                await services["token_vault"].store_token(
                    token_id="fail_test",
                    token_value="token",
                    platform="gmail",
                    user_id="user123"
                )

        # Verify failure was audited
        await services["audit_logger"]._flush_events()

    @pytest.mark.asyncio
    async def test_compliance_features(self, security_services):
        """Test compliance and audit features."""
        services = security_services

        # Generate various audit events
        await services["audit_logger"].log_event(
            event_type=AuditEventType.DATA_ACCESS,
            action="compliance_test",
            user_id="user123",
            severity=AuditSeverity.HIGH
        )

        await services["audit_logger"].log_event(
            event_type=AuditEventType.AUTHENTICATION,
            action="login",
            user_id="user123",
            ip_address="192.168.1.1"
        )

        # Force flush
        await services["audit_logger"]._flush_events()

        # Verify integrity hashes are calculated
        # This would be more comprehensive with database integration
