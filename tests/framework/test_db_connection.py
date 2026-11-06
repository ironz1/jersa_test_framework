import psycopg
from psycopg.rows import dict_row

from jersa.db.connection import connect


def test_connect_passes_timeout_and_autocommit(monkeypatch):
    seen = {}

    def fake_connect(url, **kwargs):
        seen.update(url=url, **kwargs)
        return "conn"

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    assert connect("postgresql://x") == "conn"
    assert seen["url"] == "postgresql://x"
    assert seen["autocommit"] is True
    assert seen["connect_timeout"] == 5
    assert seen["row_factory"] is dict_row
