"""Zamówienie z kasy sprawdzane w bazie: suma, odpis kasy i adres wysyłki."""

import json

import pytest

from jersa.clients.commerce import BUYER, EMAIL, SHIPPING_METHODS, checkout_body
from jersa.db.discount_codes import set_code_active
from jersa.db.orders import get_order, orders_of
from jersa.db.products import read_stock

pytestmark = pytest.mark.regression


def _checkout(shop, db, **overrides):
    """Składa zamówienie przez kasę z bieżącego koszyka i zwraca jego wiersz z bazy."""
    response = shop.checkout_order(checkout_body(**overrides))
    assert response.status_code == 200, response.text
    row = get_order(db, response.json()["order"]["id"])
    assert row is not None, "zamówienie z odpowiedzi API nie istnieje w bazie"
    return row


def _cart_with_code(shop, make_product, make_discount_code, **code):
    """Koszyk: jeden własny produkt za 200 zł i kod rabatowy (domyślnie 10%)."""
    own = make_product(amount=200)
    assert shop.add_to_cart(own.slug, "36").status_code == 200
    discount = make_discount_code(**code)
    assert shop.apply_discount(discount.code).status_code == 200
    return own, discount


@pytest.mark.parametrize(("method", "price"), list(SHIPPING_METHODS.items()))
def test_total_includes_discount_and_delivery(
    db, shop, make_product, make_discount_code, method, price
):
    """D-CHK-01: suma zamówienia = produkty − rabat + cena dostawy z listy sklepu."""
    _cart_with_code(shop, make_product, make_discount_code)
    row = _checkout(shop, db, shippingMethodId=method)
    assert row["total"] == 200 - 20 + price


def test_client_delivery_price_is_ignored(db, shop, product):
    """D-CHK-02: cena dostawy przysłana przez przeglądarkę jest ignorowana."""
    assert shop.add_to_cart(product.slug).status_code == 200
    row = _checkout(shop, db, shippingMethodId="kurier-dpd", shippingPrice=0)
    assert row["total"] == product.price + SHIPPING_METHODS["kurier-dpd"]


def test_checkout_snapshot(db, shop, make_product, make_discount_code):
    """D-CHK-03: zamówienie zapisuje odpis kasy: kupująca, firma, adres rozliczeniowy, uwagi,
    regulamin, dostawa, kod i rabat; NIP jako 10 cyfr; e-mail z formularza."""
    _, discount = _cart_with_code(shop, make_product, make_discount_code)
    row = _checkout(
        shop,
        db,
        buyerKind="company",
        companyName="Jersa sp. z o.o.",
        nip="123-456-78 90",
        notes="Obwód w pasie 70 cm",
    )
    assert row["email"] == EMAIL
    assert json.loads(row["checkoutJson"]) == {
        "buyerKind": "company",
        "firstName": BUYER["firstName"],
        "lastName": BUYER["lastName"],
        "phone": BUYER["phone"],
        "companyName": "Jersa sp. z o.o.",
        "nip": "1234567890",
        "billing": {
            "street": BUYER["street"],
            "postalCode": BUYER["postalCode"],
            "city": BUYER["city"],
            "country": "Polska",
        },
        "notes": "Obwód w pasie 70 cm",
        "termsAccepted": True,
        "shippingMethodId": "kurier-dpd",
        "shippingMethodName": "Kurier DPD przelew",
        "shippingPrice": 15,
        "discountCode": discount.code,
        "discountAmount": 20,
    }


SECOND_ADDRESS = {"street": "Długa 5", "postalCode": "00-001", "city": "Warszawa"}


@pytest.mark.parametrize("second", [False, True], ids=["adres-z-formularza", "drugi-adres"])
def test_shipping_address(db, shop, product, second):
    """D-CHK-04: adres wysyłki to drugi adres, gdy był zaznaczony, w przeciwnym razie adres
    z formularza; imię i nazwisko oraz telefon z danych kupującej."""
    assert shop.add_to_cart(product.slug).status_code == 200
    extra = {}
    if second:
        extra = {
            "shipToDifferentAddress": True,
            "shipStreet": SECOND_ADDRESS["street"],
            "shipPostalCode": SECOND_ADDRESS["postalCode"],
            "shipCity": SECOND_ADDRESS["city"],
            "shipCountry": "Polska",
        }
    row = _checkout(shop, db, **extra)
    address = SECOND_ADDRESS if second else {k: BUYER[k] for k in ("street", "postalCode", "city")}
    assert json.loads(row["shippingJson"]) == {
        "name": f"{BUYER['firstName']} {BUYER['lastName']}",
        "phone": BUYER["phone"],
        **address,
    }


def test_snapshot_survives_code_disable(db, shop, make_product, make_discount_code):
    """D-CHK-05: wyłączenie kodu po złożeniu zamówienia nie zmienia odpisu ani sumy: sklep
    przyjmuje potem płatność na sumę z rabatem."""
    _, discount = _cart_with_code(shop, make_product, make_discount_code)
    before = _checkout(shop, db)
    set_code_active(db, discount.id, False)

    # Sklep musi coś zrobić z zamówieniem po wyłączeniu kodu; sam odczyt z bazy tego nie sprawdzi.
    paid = shop.notify(before["id"], "COMPLETED", total_amount="19500")
    assert paid.status_code == 200, paid.text
    after = get_order(db, before["id"])
    assert after["status"] == "paid"
    assert after["checkoutJson"] == before["checkoutJson"]
    assert after["total"] == before["total"] == 195


def test_rejected_checkout_leaves_no_order(db, shop, make_product):
    """D-CHK-06: odrzucona kasa nie zostawia zamówienia ani zmiany stanu."""
    own = make_product()
    assert shop.add_to_cart(own.slug, "36").status_code == 200
    response = shop.checkout_order(checkout_body(termsAccepted=False))
    assert response.status_code == 400
    assert orders_of(db, own.slug) == []
    assert read_stock(db, own.slug) == own.stock
