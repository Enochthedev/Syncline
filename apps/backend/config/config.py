"""
Application Configuration Management

Centralized configuration using Pydantic Settings with:
- Environment variable loading
- Type validation
- Default values
- Secure credential handling
"""

import os
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # =============================================================================
    # Core Database Configuration
    # =============================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/mesh_development",
        description="PostgreSQL connection string with asyncpg driver",
    )
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=30, description="Max overflow connections")
    DB_POOL_PRE_PING: bool = Field(
        default=True, description="Test connections before use"
    )

    # =============================================================================
    # Redis Configuration
    # =============================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379", description="Redis connection string"
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=20, description="Redis connection pool size"
    )
    REDIS_RETRY_ON_TIMEOUT: bool = Field(default=True, description="Retry on timeout")

    # =============================================================================
    # Environment & Debug Settings
    # =============================================================================
    ENV: str = Field(
        default="development", description="Environment: development, test, production"
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    STRUCTURED_LOGGING: bool = Field(
        default=True, description="Use structured JSON logging"
    )

    # =============================================================================
    # API Configuration
    # =============================================================================
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_WORKERS: int = Field(default=1, description="Number of API workers")
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:8081",
        ],
        description="Allowed CORS origins",
    )

    # =============================================================================
    # Security Configuration
    # =============================================================================
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        description="Application secret key",
    )
    JWT_SECRET_KEY: str = Field(
        default="your-jwt-secret-key-change-this-in-production",
        description="JWT signing key",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRE_MINUTES: int = Field(default=30, description="JWT expiration time")
    ENCRYPTION_KEY: str = Field(
        default="", description="32-byte encryption key (base64 encoded)"
    )

    # =============================================================================
    # AI Configuration (Local-First with Cloud Fallback)
    # =============================================================================
    DEFAULT_LLM_PROVIDER: str = Field(
        default="openrouter", description="Primary LLM provider"
    )
    DEFAULT_CHAT_MODEL: str = Field(
        default="anthropic/claude-3.5-sonnet", description="Default chat model"
    )
    DEFAULT_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text:latest", description="Default embedding model"
    )

    # OpenRouter Configuration (Primary)
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key")
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter API base URL"
    )
    OPENROUTER_TIMEOUT: int = Field(
        default=120, description="OpenRouter request timeout"
    )
    OPENROUTER_MAX_RETRIES: int = Field(default=3, description="OpenRouter max retries")

    # Ollama Configuration (Local Fallback)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Ollama API base URL"
    )
    OLLAMA_TIMEOUT: int = Field(default=120, description="Ollama request timeout")
    OLLAMA_MAX_RETRIES: int = Field(default=3, description="Ollama max retries")

    # OpenAI Configuration (Cloud Fallback)
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")

    # Anthropic Configuration (Cloud Fallback)
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")

    AI_MAX_TOKENS: int = Field(default=1000, description="Max tokens for AI responses")
    AI_TEMPERATURE: float = Field(default=0.1, description="AI temperature")
    AI_REQUEST_TIMEOUT: int = Field(default=120, description="AI request timeout")
    AI_MAX_RETRIES: int = Field(default=3, description="AI max retries")
    AI_BATCH_SIZE: int = Field(default=10, description="AI batch processing size")
    AI_CONCURRENT_REQUESTS: int = Field(default=5, description="Concurrent AI requests")

    # =============================================================================
    # Vector Database Configuration (ChromaDB)
    # =============================================================================
    CHROMA_HOST: str = Field(default="localhost", description="ChromaDB host")
    CHROMA_PORT: int = Field(default=8000, description="ChromaDB port")
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default="./vector_db", description="ChromaDB persistence directory"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="mesh_messages", description="ChromaDB collection name"
    )
    CHROMA_DISTANCE_FUNCTION: str = Field(
        default="cosine", description="Distance function for similarity"
    )

    # =============================================================================
    # PII & Privacy Settings
    # =============================================================================
    PII_REDACTION_ENABLED: bool = Field(
        default=True, description="Enable PII redaction"
    )
    PII_REDACTION_PLACEHOLDER: str = Field(
        default="[REDACTED]", description="PII placeholder"
    )
    PII_CONFIDENCE_THRESHOLD: float = Field(
        default=0.8, description="PII confidence threshold"
    )

    MESSAGE_RETENTION_DAYS: int = Field(
        default=365, description="Message retention period"
    )
    ATTACHMENT_RETENTION_DAYS: int = Field(
        default=180, description="Attachment retention period"
    )
    LOG_RETENTION_DAYS: int = Field(default=90, description="Log retention period")

    # =============================================================================
    # Matrix/WhatsApp Bridge Configuration
    # =============================================================================
    MATRIX_HOMESERVER_URL: str = Field(
        default="http://localhost:8008", description="Matrix homeserver URL"
    )
    MATRIX_ACCESS_TOKEN: str = Field(
        default="", description="Matrix access token for Syncline user"
    )
    MATRIX_USER_ID: str = Field(
        default="@syncline:localhost", description="Matrix user ID for Syncline"
    )
    MATRIX_DEVICE_ID: str = Field(default="", description="Matrix device ID")
    WHATSAPP_BRIDGE_ENABLED: bool = Field(
        default=False, description="Whether WhatsApp bridge is enabled"
    )
    WHATSAPP_BRIDGE_BOT_ID: str = Field(
        default="@whatsappbot:localhost", description="WhatsApp bridge bot Matrix ID"
    )
    WHATSAPP_BRIDGE_URL: str = Field(
        default="http://localhost:29318",
        description="WhatsApp bridge provisioning API URL",
    )
    WHATSAPP_PROVISIONING_SECRET: str = Field(
        default="", description="WhatsApp bridge provisioning shared secret"
    )

    # =============================================================================
    # Storage Configuration
    # =============================================================================
    STORAGE_BACKEND: str = Field(
        default="local", description="Storage backend: local, s3"
    )
    STORAGE_LOCAL_PATH: str = Field(
        default="./storage", description="Local storage path"
    )
    STORAGE_MAX_FILE_SIZE: str = Field(default="50MB", description="Max file size")

    # =============================================================================
    # Rate Limiting & Circuit Breaker
    # =============================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60, description="Requests per minute"
    )
    RATE_LIMIT_BURST_SIZE: int = Field(default=10, description="Burst size")

    CIRCUIT_BREAKER_ENABLED: bool = Field(
        default=True, description="Enable circuit breaker"
    )
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5, description="Failure threshold"
    )
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(
        default=30, description="Recovery timeout"
    )

    # =============================================================================
    # Monitoring & Observability
    # =============================================================================
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics")
    HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Health check interval")
    HEALTH_CHECK_TIMEOUT: int = Field(default=10, description="Health check timeout")

    # =============================================================================
    # Feature Flags
    # =============================================================================
    FEATURE_AI_PROCESSING: bool = Field(
        default=True, description="Enable AI processing"
    )
    FEATURE_REAL_TIME_SEARCH: bool = Field(
        default=True, description="Enable real-time search"
    )
    FEATURE_ENTITY_EXTRACTION: bool = Field(
        default=True, description="Enable entity extraction"
    )
    FEATURE_SUMMARY_GENERATION: bool = Field(
        default=True, description="Enable summary generation"
    )

    # =============================================================================
    # Field Validators
    # =============================================================================

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Validate SECRET_KEY is not using default value in production.

        Raises:
            ValueError: If using default value in non-development environment
        """
        default_value = "your-super-secret-key-change-this-in-production"
        if v == default_value:
            # Allow in development, error in production
            env = os.getenv("ENV", "development")
            if env.lower() == "production":
                raise ValueError(
                    "SECRET_KEY must be changed from default value in production! "
                    "Set SECRET_KEY environment variable to a secure random string."
                )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """
        Validate JWT_SECRET_KEY is not using default value in production.

        Raises:
            ValueError: If using default value in non-development environment
        """
        default_value = "your-jwt-secret-key-change-this-in-production"
        if v == default_value:
            env = os.getenv("ENV", "development")
            if env.lower() == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default value in production! "
                    "Set JWT_SECRET_KEY environment variable."
                )
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Validate database URL has required components.

        Raises:
            ValueError: If database URL is invalid or using default password
        """
        if "password@localhost" in v:
            env = os.getenv("ENV", "development")
            if env.lower() == "production":
                raise ValueError(
                    "DATABASE_URL is using default password in production! "
                    "Set DATABASE_URL environment variable with secure credentials."
                )
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError(
                "DATABASE_URL must use PostgreSQL (postgresql:// or postgresql+asyncpg://)"
            )
        return v

    @field_validator("MATRIX_ACCESS_TOKEN", mode="after")
    @classmethod
    def validate_matrix_token(cls, v: str) -> str:
        """
        Validate MATRIX_ACCESS_TOKEN is set if WhatsApp bridge is enabled.

        Note: This validation happens before WHATSAPP_BRIDGE_ENABLED is set,
        so we check the environment variable directly.

        Raises:
            ValueError: If token is empty and WhatsApp bridge is enabled
        """
        bridge_enabled = os.getenv("WHATSAPP_BRIDGE_ENABLED", "false").lower() == "true"
        if bridge_enabled and not v:
            raise ValueError(
                "MATRIX_ACCESS_TOKEN is required when WHATSAPP_BRIDGE_ENABLED=true. "
                "Obtain a token from your Matrix homeserver and set MATRIX_ACCESS_TOKEN."
            )
        if v and len(v) < 10:
            raise ValueError("MATRIX_ACCESS_TOKEN appears to be invalid (too short)")
        return v

    @field_validator("MATRIX_USER_ID", mode="after")
    @classmethod
    def validate_matrix_user_id(cls, v: str) -> str:
        """
        Validate MATRIX_USER_ID format.

        Raises:
            ValueError: If user ID format is invalid
        """
        if v and not v.startswith("@"):
            raise ValueError(
                "MATRIX_USER_ID must start with '@' (e.g., '@syncline:localhost')"
            )
        if v and ":" not in v:
            raise ValueError(
                "MATRIX_USER_ID must include domain (e.g., '@syncline:localhost')"
            )
        return v

    @field_validator("LOG_LEVEL", mode="after")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate LOG_LEVEL is a valid logging level.

        Raises:
            ValueError: If log level is invalid
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got '{v}'")
        return v_upper

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle JSON string format
            if v.startswith("["):
                import json

                return json.loads(v)
            # Handle comma-separated format
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENV.lower() == "development"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.ENV.lower() == "test"


# Global settings instance
settings = Settings()


# Export settings
__all__ = ["settings", "Settings"]
