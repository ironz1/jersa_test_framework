import pytest

from jersa.seed import SEED_SLUG


@pytest.mark.smoke
@pytest.mark.regression
def test_seed_contains_proof_product(db):
    """D-01: seed wstawia produkt dowodowy."""
    rows = db.execute('SELECT slug FROM "ProductRow" WHERE slug = %s', (SEED_SLUG,)).fetchall()
    assert rows == [{"slug": SEED_SLUG}]
