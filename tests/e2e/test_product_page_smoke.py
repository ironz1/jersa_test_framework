import pytest
from playwright.sync_api import expect

from jersa.pages.product_page import ProductPage


@pytest.mark.smoke
def test_product_page_shows_name(page):
    product = ProductPage(page)
    product.open("zakiet-castello")
    expect(product.heading).to_have_text("Żakiet CASTELLO")
