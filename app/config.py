from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SECRET = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio"
    secret_key: str = DEFAULT_SECRET
    access_token_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173"

    site_url: str = "http://localhost:5173"
    site_title: str = "Anish Tilloo"
    site_description: str = (
        "Notes and articles on full-stack engineering, PostgreSQL and LLM tooling."
    )

    # If this folder exists, the API also serves the built Vue app from it,
    # so one process can run the whole site in production.
    frontend_dist: Path = BACKEND_DIR.parent / "frontend" / "dist"

    @field_validator("database_url")
    @classmethod
    def use_asyncpg_driver(cls, value: str) -> str:
        # Hosting providers hand out postgres:// or postgresql:// URLs.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
