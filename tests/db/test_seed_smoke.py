import pytest


@pytest.mark.smoke
def test_seed_contains_castello(db):
    rows = db.execute(
        'SELECT slug FROM "ProductRow" WHERE slug = %s', ("zakiet-castello",)
    ).fetchall()
    assert rows == [{"slug": "zakiet-castello"}]
