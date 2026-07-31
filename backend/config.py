"""
ContractIQ — Application Configuration

Loads settings from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://contractiq:contractiq@localhost:5432/contractiq"
    DATABASE_URL_SYNC: str = "postgresql://contractiq:contractiq@localhost:5432/contractiq"

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # --- AI API Keys ---
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # --- ChromaDB ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # --- File Uploads ---
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20

    # --- Backend ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = "http://localhost:8000"

    # --- Frontend ---
    FRONTEND_PORT: int = 8501

    # --- LiteLLM ---
    LITELLM_LOG: str = "DEBUG"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
