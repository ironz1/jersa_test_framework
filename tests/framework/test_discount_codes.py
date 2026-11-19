from datetime import UTC, date, datetime

from jersa.db.discount_codes import discount_code_row, new_code


def test_new_code_has_test_prefix():
    code = new_code()
    assert code.startswith("test-")
    assert code != new_code()


def test_discount_code_row_stores_end_date_as_utc_midnight():
    row = discount_code_row("test-x", kind="amount", value=20, ends_on=date(2026, 11, 19))
    assert row["endsOn"] == datetime(2026, 11, 19, tzinfo=UTC)
    assert row["kind"] == "amount"
    assert row["value"] == 20
    assert row["active"] is True
    assert row["id"]


def test_discount_code_row_without_end_date():
    assert discount_code_row("test-x")["endsOn"] is None
