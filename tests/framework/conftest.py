import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    """Autouse `_verify_url` z pytest-base-url wymusza fixture `base_url` w każdej sesji.
    Testy frameworka nie mogą zależeć od `.env` (CI go nie ma), więc dostają adres zastępczy."""
    return "http://framework-tests.invalid"
