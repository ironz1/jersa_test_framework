"""Strona zamówienia: `/zamowienie/<token>`. Pokazuje status i sumę."""

import re
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page

URL_PATTERN = re.compile(r"/zamowienie/[^/?#]+")


class OrderPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    @property
    def token(self) -> str:
        """Publiczny token zamówienia z adresu strony."""
        return urlparse(self._page.url).path.rstrip("/").rsplit("/", 1)[-1]

    def status(self, text: str) -> Locator:
        return self._page.get_by_text(text, exact=True)

    @property
    def total(self) -> Locator:
        return self._page.get_by_text(re.compile(r"\d,\d{2} zł$"))
