"""Wyniki wyszukiwania: `/szukaj?q=<fraza>`."""

import re
from urllib.parse import quote

from playwright.sync_api import Locator, Page


class SearchPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self, query: str) -> None:
        self._page.goto(f"/szukaj?q={quote(query)}")

    def result(self, name: str) -> Locator:
        return self._page.get_by_role("link", name=re.compile(re.escape(name)))
