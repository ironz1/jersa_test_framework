from uuid import uuid4

import pytest

from jersa.seed import SEED_QUERY, SEED_SLUG, SEED_SLUG_FRAGMENT

pytestmark = pytest.mark.regression


def _slugs(response):
    assert response.status_code == 200, response.text
    return [product["slug"] for product in response.json()["products"]]


def test_search_by_name_fragment(shop):
    """A-SRCH-01: wyszukiwanie po fragmencie nazwy."""
    assert SEED_SLUG in _slugs(shop.search(SEED_QUERY))


def test_search_ignores_case(shop):
    """A-SRCH-02: wyszukiwanie nie rozróżnia wielkości liter."""
    lower = _slugs(shop.search(SEED_QUERY.lower()))
    assert lower
    assert _slugs(shop.search(SEED_QUERY.upper())) == lower


def test_search_by_slug_fragment(shop):
    """A-SRCH-03: wyszukiwanie po fragmencie sluga."""
    assert SEED_SLUG in _slugs(shop.search(SEED_SLUG_FRAGMENT))


def test_empty_query_returns_nothing(shop):
    """A-SRCH-04: puste zapytanie daje pustą listę."""
    response = shop.search("")
    assert response.status_code == 200
    assert response.json() == {"products": []}


def test_query_without_matches_returns_nothing(shop):
    """A-SRCH-05: zapytanie bez trafień daje pustą listę."""
    response = shop.search(uuid4().hex)
    assert response.status_code == 200
    assert response.json() == {"products": []}
