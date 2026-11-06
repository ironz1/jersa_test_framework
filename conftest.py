import pytest

from jersa.config import resolve_base_url

pytest_plugins = [
    "jersa.fixtures.config",
    "jersa.fixtures.schemas",
    "jersa.fixtures.api",
    "jersa.fixtures.db",
]


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    """Adres sklepu. Nadpisuje fixture z pytest-base-url, z której korzysta pytest-playwright,
    więc `page.goto("/produkt/...")` działa ze ścieżką względną.
    `--base-url` z linii poleceń wygrywa z BASE_URL z .env."""
    return resolve_base_url(
        request.config.getoption("base_url"), lambda: request.getfixturevalue("settings")
    )
