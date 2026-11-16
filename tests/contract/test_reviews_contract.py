import pytest

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_reviews_match_contract(shop, assert_matches_schema):
    """K-05: lista opinii zgodna ze schematem."""
    response = shop.reviews("zakiet-castello")
    assert response.status_code == 200
    body = response.json()
    assert body["reviews"], "seed powinien mieć opinie CASTELLO"
    assert_matches_schema(body, "reviews")
