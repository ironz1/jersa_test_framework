from jersa.db.sessions import delete_session_rows


class RecordingConnection:
    def __init__(self):
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((query, params))


def test_deletes_cart_and_wishlist_rows_by_id():
    conn = RecordingConnection()
    delete_session_rows(conn, cart_id="c-1", wish_id="w-1")
    assert conn.calls == [
        ('DELETE FROM "CartRow" WHERE id = %s', ("c-1",)),
        ('DELETE FROM "WishlistRow" WHERE id = %s', ("w-1",)),
    ]


def test_skips_missing_ids():
    conn = RecordingConnection()
    delete_session_rows(conn, cart_id=None, wish_id="w-1")
    assert conn.calls == [('DELETE FROM "WishlistRow" WHERE id = %s', ("w-1",))]
    delete_session_rows(conn, cart_id=None, wish_id=None)
    assert len(conn.calls) == 1


def test_cleanup_sessions_connects_once_and_closes(monkeypatch):
    from jersa.db import sessions

    conn = RecordingConnection()
    conn.closed = False
    conn.close = lambda: setattr(conn, "closed", True)
    urls = []
    monkeypatch.setattr(sessions, "connect", lambda url: urls.append(url) or conn)

    sessions.cleanup_sessions("postgresql://x", [("c-1", "w-1"), ("c-2", None)])

    assert urls == ["postgresql://x"]
    assert [call[1] for call in conn.calls] == [("c-1",), ("w-1",), ("c-2",)]
    assert conn.closed is True


def test_cleanup_sessions_without_database_or_ids_does_nothing(monkeypatch):
    from jersa.db import sessions

    def fail(url):
        raise AssertionError("połączenie nie powinno powstać")

    monkeypatch.setattr(sessions, "connect", fail)
    sessions.cleanup_sessions(None, [("c-1", "w-1")])
    sessions.cleanup_sessions("postgresql://x", [(None, None)])
