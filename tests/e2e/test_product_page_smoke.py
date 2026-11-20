import pytest
from playwright.sync_api import expect

from jersa.pages.product_page import ProductPage
from jersa.seed import SEED_NAME, SEED_SLUG


@pytest.mark.smoke
@pytest.mark.regression
def test_product_page_shows_name(page):
    product = ProductPage(page)
    product.open(SEED_SLUG)
    expect(product.heading).to_have_text(SEED_NAME)
