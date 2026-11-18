"""Typed environment settings loaded with pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings sourced from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str
    database_url: str
    test_database_url: str | None = None
    access_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance for the current process."""
    return Settings()