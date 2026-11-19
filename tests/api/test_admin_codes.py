"""Panel kodów rabatowych: `/api/admin/discount-codes` (tylko po zalogowaniu)."""

import pytest

from jersa.db.discount_codes import new_code

pytestmark = pytest.mark.regression


def _listed(admin, code_id):
    """Kod z listy panelu po ID. Lista ma też kody operatora i innych testów."""
    response = admin.codes()
    assert response.status_code == 200, response.text
    return next(code for code in response.json()["codes"] if code["id"] == code_id)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_admin_api_requires_login(anonymous_admin, method):
    """A-ADM-01: panel kodów bez logowania odpowiada 401."""
    if method == "GET":
        response = anonymous_admin.codes()
    else:
        response = anonymous_admin.create_code(new_code(), "percent", 10)
    assert response.status_code == 401
    assert response.json() == {"error": "Brak dostępu"}


@pytest.mark.parametrize(
    ("kind", "value", "ends_on"),
    [("percent", 10, None), ("amount", 20, "2030-12-31")],
    ids=["procent-bez-daty", "kwota-z-data"],
)
def test_create_code(admin, kind, value, ends_on):
    """A-ADM-02: operator tworzy kod procentowy albo kwotowy, z datą końca albo bez;
    kod jest aktywny i widać go na liście."""
    text = new_code()
    response = admin.create_code(text, kind, value, ends_on=ends_on)
    assert response.status_code == 200, response.text
    created = response.json()["code"]
    expected = {"code": text, "kind": kind, "value": value, "endsOn": ends_on, "active": True}
    assert {key: created[key] for key in expected} == expected
    assert _listed(admin, created["id"]) == created


def test_disabled_code_stops_working(admin, shop, product):
    """A-ADM-03: wyłączony w panelu kod jest nieaktywny i nie działa w koszyku."""
    text = new_code()
    code_id = admin.create_code(text, "percent", 10).json()["code"]["id"]
    disabled = admin.disable_code(code_id)
    assert disabled.status_code == 200, disabled.text
    assert disabled.json() == {"ok": True}
    assert _listed(admin, code_id)["active"] is False

    assert shop.add_to_cart(product.slug).status_code == 200
    response = shop.apply_discount(text)
    assert response.status_code == 400
    assert response.json() == {"error": "Kod jest nieprawidłowy"}


@pytest.mark.parametrize(
    ("code", "kind", "value", "ends_on", "error"),
    [
        ("", "percent", 10, None, "Podaj kod"),
        (None, "free", 10, None, "Wybierz procent albo kwotę"),
        (None, "amount", 0, None, "Podaj wartość"),
        (None, "percent", 101, None, "Procent musi być od 1 do 100"),
        (None, "percent", 10, "2030-02-30", "Nieprawidłowa data"),
    ],
    ids=["pusty-kod", "zly-rodzaj", "wartosc-zero", "procent-ponad-100", "zla-data"],
)
def test_invalid_code_is_rejected_by_panel(admin, code, kind, value, ends_on, error):
    """A-ADM-04: panel odrzuca kod z pustą treścią, złym rodzajem, wartością lub datą."""
    text = new_code() if code is None else code
    response = admin.create_code(text, kind, value, ends_on=ends_on)
    assert response.status_code == 400
    assert response.json() == {"error": error}


def test_duplicate_code_is_rejected(admin):
    """A-ADM-05: kod, który już istnieje (bez względu na wielkość liter), jest odrzucany."""
    text = new_code()
    assert admin.create_code(text, "percent", 10).status_code == 200
    response = admin.create_code(text.upper(), "amount", 5)
    assert response.status_code == 400
    assert response.json() == {"error": "Taki kod już istnieje"}
