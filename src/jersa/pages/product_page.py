"""Strona produktu (PDP): `/produkt/<slug>`."""

from playwright.sync_api import Locator, Page


class ProductPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self, slug: str) -> None:
        # Ścieżka względna: pytest-playwright dokleja base_url z fixture.
        self._page.goto(f"/produkt/{slug}")

    @property
    def heading(self) -> Locator:
        return self._page.get_by_role("heading", level=1)
