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

    # Slack configuration
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None  # For Socket Mode
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_USER_TOKEN: Optional[str] = None
    SLACK_SCOPES: str = "channels:history channels:read chat:write groups:history groups:read im:history im:read mpim:history mpim:read users:read users:read.email team:read"
    SLACK_REDIRECT_URI: str = "http://localhost:8000/slack/oauth/callback"
    SLACK_WEBHOOK_ENDPOINT: str = "/webhooks/slack"
    SLACK_SOCKET_MODE_ENABLED: bool = True
    SLACK_EVENTS_API_ENABLED: bool = True
    SLACK_MAX_RESULTS: int = 200
    SLACK_INCLUDE_PRIVATE_CHANNELS: bool = True
    SLACK_INCLUDE_DIRECT_MESSAGES: bool = True

    # Telegram configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None
    TELEGRAM_WEBHOOK_PATH: str = "/webhooks/telegram"
    TELEGRAM_ALLOWED_UPDATES: str = "message,edited_message,channel_post,edited_channel_post"
    TELEGRAM_DROP_PENDING_UPDATES: bool = True
    TELEGRAM_MAX_CONNECTIONS: int = 40
    TELEGRAM_READ_TIMEOUT: int = 30
    TELEGRAM_WRITE_TIMEOUT: int = 30
    TELEGRAM_CONNECT_TIMEOUT: int = 30
    TELEGRAM_MAX_MESSAGES_PER_REQUEST: int = 100
    TELEGRAM_INCLUDE_PRIVATE_CHATS: bool = True
    TELEGRAM_INCLUDE_GROUP_CHATS: bool = True
    TELEGRAM_INCLUDE_CHANNELS: bool = True

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

    # Vector Database Settings
    VECTOR_DB_PERSIST_DIR: str = "./vector_db"
    VECTOR_DB_USE_LOCAL: bool = True
    VECTOR_DB_HOST: Optional[str] = None
    VECTOR_DB_PORT: Optional[int] = None
    VECTOR_DB_BATCH_SIZE: int = 100
    VECTOR_DB_MAX_CONCURRENT_BATCHES: int = 3

    # Matrix Bridge Hub Configuration
    MATRIX_HOMESERVER_URL: str = "https://matrix.org"
    MATRIX_ACCESS_TOKEN: Optional[str] = None
    MATRIX_USER_ID: Optional[str] = None
    MATRIX_DEVICE_ID: str = "MESH_BRIDGE_HUB"

    # Security Configuration
    SECURITY_ENCRYPTION_ENABLED: bool = True
    SECURITY_TOKEN_ENCRYPTION_ENABLED: bool = True
    SECURITY_KEY_ROTATION_ENABLED: bool = True
    SECURITY_AUDIT_RETENTION_DAYS: int = 2555  # 7 years for compliance
    SECURITY_IMMUTABLE_AUDIT_LOGS: bool = True
    SECURITY_KMS_KEY_ID: Optional[str] = None
    MESH_MASTER_KEY: Optional[str] = None  # Base64 encoded master key

    # WhatsApp Bridge Configuration
    WHATSAPP_BRIDGE_ENABLED: bool = False
    WHATSAPP_BRIDGE_EXECUTABLE: str = "mautrix-whatsapp"
    WHATSAPP_BRIDGE_CONFIG_PATH: str = "./bridges/whatsapp/config.yaml"
    WHATSAPP_BRIDGE_DATABASE_PATH: str = "./bridges/whatsapp/whatsapp.db"

    # Instagram/Facebook Bridge Configuration
    INSTAGRAM_BRIDGE_ENABLED: bool = False
    INSTAGRAM_BRIDGE_EXECUTABLE: str = "mautrix-meta"
    INSTAGRAM_BRIDGE_CONFIG_PATH: str = "./bridges/instagram/config.yaml"
    INSTAGRAM_BRIDGE_DATABASE_PATH: str = "./bridges/instagram/meta.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Add validation before instantiation
if not os.getenv("DATABASE_URL"):
    raise ValueError("DATABASE_URL environment variable is required")

settings = Settings()
