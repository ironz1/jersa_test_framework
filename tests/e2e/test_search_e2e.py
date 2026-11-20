import re

import pytest
from playwright.sync_api import expect

from jersa.pages.product_page import ProductPage
from jersa.pages.search_page import SearchPage
from jersa.seed import SEED_NAME, SEED_QUERY, SEED_SLUG


@pytest.mark.regression
def test_search_leads_to_product(page):
    """E-03: wyszukanie produktu i przejście na jego stronę."""
    search = SearchPage(page)
    search.open(SEED_QUERY)
    search.result(SEED_SLUG, SEED_NAME).click()

    expect(page).to_have_url(re.compile(rf"/produkt/{re.escape(SEED_SLUG)}$"))
    expect(ProductPage(page).heading).to_have_text(SEED_NAME)
