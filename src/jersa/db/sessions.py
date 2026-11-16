"""Koszyk i przechowalnia klienta w bazie: wiersze `CartRow` i `WishlistRow`.

Sklep zapisuje je pod identyfikatorem z ciasteczka klienta (`jersa_cart`, `jersa_wish`),
więc test sprząta własne wiersze po tych identyfikatorach.
"""

from collections.abc import Iterable

import psycopg

from jersa.db.connection import connect

CART_COOKIE = "jersa_cart"
WISH_COOKIE = "jersa_wish"


def delete_session_rows(
    conn: psycopg.Connection, *, cart_id: str | None, wish_id: str | None
) -> None:
    """Usuwa koszyk i przechowalnię o podanych identyfikatorach. Brak identyfikatora = pomijamy."""
    if cart_id:
        conn.execute('DELETE FROM "CartRow" WHERE id = %s', (cart_id,))
    if wish_id:
        conn.execute('DELETE FROM "WishlistRow" WHERE id = %s', (wish_id,))


def cleanup_sessions(
    database_url: str | None, sessions: Iterable[tuple[str | None, str | None]]
) -> None:
    """Sprząta koszyki i przechowalnie podanych klientów: pary (id koszyka, id przechowalni).

    Bez adresu bazy (np. STG) albo bez identyfikatora nie robi nic i nie łączy się z bazą."""
    ids = [pair for pair in sessions if pair[0] or pair[1]]
    if not database_url or not ids:
        return
    conn = connect(database_url)
    try:
        for cart_id, wish_id in ids:
            delete_session_rows(conn, cart_id=cart_id, wish_id=wish_id)
    finally:
        conn.close()
