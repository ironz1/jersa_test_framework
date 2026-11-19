"""Operacje panelu admina na API `/api/admin/*`: jedna metoda na endpoint.

Metody zwracają surową odpowiedź i nie sprawdzają statusu: status sprawdza test.
"""

import requests

from jersa.clients.api_client import ApiClient

ADMIN_COOKIE = "jersa_admin"
_CODES = "/api/admin/discount-codes"


class AdminApi:
    """Klient panelu. Pamięta treść kodów, o których utworzenie prosił, żeby fixture mogła je
    po teście usunąć z bazy (panel umie kod tylko wyłączyć)."""

    def __init__(self, client: ApiClient) -> None:
        self.client = client
        self.created_codes: list[str] = []

    def codes(self) -> requests.Response:
        return self.client.get(_CODES)

    def create_code(
        self, code: str, kind: str, value: int, ends_on: str | None = None
    ) -> requests.Response:
        self.created_codes.append(code)
        body = {"code": code, "kind": kind, "value": value, "endsOn": ends_on}
        return self.client.post(_CODES, json=body)

    def disable_code(self, code_id: str) -> requests.Response:
        return self.client.post(_CODES, json={"id": code_id, "active": False})
