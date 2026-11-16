import pytest

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_error_matches_contract(shop, product, assert_matches_schema):
    """K-09: błąd 400 zgodny ze schematem."""
    response = shop.add_to_cart(product.slug, size="")
    assert response.status_code == 400
    assert_matches_schema(response.json(), "error")
