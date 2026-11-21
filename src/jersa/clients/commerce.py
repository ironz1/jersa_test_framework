"""Operacje klienta sklepu na API `/api/commerce/*`: jedna metoda na endpoint.

Metody zwracają surową odpowiedź i nie sprawdzają statusu: status sprawdza test.
"""

from typing import Any

import requests

from jersa.clients.api_client import ApiClient

EMAIL = "klientka@example.com"
MADE_TO_MEASURE = "made-to-measure"
SHIPPING = {
    "name": "Anna Nowak",
    "street": "Piotrkowska 1",
    "city": "Łódź",
    "postalCode": "90-001",
    "phone": "500000000",
}
# Kupująca w kasie (`/kasa`): klucze jak w polu `checkout` zamówienia sklepu.
BUYER = {
    "firstName": "Anna",
    "lastName": "Nowak",
    "phone": "500000000",
    "street": "Piotrkowska 1",
    "postalCode": "90-001",
    "city": "Łódź",
}
# Metody dostawy kasy (Polska) i ich ceny w złotych, z listy sklepu.
SHIPPING_METHODS = {
    "odbior-osobisty": 0,
    "kurier-dpd": 15,
    "kurier-dpd-pobranie": 20,
}


def checkout_body(**overrides: object) -> dict[str, object]:
    """Pełne poprawne pole `checkout` zamówienia: osoba prywatna z Polski, Kurier DPD przelew,
    regulamin zaakceptowany. Test nadpisuje tylko to, co sprawdza."""
    body: dict[str, object] = {
        **BUYER,
        "email": EMAIL,
        "buyerKind": "private",
        "companyName": "",
        "nip": "",
        "country": "Polska",
        "shipToDifferentAddress": False,
        "shipStreet": "",
        "shipPostalCode": "",
        "shipCity": "",
        "shipCountry": "",
        "notes": "",
        "termsAccepted": True,
        "shippingMethodId": "kurier-dpd",
    }
    return {**body, **overrides}


_CART = "/api/commerce/cart"
_ORDERS = "/api/commerce/orders"
_PAYU_START = "/api/commerce/payu/start"
_PAYU_NOTIFY = "/api/commerce/payu/notify"
_DISCOUNT = "/api/commerce/discount"
_WISHLIST = "/api/commerce/wishlist"
_REVIEWS = "/api/commerce/reviews"
_SEARCH = "/api/commerce/search"


class CommerceApi:
    """Jeden klient sklepu: własna sesja, czyli własny koszyk i przechowalnia."""

    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def cart(self) -> requests.Response:
        return self.client.get(_CART)

    def add_to_cart(
        self, slug: str, size: str = "36", quantity: int = 1, custom_fit: bool = False
    ) -> requests.Response:
        body = {"productSlug": slug, "size": size, "quantity": quantity, "customFit": custom_fit}
        return self.client.post(_CART, json=body)

    def set_quantity(self, line_id: str, quantity: int) -> requests.Response:
        return self.client.patch(_CART, json={"lineId": line_id, "quantity": quantity})

    def remove_line(self, line_id: str) -> requests.Response:
        return self.client.delete(_CART, json={"lineId": line_id})

    def create_order(
        self, email: str = EMAIL, shipping: dict[str, Any] | None = None
    ) -> requests.Response:
        address = dict(SHIPPING) if shipping is None else shipping
        return self.client.post(_ORDERS, json={"email": email, "shipping": address})

    def checkout_order(self, checkout: dict[str, object]) -> requests.Response:
        """Zamówienie przez kasę (`/kasa`): pole `checkout` z danymi kupującej i dostawą."""
        return self.client.post(_ORDERS, json={"checkout": checkout})

    def apply_discount(self, code: str) -> requests.Response:
        """Kod rabatowy na koszyku. Pusty kod zdejmuje rabat."""
        return self.client.post(_DISCOUNT, json={"code": code})

    def start_payment(self, order_id: str) -> requests.Response:
        return self.client.post(_PAYU_START, json={"orderId": order_id})

    def notify(
        self, order_id: str, status: str, total_amount: str | None = None
    ) -> requests.Response:
        """Powiadomienie o płatności, takie jak wysyła operator płatności. `total_amount` to
        kwota w groszach jako tekst (jak w PayU); bez niej sklep kwoty nie sprawdza."""
        body = {"orderId": order_id, "extOrderId": order_id, "status": status}
        if total_amount is not None:
            body["totalAmount"] = total_amount
        return self.client.post(_PAYU_NOTIFY, json=body)

    def wishlist(self) -> requests.Response:
        return self.client.get(_WISHLIST)

    def add_wish(self, slug: str) -> requests.Response:
        return self.client.post(_WISHLIST, json={"productSlug": slug})

    def remove_wish(self, slug: str) -> requests.Response:
        return self.client.delete(_WISHLIST, json={"productSlug": slug})

    def reviews(self, slug: str) -> requests.Response:
        return self.client.get(_REVIEWS, params={"productSlug": slug})

    def add_review(self, slug: str, author: str, body: str) -> requests.Response:
        return self.client.post(
            _REVIEWS, json={"productSlug": slug, "author": author, "body": body}
        )

    def search(self, q: str) -> requests.Response:
        return self.client.get(_SEARCH, params={"q": q})
