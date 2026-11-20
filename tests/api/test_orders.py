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


BAD_FORMATS = [
    ("email", "abc", "Nieprawidłowy e-mail"),
    ("email", "a@b", "Nieprawidłowy e-mail"),
    ("postalCode", "90001", "Nieprawidłowy kod pocztowy"),
    ("postalCode", "xyz", "Nieprawidłowy kod pocztowy"),
    ("phone", "12345678", "Nieprawidłowy telefon"),
    ("phone", "abc", "Nieprawidłowy telefon"),
]
GOOD_PHONES = ["+48 500 000 000", "500-000-000", "+48500000000"]


@pytest.mark.parametrize(("field", "value", "error"), BAD_FORMATS)
def test_order_with_invalid_format_is_rejected(shop, product, field, value, error):
    """A-ORD-07: zamówienie z e-mailem, kodem pocztowym albo telefonem w złym formacie jest
    odrzucane; koszyk zostaje."""
    shop.add_to_cart(product.slug)
    if field == "email":
        response = shop.create_order(email=value)
    else:
        response = shop.create_order(shipping={**SHIPPING, field: value})
    assert response.status_code == 400
    assert response.json() == {"error": error}
    assert len(_cart_lines(shop)) == 1


@pytest.mark.parametrize("phone", GOOD_PHONES)
def test_order_accepts_phone_with_separators(shop, product, phone):
    """A-ORD-08: telefon z +48, spacjami albo myślnikami jest przyjmowany."""
    shop.add_to_cart(product.slug)
    response = shop.create_order(shipping={**SHIPPING, "phone": phone})
    assert response.status_code == 200, response.text


def test_second_order_from_same_cart_is_rejected(shop, placed_order):
    """A-ORD-06: drugie zamówienie z tego samego koszyka jest odrzucane."""
    response = shop.create_order()
    assert response.status_code == 400
    assert response.json() == {"error": "Koszyk jest pusty"}
