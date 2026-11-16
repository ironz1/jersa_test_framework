"""Testy mechanizmu własnego produktu na prawdziwej bazie i sklepie.

Sprawdzają narzędzie frameworka, nie regułę sklepu, więc nie mają przypadków w macierzy śledzenia.
"""

import pytest

from jersa.db.orders import get_order
from jersa.db.products import delete_product, insert_product, new_slug, product_row

pytestmark = pytest.mark.regression


def test_product_row_covers_required_columns(db):
    """Gdy sklep doda wymaganą kolumnę, ten test wskaże ją po nazwie."""
    required = {
        row["column_name"]
        for row in db.execute(
            """SELECT column_name FROM information_schema.columns
            WHERE table_name = 'ProductRow' AND is_nullable = 'NO' AND column_default IS NULL"""
        ).fetchall()
    }
    missing = sorted(required - set(product_row("test-x")))
    assert not missing, f"product_row() nie wypełnia wymaganych kolumn ProductRow: {missing}"


def test_own_product_is_visible_in_shop_and_removable(db, shop):
    slug = new_slug()
    row = product_row(slug)
    try:
        insert_product(db, row)

        found = shop.search(slug).json()["products"]
        assert [p["slug"] for p in found] == [slug]
        assert found[0]["price"]["amount"] == 200
        assert found[0]["sizes"] == [
            {"code": "36", "available": True},
            {"code": "38", "available": True},
        ]

        page = shop.client.get(f"/produkt/{slug}")
        assert page.status_code == 200
        assert row["name"] in page.text
    finally:
        delete_product(db, slug)

    count = db.execute('SELECT count(*) AS n FROM "ProductRow" WHERE slug = %s', (slug,)).fetchone()
    assert count["n"] == 0
    assert shop.search(slug).json() == {"products": []}


def test_delete_product_removes_its_orders_and_reviews(db, shop):
    slug = new_slug()
    try:
        insert_product(db, product_row(slug))
        assert shop.add_to_cart(slug).status_code == 200
        order = shop.create_order()
        assert order.status_code == 200
        order_id = order.json()["order"]["id"]
        assert shop.add_review(slug, "Anna", "Leży świetnie.").status_code == 200
        assert get_order(db, order_id) is not None
    finally:
        delete_product(db, slug)

    assert get_order(db, order_id) is None
    reviews = db.execute(
        'SELECT count(*) AS n FROM "ReviewRow" WHERE "productSlug" = %s', (slug,)
    ).fetchone()
    assert reviews["n"] == 0
    products = db.execute(
        'SELECT count(*) AS n FROM "ProductRow" WHERE slug = %s', (slug,)
    ).fetchone()
    assert products["n"] == 0
