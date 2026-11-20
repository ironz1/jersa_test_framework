import json

import pytest

from jersa.db.products import OwnProduct, delete_product, new_slug, product_row, set_hidden


def test_new_slug_is_unique_and_prefixed():
    a, b = new_slug(), new_slug()
    assert a != b
    assert a.startswith("test-")
    assert len(a) == 17


def test_product_row_defaults():
    row = product_row("test-abc")
    assert row["id"] == row["slug"] == "test-abc"
    assert row["name"] == "Produkt testowy abc"
    assert row["amount"] == 200
    assert json.loads(row["stockBySize"]) == {"36": 5, "38": 5}
    assert json.loads(row["sizeCodes"]) == ["36", "38"]
    assert json.loads(row["unavailable"]) == []
    assert row["isPromo"] is False
    assert row["promoPercent"] == 0


def test_product_row_promo_and_empty_size():
    row = product_row("test-abc", stock={"36": 0, "38": 2}, promo_percent=20)
    assert row["isPromo"] is True
    assert row["promoPercent"] == 20
    assert json.loads(row["unavailable"]) == ["36"]


def test_own_product_price_applies_promo():
    assert OwnProduct("test-a", "n", 200, 20, {}).price == 160
    assert OwnProduct("test-a", "n", 200, 0, {}).price == 200


def test_own_product_price_rounds_half_up():
    # 25 zł z rabatem 10% to 22,50 zł; sklep zaokrągla połówki w górę (round() dałoby 22).
    assert OwnProduct("test-a", "n", 25, 10, {}).price == 23


class NoSql:
    def execute(self, *args, **kwargs):
        raise AssertionError("SQL nie może się wykonać")


def test_delete_refuses_slug_without_test_prefix():
    with pytest.raises(ValueError, match="zakiet-castello"):
        delete_product(NoSql(), "zakiet-castello")


def test_set_hidden_refuses_slug_without_test_prefix():
    with pytest.raises(ValueError, match="zakiet-castello"):
        set_hidden(NoSql(), "zakiet-castello", True)
