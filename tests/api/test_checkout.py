"""Kasa przez API: `POST /api/commerce/orders` z polem `checkout` (formularz `/kasa`)."""

import pytest

from jersa.clients.commerce import checkout_body
from jersa.db.discount_codes import set_code_active

pytestmark = pytest.mark.regression

ONLY_POLAND = "Wysyłamy tylko do Polski. Napisz na marketing@jersa.pl"


def _cart(shop):
    response = shop.cart()
    assert response.status_code == 200, response.text
    return response.json()


def _rejected(shop, product, error, **overrides):
    """Kasa z nadpisanymi polami jest odrzucana z komunikatem, a koszyk zostaje."""
    assert shop.add_to_cart(product.slug).status_code == 200
    response = shop.checkout_order(checkout_body(**overrides))
    assert response.status_code == 400
    assert response.json() == {"error": error}
    assert [line["productSlug"] for line in _cart(shop)["lines"]] == [product.slug]


@pytest.mark.smoke
def test_checkout_order(shop, product, assert_matches_schema):
    """A-CHK-01: poprawna kasa składa zamówienie z identyfikatorem i tokenem; koszyk pusty."""
    assert shop.add_to_cart(product.slug).status_code == 200
    response = shop.checkout_order(checkout_body())
    assert response.status_code == 200, response.text
    assert_matches_schema(response.json(), "order-created")
    order = response.json()["order"]
    assert order["id"]
    assert order["publicToken"]
    assert _cart(shop)["lines"] == []


@pytest.mark.parametrize(
    ("field", "error"),
    [
        ("firstName", "Podaj imię"),
        ("lastName", "Podaj nazwisko"),
        ("email", "Podaj adres e-mail"),
        ("phone", "Podaj telefon"),
        ("street", "Podaj ulicę i numer domu"),
        ("postalCode", "Podaj kod pocztowy"),
        ("city", "Podaj miasto"),
    ],
)
@pytest.mark.parametrize("blank", ["", "  "], ids=["puste", "spacje"])
def test_checkout_without_required_field_is_rejected(shop, product, field, error, blank):
    """A-CHK-02: kasa bez wymaganego pola jest odrzucana z komunikatem; koszyk zostaje."""
    _rejected(shop, product, error, **{field: blank})


def test_checkout_without_terms_is_rejected(shop, product):
    """A-CHK-03: kasa bez akceptacji regulaminu jest odrzucana."""
    _rejected(shop, product, "Zaakceptuj regulamin", termsAccepted=False)


@pytest.mark.parametrize("method", ["", "paczkomat"], ids=["brak", "nieznana"])
def test_checkout_with_unknown_delivery_is_rejected(shop, product, method):
    """A-CHK-04: kasa bez metody dostawy albo z metodą spoza listy sklepu jest odrzucana."""
    _rejected(shop, product, "Wybierz metodę dostawy", shippingMethodId=method)


@pytest.mark.parametrize(
    ("company", "error"),
    [
        ({"companyName": "", "nip": "1234567890"}, "Podaj nazwę firmy"),
        ({"companyName": "Jersa sp. z o.o.", "nip": "123"}, "Podaj prawidłowy NIP"),
        ({"companyName": "Jersa sp. z o.o.", "nip": "12345678901"}, "Podaj prawidłowy NIP"),
    ],
    ids=["bez-nazwy", "nip-za-krotki", "nip-za-dlugi"],
)
def test_company_checkout_is_validated(shop, product, company, error):
    """A-CHK-05: kasa firmy wymaga nazwy firmy i NIP-u z 10 cyfr."""
    _rejected(shop, product, error, buyerKind="company", **company)


@pytest.mark.parametrize(
    "address",
    [
        {"country": "Niemcy"},
        {
            "shipToDifferentAddress": True,
            "shipStreet": "Hauptstraße 1",
            "shipPostalCode": "10115",
            "shipCity": "Berlin",
            "shipCountry": "Niemcy",
        },
    ],
    ids=["adres-rozliczeniowy", "drugi-adres"],
)
def test_checkout_outside_poland_is_rejected(shop, product, address):
    """A-CHK-06: kasa z krajem innym niż Polska jest odrzucana z prośbą o kontakt."""
    _rejected(shop, product, ONLY_POLAND, **address)


SECOND_ADDRESS = {
    "shipToDifferentAddress": True,
    "shipStreet": "Długa 5",
    "shipPostalCode": "00-001",
    "shipCity": "Warszawa",
    "shipCountry": "Polska",
}


@pytest.mark.parametrize(
    ("field", "error"),
    [
        ("shipStreet", "Podaj ulicę i numer domu wysyłki"),
        ("shipPostalCode", "Podaj kod pocztowy wysyłki"),
        ("shipCity", "Podaj miasto wysyłki"),
    ],
)
def test_second_address_requires_fields(shop, product, field, error):
    """A-CHK-07: zaznaczony drugi adres wymaga ulicy, kodu pocztowego i miasta."""
    _rejected(shop, product, error, **{**SECOND_ADDRESS, field: ""})


def test_code_disabled_before_order_is_rejected(shop, product, make_discount_code, db):
    """A-CHK-08: kod, który przestał działać przed złożeniem zamówienia, blokuje zamówienie;
    kod schodzi z koszyka, produkty zostają."""
    assert shop.add_to_cart(product.slug).status_code == 200
    code = make_discount_code()
    assert shop.apply_discount(code.code).status_code == 200
    set_code_active(db, code.id, False)

    response = shop.checkout_order(checkout_body())
    assert response.status_code == 400
    assert response.json() == {"error": "Kod jest nieprawidłowy"}
    # Koszyk przelicza kod przy każdym odczycie, więc wyłączony kod i tak nie byłby widoczny.
    # Po ponownym włączeniu kodu widać, czy sklep naprawdę zdjął go z koszyka.
    set_code_active(db, code.id, True)
    cart = _cart(shop)
    assert [line["productSlug"] for line in cart["lines"]] == [product.slug]
    assert cart["discountCode"] == ""
