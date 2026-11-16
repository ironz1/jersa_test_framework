from uuid import uuid4

import pytest

pytestmark = pytest.mark.regression


def _payment_page(order_id: str) -> str:
    return f"/preview/platnosc?order={order_id}"


@pytest.mark.smoke
def test_start_payment_returns_payment_page(shop, placed_order):
    """A-PAY-01: start płatności zwraca adres strony płatności."""
    response = shop.start_payment(placed_order.id)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "redirectUrl": _payment_page(placed_order.id)}


def test_start_payment_twice_returns_same_url(shop, placed_order):
    """A-PAY-02: start płatności dwa razy zwraca ten sam adres."""
    first = shop.start_payment(placed_order.id).json()
    second = shop.start_payment(placed_order.id).json()
    assert first["ok"] is True
    assert second == first


def test_start_payment_for_unknown_order_is_rejected(shop):
    """A-PAY-03: start płatności dla nieistniejącego zamówienia jest odrzucany."""
    response = shop.start_payment(str(uuid4()))
    assert response.status_code == 400
    assert response.json() == {"error": "Nie znaleziono zamówienia"}


def test_start_payment_without_order_id_is_rejected(shop):
    """A-PAY-04: start płatności bez identyfikatora zamówienia jest odrzucany."""
    response = shop.client.post("/api/commerce/payu/start", json={})
    assert response.status_code == 400
    assert response.json() == {"error": "Brak zamówienia"}


@pytest.mark.smoke
def test_completed_payment_leads_to_order_page(shop, placed_order):
    """A-PAY-05: po udanej płatności start płatności prowadzi na stronę zamówienia."""
    notified = shop.notify(placed_order.id, "COMPLETED")
    assert notified.status_code == 200
    assert notified.json() == {"ok": True, "duplicate": False}
    started = shop.start_payment(placed_order.id)
    assert started.json() == {
        "ok": True,
        "redirectUrl": f"/zamowienie/{placed_order.public_token}?paid=1",
    }


def test_second_completed_is_duplicate(shop, placed_order):
    """A-PAY-06: drugie powiadomienie o udanej płatności jest duplikatem."""
    assert shop.notify(placed_order.id, "COMPLETED").json() == {"ok": True, "duplicate": False}
    assert shop.notify(placed_order.id, "COMPLETED").json() == {"ok": True, "duplicate": True}


def test_canceled_payment_makes_order_unavailable(shop, placed_order):
    """A-PAY-07: po anulowaniu płatności zamówienia nie da się opłacić."""
    assert shop.notify(placed_order.id, "CANCELED").status_code == 200
    started = shop.start_payment(placed_order.id)
    assert started.status_code == 200
    assert started.json() == {"ok": False, "reason": "unavailable"}


def test_pending_changes_nothing(shop, placed_order):
    """A-PAY-08: płatność w toku niczego nie zmienia."""
    before = shop.start_payment(placed_order.id).json()
    notified = shop.notify(placed_order.id, "PENDING")
    assert notified.status_code == 200
    assert notified.json() == {"ok": True, "duplicate": False}
    after = shop.start_payment(placed_order.id).json()
    assert before == after == {"ok": True, "redirectUrl": _payment_page(placed_order.id)}


def test_unknown_status_is_rejected(shop, placed_order):
    """A-PAY-09: powiadomienie z nieznanym statusem jest odrzucane."""
    response = shop.notify(placed_order.id, "REFUNDED")
    assert response.status_code == 400
    assert response.json() == {"error": "Nieznany status"}


def test_completed_after_canceled_stays_canceled(shop, placed_order):
    """A-PAY-10: udana płatność po anulowaniu nie zmienia statusu."""
    assert shop.notify(placed_order.id, "CANCELED").status_code == 200
    late = shop.notify(placed_order.id, "COMPLETED")
    assert late.status_code == 200
    assert late.json() == {"ok": True, "duplicate": True}
    assert shop.start_payment(placed_order.id).json() == {"ok": False, "reason": "unavailable"}


def test_canceled_after_completed_stays_paid(shop, placed_order):
    """A-PAY-11: anulowanie po udanej płatności nie zmienia statusu: zamówienie zostaje opłacone."""
    assert shop.notify(placed_order.id, "COMPLETED").status_code == 200
    late = shop.notify(placed_order.id, "CANCELED")
    assert late.status_code == 200
    assert late.json() == {"ok": True, "duplicate": True}
    started = shop.start_payment(placed_order.id)
    assert started.json() == {
        "ok": True,
        "redirectUrl": f"/zamowienie/{placed_order.public_token}?paid=1",
    }
