"""Strona produktu (PDP): `/produkt/<slug>`."""

import re

from playwright.sync_api import Locator, Page, Response

SIZE_REQUIRED = "Wybierz rozmiar albo dopasowanie do wymiarów klientki"


class ProductPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self, slug: str) -> None:
        # Ścieżka względna: pytest-playwright dokleja base_url z fixture.
        self._page.goto(f"/produkt/{slug}")

    @property
    def heading(self) -> Locator:
        return self._page.get_by_role("heading", level=1)

    def choose_size(self, code: str) -> None:
        self._page.get_by_role("button", name=code, exact=True).click()

    def add_to_cart(self) -> None:
        self._page.get_by_role("button", name=re.compile("Do koszyka", re.IGNORECASE)).click()

    @property
    def cart_drawer(self) -> Locator:
        """Szuflada koszyka, która wysuwa się po dodaniu produktu."""
        return self._page.get_by_role("dialog", name="Koszyk")

    def go_to_checkout(self) -> None:
        self.cart_drawer.get_by_role("link", name=re.compile("Płacę", re.IGNORECASE)).click()

    @property
    def size_alert(self) -> Locator:
        return self._page.get_by_role("alert").filter(has_text=SIZE_REQUIRED)

    def add_to_wishlist(self) -> Response:
        """Klika serduszko i czeka, aż sklep zapisze produkt w przechowalni."""
        with self._page.expect_response(
            lambda response: (
                "/api/commerce/wishlist" in response.url and response.request.method == "POST"
            )
        ) as saved:
            # Karty „Produkty powiązane” mają własne serduszka w linku do karty; serduszko
            # tego produktu jest jedynym poza linkiem.
            self._page.locator('button[aria-label="Dodaj do ulubionych"]:not(a button)').click()
        return saved.value
