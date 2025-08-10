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

    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly"

    class Config:
        env_file = ".env"
        case_sensitive = True

# Add validation before instantiation
if not os.getenv("DATABASE_URL"):
    raise ValueError("DATABASE_URL environment variable is required")

settings = Settings()