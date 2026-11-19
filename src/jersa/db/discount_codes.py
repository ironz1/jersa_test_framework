"""Własne kody rabatowe testu w tabeli `DiscountCode`: wstawienie, zmiana, sprzątanie.

Kody są wspólne dla całego sklepu, więc test dostaje własny kod `test-<hex>` i usuwa go
po ID. Kodów operatora test nie rusza.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql

OWN_PREFIX = "test-"
WARSAW = ZoneInfo("Europe/Warsaw")


@dataclass(frozen=True)
class OwnDiscountCode:
    id: str
    code: str
    kind: str
    value: int


def new_code() -> str:
    return OWN_PREFIX + uuid.uuid4().hex[:12]


def warsaw_today() -> date:
    """Dzisiejsza data w Warszawie: według niej sklep liczy koniec ważności kodu."""
    return datetime.now(WARSAW).date()


def discount_code_row(
    code: str,
    *,
    kind: str = "percent",
    value: int = 10,
    ends_on: date | None = None,
    active: bool = True,
) -> dict[str, object]:
    """Wiersz `DiscountCode`. Datę końca sklep czyta jako dzień z czasu UTC, więc zapisujemy
    północ UTC tego dnia."""
    return {
        "id": str(uuid.uuid4()),
        "code": code,
        "kind": kind,
        "value": value,
        "endsOn": None if ends_on is None else datetime(*ends_on.timetuple()[:3], tzinfo=UTC),
        "active": active,
    }


def insert_discount_code(conn: psycopg.Connection, row: dict[str, object]) -> None:
    query = sql.SQL('INSERT INTO "DiscountCode" ({}) VALUES ({})').format(
        sql.SQL(", ").join(sql.Identifier(column) for column in row),
        sql.SQL(", ").join(sql.Placeholder() * len(row)),
    )
    conn.execute(query, list(row.values()))


def set_code_active(conn: psycopg.Connection, code_id: str, active: bool) -> None:
    conn.execute('UPDATE "DiscountCode" SET active = %s WHERE id = %s', (active, code_id))


def delete_discount_code(conn: psycopg.Connection, code_id: str) -> None:
    """Usuwa kod po ID, tylko kod testu (prefiks `test-`, bez względu na wielkość liter)."""
    conn.execute(
        'DELETE FROM "DiscountCode" WHERE id = %s AND lower(code) LIKE %s',
        (code_id, OWN_PREFIX + "%"),
    )


def code_ids(conn: psycopg.Connection, code: str) -> list[str]:
    """ID kodów testu o tej treści bez względu na wielkość liter (sprzątanie po panelu)."""
    rows = conn.execute(
        'SELECT id FROM "DiscountCode" WHERE lower(code) = lower(%s) AND lower(code) LIKE %s',
        (code, OWN_PREFIX + "%"),
    ).fetchall()
    return [row["id"] for row in rows]
