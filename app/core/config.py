from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env.example"

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_days: int = 7
    test_database_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings: 
    return Settings()