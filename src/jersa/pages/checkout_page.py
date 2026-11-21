"""Kasa: `/kasa`. Formularz zamówienia gościa: dane, adres, regulamin, dostawa."""

import re
from collections.abc import Mapping

from playwright.sync_api import Locator, Page

# Cennik dostaw z kasy sklepu (Polska). Zmiana cennika w sklepie wymaga zmiany tutaj.
COURIER = "Kurier DPD przelew"
COURIER_PRICE = 15

# Pełna etykieta pola na stronie → klucz kupującej (jak w polu `checkout` zamówienia).
_BUYER_FIELDS = {
    "Imię": "firstName",
    "Nazwisko": "lastName",
    "Telefon": "phone",
    "Ulica i nr domu": "street",
    "Kod pocztowy": "postalCode",
    "Miasto": "city",
}


class CheckoutPage:
    def __init__(self, page: Page) -> None:
        self._page = page

    def _field(self, label: str) -> Locator:
        # Cała etykieta, z gwiazdką pola wymaganego albo bez: „Kod” nie złapie „Kod pocztowy”.
        return self._page.get_by_label(re.compile(rf"^{re.escape(label)}( \*)?$"))

    def fill(self, email: str, buyer: Mapping[str, str]) -> None:
        self._field("E-mail").fill(email)
        for label, key in _BUYER_FIELDS.items():
            self._field(label).fill(buyer[key])

    def choose_delivery(self, name: str) -> None:
        self._page.get_by_role("radio", name=re.compile(re.escape(name))).check()

    def accept_terms(self) -> None:
        self._page.get_by_role("checkbox", name=re.compile("regulaminem")).check()

    def submit(self) -> None:
        self._page.get_by_role("button", name="potwierdzam zakup").click()
