import pytest


@pytest.mark.smoke
def test_new_session_gets_empty_cart(api_client):
    response = api_client.get("/api/commerce/cart")
    assert response.status_code == 200
    assert response.json()["lines"] == []
    assert "jersa_cart" in api_client.cookies
