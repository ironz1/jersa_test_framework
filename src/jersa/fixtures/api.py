from collections.abc import Iterator

import pytest

from jersa.clients.api_client import ApiClient


@pytest.fixture
def api_client(base_url: str) -> Iterator[ApiClient]:
    """Nowy klient na każdy test: nowa sesja i nowe ciasteczka, czyli własny koszyk."""
    client = ApiClient(base_url)
    yield client
    client.close()
