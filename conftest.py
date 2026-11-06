import pytest

from jersa.config import Settings

pytest_plugins = [
    "jersa.fixtures.config",
    "jersa.fixtures.schemas",
]


@pytest.fixture(scope="session")
def base_url(settings: Settings) -> str:
    """Adres sklepu. Nadpisuje fixture z pytest-base-url, z której korzysta pytest-playwright,
    więc `page.goto("/produkt/...")` działa ze ścieżką względną."""
    return settings.base_url
