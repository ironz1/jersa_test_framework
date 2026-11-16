import pytest

pytestmark = pytest.mark.regression


def test_review_is_stored_trimmed(db, shop, product):
    """D-REV-01: opinia zapisuje się bez spacji wokół imienia i treści."""
    response = shop.add_review(product.slug, "  Anna  ", "  Leży świetnie.  ")
    assert response.status_code == 200, response.text

    rows = db.execute(
        'SELECT author, body FROM "ReviewRow" WHERE "productSlug" = %s', (product.slug,)
    ).fetchall()
    assert rows == [{"author": "Anna", "body": "Leży świetnie."}]
