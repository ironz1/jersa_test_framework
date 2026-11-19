import pytest

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_discount_matches_contract(shop, product, make_discount_code, assert_matches_schema):
    """K-10: odpowiedź na kod rabatowy zgodna ze schematem."""
    assert shop.add_to_cart(product.slug).status_code == 200
    response = shop.apply_discount(make_discount_code().code)
    assert response.status_code == 200
    assert_matches_schema(response.json(), "discount")
