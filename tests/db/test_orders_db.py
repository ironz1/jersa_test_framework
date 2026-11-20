"""Zamówienie złożone przez API sprawdzane w bazie: wiersz zamówienia i stan magazynowy."""

import json
from datetime import timedelta

import pytest

from jersa.clients.commerce import EMAIL, MADE_TO_MEASURE, SHIPPING, checkout_body
from jersa.db.orders import get_order, orders_of
from jersa.db.products import read_stock, set_hidden

pytestmark = pytest.mark.regression

CUSTOM_FIT_SURCHARGE = 100


def _order(shop, db):
    """Składa zamówienie z bieżącego koszyka i zwraca jego wiersz z bazy."""
    response = shop.create_order()
    assert response.status_code == 200, response.text
    row = get_order(db, response.json()["order"]["id"])
    assert row is not None, "zamówienie z odpowiedzi API nie istnieje w bazie"
    return row


def test_order_row_matches_request(db, shop, product):
    """D-ORD-01: wiersz zamówienia zawiera dane klienta, pozycje, sumę, status i termin."""
    assert shop.add_to_cart(product.slug, "36", quantity=2).status_code == 200
    row = _order(shop, db)

    assert row["email"] == EMAIL
    assert json.loads(row["shippingJson"]) == SHIPPING
    assert json.loads(row["linesJson"]) == [
        {
            "productSlug": product.slug,
            "size": "36",
            "quantity": 2,
            "customFit": False,
            "sizeSurcharge": 0,
        }
    ]
    assert row["total"] == product.price * 2
    assert row["status"] == "awaiting_payment"
    assert row["expiresAt"] - row["createdAt"] == timedelta(minutes=30)
    assert row["payuOrderId"] is None


def test_order_reserves_stock(db, shop, product):
    """D-ORD-02: zamówienie 2 sztuk zmniejsza stan rozmiaru o 2."""
    assert shop.add_to_cart(product.slug, "36", quantity=2).status_code == 200
    _order(shop, db)

    stock = read_stock(db, product.slug)
    assert stock["36"] == product.stock["36"] - 2
    assert stock["38"] == product.stock["38"]


def test_made_to_measure_order_keeps_stock(db, shop, product):
    """D-ORD-03: zamówienie na miarę kosztuje cenę + 100 zł i nie zmienia stanu."""
    added = shop.add_to_cart(product.slug, MADE_TO_MEASURE, custom_fit=True)
    assert added.status_code == 200
    row = _order(shop, db)

    assert row["total"] == product.price + CUSTOM_FIT_SURCHARGE
    assert read_stock(db, product.slug) == product.stock


def test_promo_price_goes_into_total(db, shop, make_product):
    """D-ORD-04: suma zamówienia jest liczona od ceny promocyjnej."""
    promo = make_product(amount=200, promo_percent=20)
    assert shop.add_to_cart(promo.slug, "36").status_code == 200
    row = _order(shop, db)

    assert row["total"] == 160


def test_promo_price_rounds_half_up(db, shop, make_product):
    """D-ORD-07: cena promocyjna z połówką złotego jest zaokrąglana w górę."""
    promo = make_product(amount=25, promo_percent=10)
    assert promo.price == 23
    assert shop.add_to_cart(promo.slug, "36").status_code == 200
    row = _order(shop, db)

    assert row["total"] == 23


def _buy_last_unit_first(make_shop, slug, size):
    """Drugi klient kupuje ostatnią sztukę rozmiaru. Zwraca ID jego zamówienia."""
    early = make_shop()
    assert early.add_to_cart(slug, size).status_code == 200
    response = early.create_order()
    assert response.status_code == 200, response.text
    return response.json()["order"]["id"]


def test_rejected_order_leaves_no_trace(db, make_shop, make_product):
    """D-ORD-05: zamówienie, które przegrało wyścig o ostatnią sztukę, nie zostawia wiersza
    ani zmiany stanu."""
    scarce = make_product(stock={"36": 1})
    late = make_shop()
    assert late.add_to_cart(scarce.slug, "36").status_code == 200
    winner_id = _buy_last_unit_first(make_shop, scarce.slug, "36")
    assert late.create_order().status_code == 400

    assert [row["id"] for row in orders_of(db, scarce.slug)] == [winner_id]
    assert read_stock(db, scarce.slug) == {"36": 0}


def test_rejected_order_with_several_lines_changes_nothing(db, make_shop, make_product):
    """D-ORD-06: gdy druga pozycja przegrała wyścig o ostatnią sztukę, nie zmienia się też stan
    pierwszej."""
    mixed = make_product(stock={"36": 5, "38": 1})
    late = make_shop()
    assert late.add_to_cart(mixed.slug, "36").status_code == 200
    assert late.add_to_cart(mixed.slug, "38").status_code == 200
    winner_id = _buy_last_unit_first(make_shop, mixed.slug, "38")
    response = late.create_order()
    assert response.status_code == 400
    assert response.json() == {"error": "Brak stanu"}

    assert [row["id"] for row in orders_of(db, mixed.slug)] == [winner_id]
    assert read_stock(db, mixed.slug) == {"36": 5, "38": 0}


def test_order_with_hidden_product_leaves_no_trace(db, shop, make_product):
    """D-ORD-08: odrzucone zamówienie z produktem ukrytym po dodaniu do koszyka nie zostawia
    wiersza ani zmiany stanu."""
    hidden_later = make_product(stock={"36": 3})
    assert shop.add_to_cart(hidden_later.slug, "36").status_code == 200
    set_hidden(db, hidden_later.slug, True)
    assert shop.checkout_order(checkout_body()).status_code == 400

    assert orders_of(db, hidden_later.slug) == []
    assert read_stock(db, hidden_later.slug) == {"36": 3}
