import pytest
from playwright.sync_api import expect

from jersa.pages.product_page import ProductPage
from jersa.seed import SEED_SLUG


@pytest.mark.regression
def test_size_is_required(page):
    """E-02: dodanie do koszyka bez rozmiaru pokazuje komunikat, a koszyk zostaje pusty."""
    product_page = ProductPage(page)
    product_page.open(SEED_SLUG)
    product_page.add_to_cart()

    expect(product_page.size_alert).to_be_visible()
    cart = page.request.get("/api/commerce/cart")
    assert cart.status == 200
    assert cart.json()["lines"] == []
