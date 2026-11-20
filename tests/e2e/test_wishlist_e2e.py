import pytest
from playwright.sync_api import expect

from jersa.pages.product_page import ProductPage
from jersa.pages.wishlist_page import WishlistPage
from jersa.seed import SEED_NAME, SEED_SLUG


@pytest.mark.regression
def test_heart_adds_to_wishlist(page):
    """E-04: serduszko na stronie produktu dodaje go do przechowalni."""
    product_page = ProductPage(page)
    product_page.open(SEED_SLUG)
    saved = product_page.add_to_wishlist()
    assert saved.ok

    wishlist = WishlistPage(page)
    wishlist.open()
    expect(wishlist.heading).to_be_visible()
    expect(wishlist.item(SEED_NAME)).to_be_visible()
