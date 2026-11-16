import pytest

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_wishlist_matches_contract(shop, assert_matches_schema):
    """K-04: przechowalnia z produktem zgodna ze schematem."""
    response = shop.add_wish("zakiet-castello")
    assert response.status_code == 200
    body = response.json()
    assert body["products"], "przechowalnia powinna mieć produkt"
    assert_matches_schema(body, "wishlist")
