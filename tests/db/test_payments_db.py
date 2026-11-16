"""Płatność i wygasanie zamówienia sprawdzane w bazie: status i stan magazynowy."""

import pytest

from jersa.db.orders import backdate_expiry, get_order
from jersa.db.products import read_stock

pytestmark = pytest.mark.regression


def test_completed_payment_marks_order_paid(db, shop, product, placed_order):
    """D-PAY-01: udana płatność ustawia status „paid” i nie zmienia stanu."""
    assert shop.notify(placed_order.id, "COMPLETED").status_code == 200

    assert get_order(db, placed_order.id)["status"] == "paid"
    stock = read_stock(db, product.slug)
    assert stock["36"] == product.stock["36"] - placed_order.quantity
    assert stock["38"] == product.stock["38"]


def test_canceled_payment_returns_stock(db, shop, product, placed_order):
    """D-PAY-02: anulowana płatność ustawia status „cancelled” i zwraca stan."""
    assert read_stock(db, product.slug)["36"] == product.stock["36"] - placed_order.quantity
    assert shop.notify(placed_order.id, "CANCELED").status_code == 200

    assert get_order(db, placed_order.id)["status"] == "cancelled"
    assert read_stock(db, product.slug) == product.stock


def test_expired_order_is_cancelled_and_restocked(db, shop, product, placed_order):
    """D-EXP-01: zamówienie po terminie zostaje anulowane, a stan wraca."""
    backdate_expiry(db, placed_order.id)
    started = shop.start_payment(placed_order.id)
    assert started.status_code == 200
    assert started.json() == {"ok": False, "reason": "unavailable"}

    assert get_order(db, placed_order.id)["status"] == "cancelled"
    assert read_stock(db, product.slug) == product.stock


def test_canceled_after_paid_keeps_order_paid(db, shop, product, placed_order):
    """D-PAY-03: anulowanie po udanej płatności nie zmienia statusu ani stanu."""
    assert shop.notify(placed_order.id, "COMPLETED").status_code == 200
    stock_after_payment = read_stock(db, product.slug)
    late = shop.notify(placed_order.id, "CANCELED")
    assert late.status_code == 200
    assert late.json() == {"ok": True, "duplicate": True}

    assert get_order(db, placed_order.id)["status"] == "paid"
    assert read_stock(db, product.slug) == stock_after_payment
