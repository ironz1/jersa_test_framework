import pytest

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_order_created_matches_contract(shop, product, assert_matches_schema):
    """K-06: utworzone zamówienie zgodne ze schematem."""
    assert shop.add_to_cart(product.slug).status_code == 200
    response = shop.create_order()
    assert response.status_code == 200
    assert_matches_schema(response.json(), "order-created")


def test_payment_start_matches_contract(shop, placed_order, assert_matches_schema):
    """K-07: udany start płatności zgodny ze schematem."""
    response = shop.start_payment(placed_order.id)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert_matches_schema(body, "payu-start")


def test_payment_unavailable_matches_contract(shop, placed_order, assert_matches_schema):
    """K-07: start płatności dla anulowanego zamówienia zgodny ze schematem."""
    assert shop.notify(placed_order.id, "CANCELED").status_code == 200
    response = shop.start_payment(placed_order.id)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert_matches_schema(body, "payu-start")


def test_payment_notify_matches_contract(shop, placed_order, assert_matches_schema):
    """K-08: odpowiedź na powiadomienie o płatności zgodna ze schematem."""
    response = shop.notify(placed_order.id, "COMPLETED")
    assert response.status_code == 200
    assert_matches_schema(response.json(), "payu-notify")
