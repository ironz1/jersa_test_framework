"""Klient HTTP do API sklepu (BFF `/api/commerce/*`)."""

from typing import Any

import requests
from requests.cookies import RequestsCookieJar

DEFAULT_TIMEOUT = 10.0


class ApiClient:
    """Jedna sesja `requests` = jeden zestaw ciasteczek (koszyk, wishlist).

    Nie rzuca wyjątku na 4xx/5xx: status sprawdza test.
    """

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()

    def url(self, path: str) -> str:
        if not path.startswith("/"):
            raise ValueError(f"Ścieżka musi zaczynać się od '/', a jest: {path!r}")
        return self._base_url + path

    @property
    def cookies(self) -> RequestsCookieJar:
        return self._session.cookies

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("DELETE", path, **kwargs)

    def close(self) -> None:
        self._session.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self._timeout)
        return self._session.request(method, self.url(path), **kwargs)
