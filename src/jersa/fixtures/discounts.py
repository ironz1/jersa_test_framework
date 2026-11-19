from collections.abc import Callable, Iterator

import psycopg
import pytest

from jersa.db.discount_codes import (
    OwnDiscountCode,
    delete_discount_code,
    discount_code_row,
    insert_discount_code,
    new_code,
)


@pytest.fixture
def make_discount_code(db: psycopg.Connection) -> Iterator[Callable[..., OwnDiscountCode]]:
    """Fabryka własnych kodów rabatowych testu.

    `make_discount_code(kind="amount", value=20, ends_on=date(...), active=False, code=...)`
    wstawia kod `test-<hex>` (albo podany, który też musi mieć prefiks `test-`). Po teście,
    także nieudanym, kody znikają po ID. Zależy od `db`, więc bez DATABASE_URL test jest
    pomijany.
    """
    created: list[str] = []

    def _make(code: str | None = None, **overrides: object) -> OwnDiscountCode:
        text = code or new_code()
        if not text.lower().startswith("test-"):
            raise ValueError(f"Kod testu musi mieć prefiks 'test-', a jest: {text!r}")
        row = discount_code_row(text, **overrides)
        insert_discount_code(db, row)
        created.append(str(row["id"]))
        return OwnDiscountCode(
            id=str(row["id"]), code=text, kind=str(row["kind"]), value=int(row["value"])
        )

    yield _make
    for code_id in created:
        delete_discount_code(db, code_id)
