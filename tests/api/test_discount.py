"""Kod rabatowy na koszyku: `POST /api/commerce/discount`, wynik widać w koszyku."""

from datetime import timedelta

import pytest

from jersa.clients.commerce import MADE_TO_MEASURE
from jersa.db.discount_codes import new_code, warsaw_today

pytestmark = pytest.mark.regression

INVALID = {"error": "Kod jest nieprawidłowy"}


def _discount(shop):
    """Kod i kwota rabatu z koszyka."""
    response = shop.cart()
    assert response.status_code == 200, response.text
    cart = response.json()
    return cart["discountCode"], cart["discountAmount"]


def _cart_with(shop, make_product, **product):
    """Koszyk z jedną sztuką własnego produktu w rozmiarze 36."""
    own = make_product(**product)
    assert shop.add_to_cart(own.slug, "36").status_code == 200
    return own


def test_percent_code(shop, make_product, make_discount_code):
    """A-DISC-01: kod procentowy daje rabat od sumy produktów; koszyk pokazuje kod i rabat."""
    _cart_with(shop, make_product, amount=200)
    code = make_discount_code(kind="percent", value=10)
    response = shop.apply_discount(code.code)
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "discount": 20}
    assert _discount(shop) == (code.code, 20)


def test_percent_rounds_half_up(shop, make_product, make_discount_code):
    """A-DISC-02: rabat procentowy zaokrąglany do pełnych złotych, połówki w górę."""
    _cart_with(shop, make_product, amount=25)
    code = make_discount_code(kind="percent", value=10)
    assert shop.apply_discount(code.code).json() == {"ok": True, "discount": 3}


@pytest.mark.parametrize(
    ("value", "expected"), [(50, 50), (300, 200)], ids=["mniej-niz-produkty", "wiecej"]
)
def test_amount_code_is_capped_at_products(shop, make_product, make_discount_code, value, expected):
    """A-DISC-03: kod kwotowy odejmuje swoją wartość, ale nie więcej niż suma produktów."""
    _cart_with(shop, make_product, amount=200)
    code = make_discount_code(kind="amount", value=value)
    assert shop.apply_discount(code.code).json() == {"ok": True, "discount": expected}


def test_discount_base_uses_sale_price(shop, make_product, make_discount_code):
    """A-DISC-04: podstawa rabatu to cena sprzedaży (po promocji)."""
    _cart_with(shop, make_product, amount=200, promo_percent=20)
    code = make_discount_code(kind="percent", value=10)
    assert shop.apply_discount(code.code).json() == {"ok": True, "discount": 16}


def test_discount_base_includes_custom_fit(shop, make_product, make_discount_code):
    """A-DISC-04: podstawa rabatu zawiera dopłatę za szycie na miarę."""
    tailored = make_product(amount=200)
    response = shop.add_to_cart(tailored.slug, MADE_TO_MEASURE, custom_fit=True)
    assert response.status_code == 200, response.text
    code = make_discount_code(kind="percent", value=10)
    assert shop.apply_discount(code.code).json() == {"ok": True, "discount": 30}


def test_code_ignores_letter_case(shop, make_product, make_discount_code):
    """A-DISC-05: kod działa bez względu na wielkość liter; koszyk pokazuje pisownię operatora."""
    _cart_with(shop, make_product, amount=200)
    code = make_discount_code(code=new_code().upper())
    assert shop.apply_discount(code.code.lower()).status_code == 200
    assert _discount(shop) == (code.code, 20)


@pytest.mark.parametrize("variant", ["nieznany", "wylaczony", "po-dacie"])
def test_invalid_code_is_rejected(shop, make_product, make_discount_code, variant):
    """A-DISC-06: kod nieznany, wyłączony albo po dacie końca jest odrzucany; brak rabatu."""
    _cart_with(shop, make_product)
    if variant == "nieznany":
        text = "test-nie-ma-takiego-kodu"
    elif variant == "wylaczony":
        text = make_discount_code(active=False).code
    else:
        text = make_discount_code(ends_on=warsaw_today() - timedelta(days=1)).code
    response = shop.apply_discount(text)
    assert response.status_code == 400
    assert response.json() == INVALID
    assert _discount(shop) == ("", 0)


@pytest.mark.parametrize("ends", ["dzis", "bez-daty"])
def test_code_valid_through_end_date(shop, make_product, make_discount_code, ends):
    """A-DISC-07: kod działa do dnia końca włącznie (Europe/Warsaw); bez daty nie wygasa."""
    _cart_with(shop, make_product, amount=200)
    ends_on = warsaw_today() if ends == "dzis" else None
    code = make_discount_code(ends_on=ends_on)
    assert shop.apply_discount(code.code).json() == {"ok": True, "discount": 20}


def test_empty_code_removes_discount(shop, make_product, make_discount_code):
    """A-DISC-08: puste pole kodu zdejmuje rabat z koszyka."""
    _cart_with(shop, make_product)
    shop.apply_discount(make_discount_code().code)
    assert shop.apply_discount("").json() == {"ok": True, "discount": 0}
    assert _discount(shop) == ("", 0)


def test_new_code_replaces_previous(shop, make_product, make_discount_code):
    """A-DISC-09: nowy kod zastępuje poprzedni; na koszyku jest jeden kod."""
    _cart_with(shop, make_product, amount=200)
    shop.apply_discount(make_discount_code(kind="percent", value=10).code)
    second = make_discount_code(kind="amount", value=20)
    assert shop.apply_discount(second.code).status_code == 200
    assert _discount(shop) == (second.code, 20)


def test_invalid_code_keeps_previous(shop, make_product, make_discount_code):
    """A-DISC-10: zły kod nie zdejmuje poprzedniego dobrego kodu (decyzja właściciela)."""
    _cart_with(shop, make_product, amount=200)
    first = make_discount_code(kind="percent", value=10)
    shop.apply_discount(first.code)
    response = shop.apply_discount("test-nie-ma-takiego-kodu")
    assert response.status_code == 400
    assert response.json() == INVALID
    assert _discount(shop) == (first.code, 20)
