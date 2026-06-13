"""Application configuration.

Single source of truth for settings, loaded from environment variables (and a
local `.env` at the repo root for host-run commands like Alembic migrations).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file: backend/core/config.py -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Database ----
    postgres_user: str = "stockuser"
    postgres_password: str = "stockpass"
    postgres_db: str = "stockdb"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # Optional explicit override; if unset it's derived from the parts above.
    database_url: str | None = None

    # ---- Auth / JWT ----
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # ---- Market data ----
    market_data_provider: str = "yfinance"
    seed_symbols: str = "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA"
    history_years: int = 5

    # ---- App ----
    environment: str = "development"
    log_level: str = "INFO"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def seed_symbol_list(self) -> list[str]:
        return [s.strip().upper() for s in self.seed_symbols.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (import this, not the class)."""
    return Settings()
