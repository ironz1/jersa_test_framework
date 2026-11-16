"""Koszyk i przechowalnia klienta zapisują się w bazie pod identyfikatorem z ciasteczka."""

import pytest

from jersa.db.sessions import delete_session_rows

pytestmark = pytest.mark.regression


def _count(db, table, row_id):
    return db.execute(f'SELECT count(*) AS n FROM "{table}" WHERE id = %s', (row_id,)).fetchone()[
        "n"
    ]


def test_session_rows_are_found_by_cookie_and_deleted(db, shop, product):
    assert shop.add_to_cart(product.slug).status_code == 200
    assert shop.add_wish("zakiet-castello").status_code == 200
    cart_id = shop.client.cookies.get("jersa_cart")
    wish_id = shop.client.cookies.get("jersa_wish")
    assert cart_id
    assert wish_id
    assert _count(db, "CartRow", cart_id) == 1
    assert _count(db, "WishlistRow", wish_id) == 1

    delete_session_rows(db, cart_id=cart_id, wish_id=wish_id)

    assert _count(db, "CartRow", cart_id) == 0
    assert _count(db, "WishlistRow", wish_id) == 0
