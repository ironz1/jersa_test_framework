"""Połączenie z bazą sklepu (Postgres) do testów DB i fixtures danych."""

import psycopg  # moduł, nie funkcja: testy podmieniają psycopg.connect
from psycopg.rows import dict_row

CONNECT_TIMEOUT_S = 5


def connect(database_url: str) -> psycopg.Connection:
    """Autocommit (każde zapytanie od razu widoczne), wiersze jako słowniki,
    krótki timeout, żeby niedziałająca baza dawała błąd zamiast zawieszenia."""
    return psycopg.connect(
        database_url,
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=CONNECT_TIMEOUT_S,
    )
