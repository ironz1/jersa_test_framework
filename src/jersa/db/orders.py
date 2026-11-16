"""Odczyt zamówień (`OrderRow`) do asercji w testach bazy."""

from typing import Any

import psycopg

from jersa.db.products import lines_pattern


def get_order(conn: psycopg.Connection, order_id: str) -> dict[str, Any] | None:
    return conn.execute('SELECT * FROM "OrderRow" WHERE id = %s', (order_id,)).fetchone()


def order_id_by_token(conn: psycopg.Connection, public_token: str) -> str:
    row = conn.execute(
        'SELECT id FROM "OrderRow" WHERE "publicToken" = %s', (public_token,)
    ).fetchone()
    if row is None:
        raise LookupError(f"Brak zamówienia z tokenem '{public_token}'")
    return row["id"]


def orders_of(conn: psycopg.Connection, slug: str) -> list[dict[str, Any]]:
    """Zamówienia zawierające produkt o podanym slugu."""
    return conn.execute(
        'SELECT * FROM "OrderRow" WHERE "linesJson" LIKE %s ORDER BY "createdAt"',
        (lines_pattern(slug),),
    ).fetchall()


def backdate_expiry(conn: psycopg.Connection, order_id: str) -> None:
    """Cofa termin płatności własnego zamówienia o godzinę wstecz, żeby sklep uznał je za
    przeterminowane. Sklep zapisuje czas w UTC bez strefy."""
    conn.execute(
        """UPDATE "OrderRow" SET "expiresAt" = (now() at time zone 'utc') - interval '1 hour'
        WHERE id = %s""",
        (order_id,),
    )
