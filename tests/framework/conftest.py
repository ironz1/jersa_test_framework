import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    """Autouse `_verify_url` z pytest-base-url wymusza fixture `base_url` w każdej sesji.
    Testy frameworka nie mogą zależeć od `.env` (CI go nie ma), więc dostają adres zastępczy."""
    return "http://framework-tests.invalid"


class RecordingClient:
    """Atrapa `ApiClient`: zapisuje wywołania zamiast wysyłać żądania."""

    def __init__(self):
        self.calls = []

    def _record(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return "response"

    def get(self, path, **kwargs):
        return self._record("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self._record("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self._record("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self._record("DELETE", path, **kwargs)


@pytest.fixture
def recording_client() -> RecordingClient:
    """Atrapa klienta HTTP dla testów klientów API (`CommerceApi`, `AdminApi`)."""
    return RecordingClient()
