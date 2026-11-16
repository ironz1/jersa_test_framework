from collections.abc import Callable, Iterator

import pytest

from jersa.clients.api_client import ApiClient
from jersa.clients.commerce import CommerceApi
from jersa.config import Settings
from jersa.db.sessions import CART_COOKIE, WISH_COOKIE, cleanup_sessions


@pytest.fixture
def api_client(base_url: str) -> Iterator[ApiClient]:
    """Nowy klient na każdy test: nowa sesja i nowe ciasteczka, czyli własny koszyk."""
    client = ApiClient(base_url)
    yield client
    client.close()


@pytest.fixture
def make_shop(base_url: str, settings: Settings) -> Iterator[Callable[[], CommerceApi]]:
    """Fabryka klientów sklepu. Każde wywołanie to osobna sesja (osobny koszyk),
    więc test może mieć dwóch niezależnych klientów.

    Po teście sesje są zamykane, a gdy skonfigurowano bazę, koszyk i przechowalnia każdego
    klienta są usuwane z bazy po identyfikatorze z ciasteczka (bez bazy np. na STG: pomijamy)."""
    clients: list[ApiClient] = []

    def _make() -> CommerceApi:
        client = ApiClient(base_url)
        clients.append(client)
        return CommerceApi(client)

    yield _make

    sessions = [
        (client.cookies.get(CART_COOKIE), client.cookies.get(WISH_COOKIE)) for client in clients
    ]
    for client in clients:
        client.close()
    cleanup_sessions(settings.database_url, sessions)


@pytest.fixture
def shop(make_shop: Callable[[], CommerceApi]) -> CommerceApi:
    """Jeden klient sklepu na test."""
    return make_shop()
