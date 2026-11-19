import pytest

from jersa.clients.commerce import SHIPPING

pytestmark = pytest.mark.regression


def _cart_lines(shop):
    response = shop.cart()
    assert response.status_code == 200, response.text
    return response.json()["lines"]


@pytest.mark.smoke
def test_order_from_cart(shop, product):
    """A-ORD-01: zamówienie z koszyka zwraca identyfikator i token; koszyk jest potem pusty."""
    assert shop.add_to_cart(product.slug).status_code == 200
    response = shop.create_order()
    assert response.status_code == 200, response.text
    order = response.json()["order"]
    assert order["id"]
    assert order["publicToken"]
    assert order["id"] != order["publicToken"]
    assert _cart_lines(shop) == []


def test_order_from_empty_cart_is_rejected(shop):
    """A-ORD-02: zamówienie z pustego koszyka jest odrzucane."""
    response = shop.create_order()
    assert response.status_code == 400
    assert response.json() == {"error": "Koszyk jest pusty"}


def test_order_without_email_is_rejected(shop, product):
    """A-ORD-03: zamówienie bez e-maila jest odrzucane, koszyk zostaje."""
    shop.add_to_cart(product.slug)
    response = shop.create_order(email="")
    assert response.status_code == 400
    assert response.json() == {"error": "Brak e-maila"}
    assert len(_cart_lines(shop)) == 1


@pytest.mark.parametrize("field", list(SHIPPING))
def test_order_without_shipping_field_is_rejected(shop, product, field):
    """A-ORD-04: zamówienie bez jednego z pól adresu jest odrzucane, koszyk zostaje."""
    shop.add_to_cart(product.slug)
    response = shop.create_order(shipping={**SHIPPING, field: ""})
    assert response.status_code == 400
    assert response.json() == {"error": "Brak danych dostawy"}
    assert len(_cart_lines(shop)) == 1


def test_order_losing_last_unit_is_rejected(make_shop, make_product):
    """A-ORD-05: zamówienie, które przegrało z innym klientem ostatnią sztukę, jest odrzucane;
    koszyk zostaje."""
    scarce = make_product(stock={"36": 1})
    late, early = make_shop(), make_shop()
    assert late.add_to_cart(scarce.slug, "36").status_code == 200
    assert early.add_to_cart(scarce.slug, "36").status_code == 200
    assert early.create_order().status_code == 200

    response = late.create_order()
    assert response.status_code == 400
    assert response.json() == {"error": "Brak stanu"}
    assert [line["quantity"] for line in _cart_lines(late)] == [1]


def test_second_order_from_same_cart_is_rejected(shop, placed_order):
    """A-ORD-06: drugie zamówienie z tego samego koszyka jest odrzucane."""
    response = shop.create_order()
    assert response.status_code == 400
    assert response.json() == {"error": "Koszyk jest pusty"}
