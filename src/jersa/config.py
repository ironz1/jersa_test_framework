"""Konfiguracja frameworka czytana z `.env` i zmiennych środowiskowych."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import SecretStr, ValidationError, field_validator
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
        # Bez tego błąd walidacji wypisuje całe wejście, w tym hasła z innych zmiennych.
        hide_input_in_errors=True,
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


class ConfigError(RuntimeError):
    """Brakująca albo błędna konfiguracja, z komunikatem dla człowieka (bez wartości zmiennych)."""


def load_settings(**kwargs: Any) -> Settings:
    """`Settings()` z komunikatem wskazującym zmienne i `.env.example` zamiast śladu pydantic."""
    try:
        return Settings(**kwargs)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc']).upper()}: {item['msg']}"
            for item in error.errors()
        )
        raise ConfigError(
            f"Błędna konfiguracja ({problems}). Ustaw zmienne w .env (wzór: .env.example) "
            "albo jako zmienne środowiskowe."
        ) from None


def resolve_base_url(cli_base_url: str | None, settings_factory: Callable[[], Settings]) -> str:
    """Opcja `--base-url` (pytest-base-url) wygrywa z `.env`; bez niej adres z konfiguracji."""
    if cli_base_url:
        return cli_base_url.rstrip("/")
    return settings_factory().base_url
