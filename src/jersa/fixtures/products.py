from collections.abc import Callable, Iterator

import psycopg
import pytest

from jersa.db.products import (
    DEFAULT_STOCK,
    OwnProduct,
    delete_product,
    insert_product,
    new_slug,
    product_row,
)


@pytest.fixture
def make_product(db: psycopg.Connection) -> Iterator[Callable[..., OwnProduct]]:
    """Fabryka własnych produktów testu.

    `make_product(amount=200, stock={"36": 1}, promo_percent=20, made_to_measure=True)` wstawia
    produkt `test-<hex>` do bazy. Po teście, także nieudanym, każdy utworzony produkt znika
    razem ze swoimi zamówieniami i opiniami. Zależy od `db`, więc bez DATABASE_URL test jest
    pomijany.
    """
    created: list[str] = []

    def _make(**overrides: object) -> OwnProduct:
        slug = new_slug()
        row = product_row(slug, **overrides)
        created.append(slug)
        insert_product(db, row)
        return OwnProduct(
            slug=slug,
            name=str(row["name"]),
            amount=int(row["amount"]),
            promo_percent=int(row["promoPercent"]),
            stock=dict(overrides.get("stock") or DEFAULT_STOCK),
        )

    yield _make
    for slug in created:
        delete_product(db, slug)


@pytest.fixture
def product(make_product: Callable[..., OwnProduct]) -> OwnProduct:
    """Domyślny własny produkt: 200 zł, po 5 sztuk rozmiarów 36 i 38, z opcją szycia na miarę."""
    return make_product()
