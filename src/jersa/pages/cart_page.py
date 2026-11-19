"""Koszyk: `/koszyk`. Pozycje, kod rabatowy i przejście do kasy."""

import re

from playwright.sync_api import Locator, Page


class CartPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self) -> None:
        self._page.goto("/koszyk")

    def apply_code(self, code: str) -> None:
        """Wpisuje kod i klika Zastosuj; czeka, aż sklep odpowie na kod."""
        self._page.get_by_label("Kod rabatowy").fill(code)
        with self._page.expect_response(
            lambda response: (
                "/api/commerce/discount" in response.url and response.request.method == "POST"
            )
        ):
            self._page.get_by_role("button", name="Zastosuj").click()

    def discount(self, code: str) -> Locator:
        """Wiersz rabatu w podsumowaniu koszyka: „Rabat <kod>”."""
        return self._page.get_by_text(f"Rabat {code}", exact=True)

    def go_to_checkout(self) -> None:
        self._page.get_by_role("link", name=re.compile("Płacę", re.IGNORECASE)).click()
