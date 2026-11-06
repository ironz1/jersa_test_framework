"""Konfiguracja frameworka czytana z `.env` i zmiennych środowiskowych."""

from pathlib import Path
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/jersa/config.py → katalog projektu. Ścieżka absolutna, żeby .env był znaleziony
# niezależnie od katalogu, z którego uruchomiono pytest (np. IDE uruchamia z tests/...).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Cel testów. Zmienne środowiskowe wygrywają z plikiem `.env` (wygodne w CI)."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env zawiera też zmienne dla docker compose
    )

    base_url: str
    database_url: str | None = None
    admin_password: SecretStr | None = None

    @field_validator("base_url")
    @classmethod
    def _base_url_is_http(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"BASE_URL musi być adresem http(s)://host, a jest: {value!r}")
        return value.rstrip("/")

    @field_validator("database_url", mode="before")
    @classmethod
    def _empty_database_url_is_none(cls, value: object) -> object:
        return None if value == "" else value
