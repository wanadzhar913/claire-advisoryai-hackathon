import os
import sys
from pathlib import Path
from functools import lru_cache
from typing import List, Literal, Dict, ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError, TypeAdapter, field_validator, AnyHttpUrl

# project root directory
BASIC_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASIC_DIR.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BASIC_DIR))

class AppSettings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    BACKEND_PROJECT_NAME: str = "Claire API"
    BACKEND_API_V1_STR: str = "/api/v1"
    BACKEND_API_VERSION: str = "0.1.0"
    BACKEND_API_ENVIRONMENT: Literal["development", "production"] = "development"
    BACKEND_API_DESCRIPTION: str = "Claire API"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "t", "yes")

    # OpenAI settings
    OPENAI_API_KEY: str
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    DEFAULT_LLM_TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 16384
    MAX_LLM_CALL_RETRIES: int = 3

    # Long term memory Configuration
    LONG_TERM_MEMORY_MODEL: str = os.getenv("LONG_TERM_MEMORY_MODEL", "gpt-5-nano")
    LONG_TERM_MEMORY_EMBEDDER_MODEL: str = os.getenv("LONG_TERM_MEMORY_EMBEDDER_MODEL", "text-embedding-3-small")
    LONG_TERM_MEMORY_COLLECTION_NAME: str = os.getenv("LONG_TERM_MEMORY_COLLECTION_NAME", "longterm_memory")

    # Database settings
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 5
    CHECKPOINT_TABLES: List[str] = ["checkpoint_blobs", "checkpoint_writes", "checkpoints"]

    # Minio settings
    MINIO_ENDPOINT: str
    MINIO_SECURE: int = 0 # 0 for http, 1 for https
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_SECRET_KEY: str
    MINIO_ACCESS_KEY: str
    MINIO_BUCKET_NAME: str

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = 'INFO'
    LOG_FORMAT: str = "console"
    LOG_DIR: Path = Path("/app/backend/logs")

    # Clerk Authentication settings
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: str
    CLERK_JWKS_URL: str  

@lru_cache
def get_settings() -> AppSettings:
    """Load settings once and cache globally."""
    return AppSettings()

# Global singleton-style instance
settings = get_settings()

if __name__ == "__main__":
    print(settings)