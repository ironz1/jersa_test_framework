import pytest

from jersa.config import Settings, is_headed


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, settings: Settings, pytestconfig):
    """Nadpisuje fixture z pytest-playwright: okno przeglądarki także przy `HEADED=true` w `.env`.
    Opcja `--headed` z linii poleceń działa jak dotąd."""
    headed = is_headed(bool(pytestconfig.getoption("headed")), settings.headed)
    return {**browser_type_launch_args, "headless": not headed}
