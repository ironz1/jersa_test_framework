import pytest

from jersa.db.discount_codes import new_code

pytestmark = [pytest.mark.regression, pytest.mark.contract]


def test_created_code_matches_contract(admin, assert_matches_schema):
    """K-11: utworzony w panelu kod zgodny ze schematem."""
    response = admin.create_code(new_code(), "amount", 20, ends_on="2030-12-31")
    assert response.status_code == 200, response.text
    assert_matches_schema(response.json(), "admin-discount-code")


def test_code_list_matches_contract(admin, assert_matches_schema):
    """K-11: lista kodów panelu zgodna ze schematem."""
    assert admin.create_code(new_code(), "percent", 10).status_code == 200
    response = admin.codes()
    assert response.status_code == 200
    assert_matches_schema(response.json(), "admin-discount-codes")
