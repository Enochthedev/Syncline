from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    ENV: str = "development"
    DEBUG: bool = False

    # Database connection pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_PRE_PING: bool = True

    X_API_KEY: Optional[str] = None
    X_API_SECRET: Optional[str] = None
    X_ACCESS_TOKEN: Optional[str] = None
    X_CALLBACK_URL: str = "http://localhost:8000/x/callback"

    # Gmail configuration
    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify"
    GMAIL_CREDENTIALS_FILE: str = "config/credentials.json"
    GMAIL_TOKEN_FILE: str = "token.json"
    GMAIL_WEBHOOK_ENDPOINT: str = "/webhooks/gmail"
    GMAIL_WEBHOOK_SECRET: Optional[str] = None
    GMAIL_TOPIC_NAME: Optional[str] = None
    GMAIL_MAX_RESULTS: int = 100
    GMAIL_INCLUDE_SPAM_TRASH: bool = False

    # AI Processing Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # AI Model Configuration (Local-first)
    DEFAULT_LLM_PROVIDER: str = "ollama"  # ollama, openai, anthropic
    # Local Ollama model (M1 Air optimized)
    DEFAULT_CHAT_MODEL: str = "tinyllama:latest"
    DEFAULT_EMBEDDING_MODEL: str = "nomic-embed-text:latest"  # Local embedding model

    # AI Processing Settings
    AI_MAX_TOKENS: int = 1000
    AI_TEMPERATURE: float = 0.1
    AI_REQUEST_TIMEOUT: int = 120
    AI_MAX_RETRIES: int = 3
    AI_BATCH_SIZE: int = 10

    # PII Redaction Settings
    PII_REDACTION_ENABLED: bool = True
    PII_REDACTION_PLACEHOLDER: str = "[REDACTED]"
    PII_CONFIDENCE_THRESHOLD: float = 0.8

    class Config:
        env_file = ".env"
        case_sensitive = True


# Add validation before instantiation
if not os.getenv("DATABASE_URL"):
    raise ValueError("DATABASE_URL environment variable is required")

settings = Settings()
