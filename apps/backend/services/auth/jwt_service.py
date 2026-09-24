"""
JWT Authentication Service

Provides JWT token generation and validation:
- Access token generation
- Refresh token generation
- Token validation and decoding
- Token revocation support
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import jwt
from passlib.context import CryptContext

from config.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTService:
    """
    Service for JWT token operations.

    Provides:
    - Access token generation (short-lived)
    - Refresh token generation (long-lived)
    - Token validation
    - Password hashing and verification
    """

    def __init__(
        self,
        secret_key: str = settings.JWT_SECRET_KEY,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize JWT service.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token lifetime
            refresh_token_expire_days: Refresh token lifetime
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str = "user",
        extra_claims: Optional[dict] = None,
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User ID
            email: User email
            role: User role
            extra_claims: Additional claims to include

        Returns:
            JWT access token
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        claims = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        if extra_claims:
            claims.update(extra_claims)

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User ID
            email: User email

        Returns:
            JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        claims = {
            "sub": str(user_id),
            "email": email,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> dict:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Token claims

        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
        """
        try:
            claims = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return claims
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify token and return claims if valid.

        Args:
            token: JWT token

        Returns:
            Token claims or None if invalid
        """
        try:
            return self.decode_token(token)
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
            return None

    def hash_password(self, password: str) -> str:
        """
        Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)


# Global service instance
_jwt_service: Optional[JWTService] = None


def get_jwt_service() -> JWTService:
    """
    Get the global JWT service instance.

    Returns:
        JWT service
    """
    global _jwt_service

    if _jwt_service is None:
        _jwt_service = JWTService()

    return _jwt_service


__all__ = [
    "JWTService",
    "get_jwt_service",
]
