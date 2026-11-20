from uuid import uuid4

import pytest

pytestmark = pytest.mark.regression

SEED_PRODUCT = "zakiet-castello"


def test_new_customer_has_empty_wishlist(shop):
    """A-WISH-01: nowy klient ma pustą przechowalnię i dostaje jej ciasteczko."""
    response = shop.wishlist()
    assert response.status_code == 200
    assert response.json() == {"slugs": [], "products": []}
    assert "jersa_wish" in shop.client.cookies


def test_add_to_wishlist(shop):
    """A-WISH-02: dodanie produktu do przechowalni."""
    response = shop.add_wish(SEED_PRODUCT)
    assert response.status_code == 200
    body = response.json()
    assert body["slugs"] == [SEED_PRODUCT]
    assert [product["slug"] for product in body["products"]] == [SEED_PRODUCT]


def test_add_same_product_twice_keeps_one_entry(shop):
    """A-WISH-03: ten sam produkt dodany dwa razy daje jeden wpis."""
    shop.add_wish(SEED_PRODUCT)
    response = shop.add_wish(SEED_PRODUCT)
    assert response.status_code == 200
    assert response.json()["slugs"] == [SEED_PRODUCT]


def test_remove_from_wishlist(shop):
    """A-WISH-04: usunięcie produktu z przechowalni."""
    shop.add_wish(SEED_PRODUCT)
    response = shop.remove_wish(SEED_PRODUCT)
    assert response.status_code == 200
    assert response.json() == {"slugs": [], "products": []}
    assert shop.wishlist().json() == {"slugs": [], "products": []}


def test_wishlist_without_product_is_rejected(shop):
    """A-WISH-05: żądanie do przechowalni bez produktu jest odrzucane."""
    response = shop.client.post("/api/commerce/wishlist", json={})
    assert response.status_code == 400
    assert response.json() == {"error": "Brak produktu"}


@pytest.mark.parametrize("kind", ["nieistniejacy", "ukryty"])
def test_wish_for_unknown_or_hidden_product_is_rejected(shop, make_product, kind):
    """A-WISH-06: dodanie do przechowalni produktu, którego nie ma albo który jest ukryty,
    jest odrzucane."""
    if kind == "ukryty":
        slug = make_product(hidden=True).slug
    else:
        slug = "test-nie-ma-" + uuid4().hex[:8]
    response = shop.add_wish(slug)
    assert response.status_code == 400
    assert response.json() == {"error": "Nie znaleziono produktu"}
    assert shop.wishlist().json()["slugs"] == []
