"""Uszkodzona treść JSON w każdym endpoincie sklepu, który przyjmuje treść żądania."""

import pytest

pytestmark = pytest.mark.regression

MALFORMED = {"data": "{oops", "headers": {"Content-Type": "application/json"}}
ENDPOINTS = [
    ("post", "/api/commerce/cart"),
    ("patch", "/api/commerce/cart"),
    ("delete", "/api/commerce/cart"),
    ("post", "/api/commerce/orders"),
    ("post", "/api/commerce/payu/start"),
    ("post", "/api/commerce/wishlist"),
    ("delete", "/api/commerce/wishlist"),
    ("post", "/api/commerce/reviews"),
    ("post", "/api/commerce/discount"),
]


@pytest.mark.parametrize(
    ("method", "path"),
    ENDPOINTS,
    ids=[f"{method.upper()} {path.removeprefix('/api/commerce/')}" for method, path in ENDPOINTS],
)
def test_malformed_json_is_rejected(shop, assert_matches_schema, method, path):
    """A-JSON-01: uszkodzony JSON jest odrzucany komunikatem „Nieprawidłowe dane” w kształcie
    błędu API."""
    response = getattr(shop.client, method)(path, **MALFORMED)
    assert response.status_code == 400
    assert response.json() == {"error": "Nieprawidłowe dane"}
    assert_matches_schema(response.json(), "error")


def test_malformed_payment_notification_is_rejected(shop):
    """A-JSON-02: uszkodzone powiadomienie o płatności jest odrzucane: „Brak zamówienia”.

    Ten endpoint czyta surową treść (do podpisu operatora płatności), więc z uszkodzonej treści
    nie wyczyta zamówienia i odpowiada jak przy jego braku.
    """
    response = shop.client.post("/api/commerce/payu/notify", **MALFORMED)
    assert response.status_code == 400
    assert response.json() == {"error": "Brak zamówienia"}
