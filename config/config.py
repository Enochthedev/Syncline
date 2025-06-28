from dotenv import load_dotenv
from pydantic_settings  import BaseSettings
import os

load_dotenv()  # This loads .env variables into the environment

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    class Config:
        case_sensitive = True

settings = Settings()  