from collections.abc import Iterator

import psycopg
import pytest

from jersa.config import Settings
from jersa.db.connection import connect


@pytest.fixture(scope="session")
def db(settings: Settings) -> Iterator[psycopg.Connection]:
    """Połączenie na całą sesję. Bez DATABASE_URL (np. STG) testy bazy są pomijane."""
    if settings.database_url is None:
        pytest.skip("DATABASE_URL nie jest ustawione, pomijam test bazy")
    conn = connect(settings.database_url)
    yield conn
    conn.close()
