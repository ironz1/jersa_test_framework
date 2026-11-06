import pytest


@pytest.mark.smoke
@pytest.mark.contract
def test_search_matches_contract(api_client, assert_matches_schema):
    response = api_client.get("/api/commerce/search", params={"q": "castello"})
    assert response.status_code == 200
    body = response.json()
    assert body["products"], "seed powinien zwrócić CASTELLO"
    assert_matches_schema(body, "search")
