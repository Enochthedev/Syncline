"""
Encryption Service for Secure Credential Storage

Provides encryption/decryption for sensitive data like API tokens, passwords,
and connection credentials stored in the database.

Uses Fernet (symmetric encryption) from the cryptography library.
"""

import json
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from config.config import settings


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive credentials.

    Uses Fernet symmetric encryption with a key derived from the application's
    SECRET_KEY. This ensures credentials are encrypted at rest in the database.

    Example:
        service = EncryptionService()
        encrypted = service.encrypt_credentials({"api_key": "secret123"})
        decrypted = service.decrypt_credentials(encrypted)
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption service with encryption key.

        Args:
            secret_key: Optional secret key. If not provided, uses settings.SECRET_KEY
        """
        self.secret_key = secret_key or settings.SECRET_KEY
        self._cipher = self._create_cipher()

    def _create_cipher(self) -> Fernet:
        """
        Create Fernet cipher from SECRET_KEY using PBKDF2 key derivation.

        Uses a static salt (should be unique per deployment in production).
        Returns a Fernet cipher instance for encryption/decryption.
        """
        # Use a static salt derived from SECRET_KEY
        # In production, consider storing this salt separately
        salt = self.secret_key[:16].ljust(16, '0').encode('utf-8')

        # Derive encryption key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode('utf-8')))

        return Fernet(key)

    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        Encrypt a credentials dictionary to an encrypted string.

        Args:
            credentials: Dictionary of credential keys/values to encrypt

        Returns:
            Base64-encoded encrypted string

        Example:
            >>> service.encrypt_credentials({"token": "abc123"})
            'gAAAAABh...'
        """
        if not credentials:
            return ""

        # Convert dict to JSON string
        json_str = json.dumps(credentials)

        # Encrypt and return as string
        encrypted_bytes = self._cipher.encrypt(json_str.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """
        Decrypt an encrypted credentials string back to a dictionary.

        Args:
            encrypted_credentials: Base64-encoded encrypted string

        Returns:
            Dictionary of decrypted credentials

        Raises:
            ValueError: If decryption fails (invalid token or tampered data)

        Example:
            >>> service.decrypt_credentials('gAAAAABh...')
            {"token": "abc123"}
        """
        if not encrypted_credentials:
            return {}

        try:
            # Decrypt bytes
            decrypted_bytes = self._cipher.decrypt(encrypted_credentials.encode('utf-8'))

            # Convert back to dict
            json_str = decrypted_bytes.decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")

    def encrypt_value(self, value: str) -> str:
        """
        Encrypt a single string value.

        Args:
            value: String value to encrypt

        Returns:
            Encrypted string
        """
        if not value:
            return ""

        encrypted_bytes = self._cipher.encrypt(value.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt a single encrypted string value.

        Args:
            encrypted_value: Encrypted string

        Returns:
            Decrypted string

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_value:
            return ""

        try:
            decrypted_bytes = self._cipher.decrypt(encrypted_value.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {str(e)}")


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get singleton encryption service instance.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
