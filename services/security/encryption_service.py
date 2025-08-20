"""
Field-level encryption service for PII data protection.

This service provides AES-256 encryption for sensitive data fields
with key management and rotation support.
"""

import logging
import secrets
import base64
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import os
import json

from .types import (
    EncryptionKey, EncryptedData, KeyType, EncryptionAlgorithm,
    AuditEventType, SecurityConfig
)
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption operations."""
    pass


class KeyNotFoundError(EncryptionError):
    """Raised when an encryption key is not found."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


class EncryptionService:
    """
    Field-level encryption service with AES-256 support.

    Provides encryption and decryption of sensitive data fields
    with key management and audit logging.
    """

    def __init__(
        self,
        audit_logger: Optional['AuditLogger'] = None,
        config: Optional[SecurityConfig] = None
    ):
        self.audit_logger = audit_logger
        self.config = config or SecurityConfig()
        self._keys: Dict[str, EncryptionKey] = {}
        self._key_cache: Dict[str, bytes] = {}
        self._master_key: Optional[bytes] = None

        # Initialize master key
        self._initialize_master_key()

    def _initialize_master_key(self) -> None:
        """Initialize or load the master encryption key."""
        try:
            # In production, this would come from KMS/HSM
            master_key_env = os.getenv("MESH_MASTER_KEY")
            if master_key_env:
                self._master_key = base64.b64decode(master_key_env)
            else:
                # Generate a new master key for development
                self._master_key = secrets.token_bytes(32)  # 256 bits
                logger.warning(
                    "No master key found in environment. Generated new key for development. "
                    "In production, use KMS/HSM for key management."
                )
        except Exception as e:
            logger.error(f"Failed to initialize master key: {e}")
            raise EncryptionError(f"Master key initialization failed: {e}")

    async def encrypt_field(
        self,
        plaintext: str,
        field_name: str,
        key_type: KeyType = KeyType.DATA_ENCRYPTION_KEY,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    ) -> EncryptedData:
        """
        Encrypt a data field using the specified algorithm.

        Args:
            plaintext: The data to encrypt
            field_name: Name of the field being encrypted (for audit)
            key_type: Type of encryption key to use
            algorithm: Encryption algorithm to use

        Returns:
            EncryptedData object containing encrypted value and metadata
        """
        try:
            # Get or create encryption key
            key_id = f"{key_type.value}_{field_name}_{datetime.utcnow().strftime('%Y%m')}"
            encryption_key = await self._get_or_create_key(key_id, key_type, algorithm)

            # Get the actual key bytes
            key_bytes = await self._get_key_bytes(encryption_key.key_id)

            if algorithm == EncryptionAlgorithm.AES_256_GCM:
                encrypted_data = self._encrypt_aes_gcm(
                    plaintext.encode('utf-8'), key_bytes)
            elif algorithm == EncryptionAlgorithm.AES_256_CBC:
                encrypted_data = self._encrypt_aes_cbc(
                    plaintext.encode('utf-8'), key_bytes)
            else:
                raise EncryptionError(f"Unsupported algorithm: {algorithm}")

            result = EncryptedData(
                encrypted_value=encrypted_data["ciphertext"],
                key_id=encryption_key.key_id,
                algorithm=algorithm,
                iv=encrypted_data["iv"],
                tag=encrypted_data.get("tag"),
                metadata={"field_name": field_name,
                          "encrypted_at": datetime.utcnow().isoformat()}
            )

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.ENCRYPTION_OPERATION,
                    action="encrypt_field",
                    resource_type="encrypted_field",
                    resource_id=field_name,
                    details={
                        "key_id": encryption_key.key_id,
                        "algorithm": algorithm.value,
                        "field_name": field_name
                    }
                )

            return result

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.ENCRYPTION_OPERATION,
                    action="encrypt_field",
                    resource_type="encrypted_field",
                    resource_id=field_name,
                    success=False,
                    error_message=str(e),
                    details={"field_name": field_name,
                             "algorithm": algorithm.value}
                )
            logger.error(f"Encryption failed for field {field_name}: {e}")
            raise EncryptionError(f"Encryption failed: {e}")

    async def decrypt_field(
        self,
        encrypted_data: Union[EncryptedData, Dict[str, Any]],
        field_name: str
    ) -> str:
        """
        Decrypt a data field.

        Args:
            encrypted_data: EncryptedData object or dict with encrypted data
            field_name: Name of the field being decrypted (for audit)

        Returns:
            Decrypted plaintext string
        """
        try:
            # Handle dict input
            if isinstance(encrypted_data, dict):
                encrypted_data = EncryptedData(
                    encrypted_value=encrypted_data["encrypted_value"],
                    key_id=encrypted_data["key_id"],
                    algorithm=EncryptionAlgorithm(encrypted_data["algorithm"]),
                    iv=encrypted_data["iv"],
                    tag=encrypted_data.get("tag")
                )

            # Get the decryption key
            key_bytes = await self._get_key_bytes(encrypted_data.key_id)

            if encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM:
                plaintext_bytes = self._decrypt_aes_gcm(
                    encrypted_data.encrypted_value,
                    key_bytes,
                    encrypted_data.iv,
                    encrypted_data.tag
                )
            elif encrypted_data.algorithm == EncryptionAlgorithm.AES_256_CBC:
                plaintext_bytes = self._decrypt_aes_cbc(
                    encrypted_data.encrypted_value,
                    key_bytes,
                    encrypted_data.iv
                )
            else:
                raise DecryptionError(
                    f"Unsupported algorithm: {encrypted_data.algorithm}")

            plaintext = plaintext_bytes.decode('utf-8')

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DECRYPTION_OPERATION,
                    action="decrypt_field",
                    resource_type="encrypted_field",
                    resource_id=field_name,
                    details={
                        "key_id": encrypted_data.key_id,
                        "algorithm": encrypted_data.algorithm.value,
                        "field_name": field_name
                    }
                )

            return plaintext

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.DECRYPTION_OPERATION,
                    action="decrypt_field",
                    resource_type="encrypted_field",
                    resource_id=field_name,
                    success=False,
                    error_message=str(e),
                    details={"field_name": field_name}
                )
            logger.error(f"Decryption failed for field {field_name}: {e}")
            raise DecryptionError(f"Decryption failed: {e}")

    def _encrypt_aes_gcm(self, plaintext: bytes, key: bytes) -> Dict[str, bytes]:
        """Encrypt using AES-256-GCM."""
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv),
                        backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return {
            "ciphertext": ciphertext,
            "iv": iv,
            "tag": encryptor.tag
        }

    def _decrypt_aes_gcm(self, ciphertext: bytes, key: bytes, iv: bytes, tag: bytes) -> bytes:
        """Decrypt using AES-256-GCM."""
        cipher = Cipher(algorithms.AES(key), modes.GCM(
            iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def _encrypt_aes_cbc(self, plaintext: bytes, key: bytes) -> Dict[str, bytes]:
        """Encrypt using AES-256-CBC with PKCS7 padding."""
        from cryptography.hazmat.primitives import padding

        iv = secrets.token_bytes(16)  # 128-bit IV for CBC

        # Apply PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv),
                        backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return {
            "ciphertext": ciphertext,
            "iv": iv
        }

    def _decrypt_aes_cbc(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """Decrypt using AES-256-CBC with PKCS7 padding."""
        from cryptography.hazmat.primitives import padding

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv),
                        backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

        return plaintext

    async def _get_or_create_key(
        self,
        key_id: str,
        key_type: KeyType,
        algorithm: EncryptionAlgorithm
    ) -> EncryptionKey:
        """Get an existing key or create a new one."""
        if key_id in self._keys:
            return self._keys[key_id]

        # Create new key
        encryption_key = EncryptionKey(
            key_id=key_id,
            key_type=key_type,
            algorithm=algorithm,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90)  # 90-day rotation
        )

        # Generate the actual key bytes
        key_bytes = secrets.token_bytes(32)  # 256 bits

        # Store encrypted with master key
        encrypted_key = self._encrypt_with_master_key(key_bytes)
        self._key_cache[key_id] = encrypted_key
        self._keys[key_id] = encryption_key

        logger.info(f"Created new encryption key: {key_id}")
        return encryption_key

    async def _get_key_bytes(self, key_id: str) -> bytes:
        """Get the actual key bytes for encryption/decryption."""
        if key_id not in self._key_cache:
            raise KeyNotFoundError(f"Key not found: {key_id}")

        encrypted_key = self._key_cache[key_id]
        return self._decrypt_with_master_key(encrypted_key)

    def _encrypt_with_master_key(self, key_bytes: bytes) -> bytes:
        """Encrypt a key with the master key."""
        if not self._master_key:
            raise EncryptionError("Master key not initialized")

        iv = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(self._master_key),
                        modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(key_bytes) + encryptor.finalize()

        # Return IV + tag + ciphertext
        return iv + encryptor.tag + ciphertext

    def _decrypt_with_master_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a key with the master key."""
        if not self._master_key:
            raise EncryptionError("Master key not initialized")

        # Extract IV, tag, and ciphertext
        iv = encrypted_key[:12]
        tag = encrypted_key[12:28]
        ciphertext = encrypted_key[28:]

        cipher = Cipher(algorithms.AES(self._master_key),
                        modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    async def rotate_key(self, key_id: str) -> EncryptionKey:
        """
        Rotate an encryption key.

        Args:
            key_id: ID of the key to rotate

        Returns:
            New EncryptionKey object
        """
        try:
            old_key = self._keys.get(key_id)
            if not old_key:
                raise KeyNotFoundError(f"Key not found for rotation: {key_id}")

            # Mark old key as inactive
            old_key.is_active = False

            # Create new key with same parameters but new ID
            new_key_id = f"{key_id}_rotated_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            new_key = await self._get_or_create_key(
                new_key_id,
                old_key.key_type,
                old_key.algorithm
            )

            # Audit log
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.KEY_ROTATION,
                    action="rotate_key",
                    resource_type="encryption_key",
                    resource_id=key_id,
                    details={
                        "old_key_id": key_id,
                        "new_key_id": new_key_id,
                        "key_type": old_key.key_type.value
                    }
                )

            logger.info(f"Key rotated: {key_id} -> {new_key_id}")
            return new_key

        except Exception as e:
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.KEY_ROTATION,
                    action="rotate_key",
                    resource_type="encryption_key",
                    resource_id=key_id,
                    success=False,
                    error_message=str(e)
                )
            logger.error(f"Key rotation failed for {key_id}: {e}")
            raise EncryptionError(f"Key rotation failed: {e}")

    def get_key_info(self, key_id: str) -> Optional[EncryptionKey]:
        """Get information about an encryption key."""
        return self._keys.get(key_id)
