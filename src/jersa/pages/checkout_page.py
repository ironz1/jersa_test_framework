"""Kasa: `/kasa`. Formularz zamówienia gościa."""

import re
from collections.abc import Mapping

from playwright.sync_api import Locator, Page

# Etykieta pola formularza → klucz w słowniku adresu (jak w API zamówień).
_SHIPPING_FIELDS = {
    "Imię": "name",
    "Ulica": "street",
    "Miasto": "city",
    "Kod": "postalCode",
    "Telefon": "phone",
}


class CheckoutPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def _field(self, label: str) -> Locator:
        return self._page.get_by_label(re.compile(label, re.IGNORECASE))

    def fill(self, email: str, shipping: Mapping[str, str]) -> None:
        self._field("e-mail").fill(email)
        for label, key in _SHIPPING_FIELDS.items():
            self._field(label).fill(shipping[key])

    def submit(self) -> None:
        self._page.get_by_role("button", name=re.compile("Zamawiam", re.IGNORECASE)).click()
