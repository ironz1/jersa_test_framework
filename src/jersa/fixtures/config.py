import pytest

from jersa.config import ConfigError, Settings, load_settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Konfiguracja na całą sesję. Brak albo zły BASE_URL kończy test czytelnym komunikatem."""
    try:
        return load_settings()
    except ConfigError as error:
        pytest.fail(str(error), pytrace=False)
