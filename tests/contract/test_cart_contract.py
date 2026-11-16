import pytest

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_empty_cart_matches_contract(shop, assert_matches_schema):
    """K-02: pusty koszyk zgodny ze schematem."""
    response = shop.cart()
    assert response.status_code == 200
    assert_matches_schema(response.json(), "cart")


def test_cart_with_line_matches_contract(shop, product, assert_matches_schema):
    """K-03: koszyk z pozycją i produktem zgodny ze schematem."""
    response = shop.add_to_cart(product.slug)
    assert response.status_code == 200
    body = response.json()
    assert body["lines"], "koszyk powinien mieć pozycję"
    assert body["lines"][0]["product"] is not None
    assert_matches_schema(body, "cart")
