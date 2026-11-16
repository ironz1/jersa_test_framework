from uuid import uuid4

import pytest

pytestmark = pytest.mark.regression


def test_seed_reviews_are_listed(shop):
    """A-REV-01: lista opinii produktu zawiera opinie z seeda."""
    response = shop.reviews("zakiet-castello")
    assert response.status_code == 200
    authors = {review["author"] for review in response.json()["reviews"]}
    assert {"Paulina", "Malwina"} <= authors


def test_added_review_is_listed(shop, product):
    """A-REV-02: dodana opinia jest od razu na liście."""
    added = shop.add_review(product.slug, "Anna", "Leży świetnie.")
    assert added.status_code == 200, added.text
    listed = shop.reviews(product.slug)
    assert listed.status_code == 200
    for body in (added.json(), listed.json()):
        assert [(review["author"], review["body"]) for review in body["reviews"]] == [
            ("Anna", "Leży świetnie.")
        ]


def test_review_without_author_is_rejected(shop, product):
    """A-REV-03: opinia bez imienia jest odrzucana."""
    response = shop.add_review(product.slug, "", "Leży świetnie.")
    assert response.status_code == 400
    assert response.json() == {"error": "Podaj imię lub pseudonim"}


def test_review_without_body_is_rejected(shop, product):
    """A-REV-04: opinia bez treści jest odrzucana."""
    response = shop.add_review(product.slug, "Anna", "")
    assert response.status_code == 400
    assert response.json() == {"error": "Napisz opinię"}


def test_reviews_without_product_are_rejected(shop):
    """A-REV-05: lista opinii bez wskazania produktu jest odrzucana."""
    response = shop.client.get("/api/commerce/reviews")
    assert response.status_code == 400
    assert response.json() == {"error": "Brak produktu"}


def test_review_for_unknown_product_is_rejected(shop):
    """A-REV-06: opinia do nieistniejącego produktu jest odrzucana."""
    response = shop.add_review("nie-ma-" + uuid4().hex, "Anna", "Leży świetnie.")
    assert response.status_code == 400
    assert response.json() == {"error": "Nie znaleziono produktu"}
