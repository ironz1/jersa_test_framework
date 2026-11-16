import re

import pytest
from playwright.sync_api import expect

from jersa.pages.product_page import ProductPage
from jersa.pages.search_page import SearchPage


@pytest.mark.regression
def test_search_leads_to_product(page):
    """E-03: wyszukanie produktu i przejście na jego stronę."""
    search = SearchPage(page)
    search.open("castello")
    search.result("Żakiet CASTELLO").click()

    expect(page).to_have_url(re.compile(r"/produkt/zakiet-castello$"))
    expect(ProductPage(page).heading).to_have_text("Żakiet CASTELLO")
