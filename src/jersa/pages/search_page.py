"""Wyniki wyszukiwania: `/szukaj?q=<fraza>`."""

from urllib.parse import quote

from playwright.sync_api import Locator, Page

from jersa.pages.names import name_pattern


class SearchPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self, query: str) -> None:
        self._page.goto(f"/szukaj?q={quote(query)}")

    def result(self, slug: str, name: str) -> Locator:
        """Link do wyniku po dokładnym adresie produktu. Sama nazwa nie wystarcza: dwa produkty
        mogą mieć tę samą (`sukienka-stella` i `sukienka-stella1`)."""
        return self._page.locator(f'a[href="/produkt/{slug}"]').filter(has_text=name_pattern(name))
