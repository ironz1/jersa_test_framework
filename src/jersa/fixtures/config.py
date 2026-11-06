import pytest

from jersa.config import Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Konfiguracja na całą sesję. Brak albo zły BASE_URL kończy się błędem walidacji."""
    return Settings()
