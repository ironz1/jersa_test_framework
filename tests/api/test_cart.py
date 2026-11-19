import pytest

from jersa.clients.commerce import MADE_TO_MEASURE

pytestmark = pytest.mark.regression

CART = "/api/commerce/cart"


def _lines(response):
    assert response.status_code == 200, response.text
    return response.json()["lines"]


@pytest.mark.smoke
def test_add_product_creates_line(shop, product):
    """A-CART-02: dodanie produktu w rozmiarze tworzy pozycję z ilością 1."""
    lines = _lines(shop.add_to_cart(product.slug, "36"))
    assert len(lines) == 1
    line = lines[0]
    assert line["productSlug"] == product.slug
    assert line["size"] == "36"
    assert line["quantity"] == 1
    assert line["customFit"] is False
    assert line["product"]["slug"] == product.slug


def test_same_product_and_size_increases_quantity(shop, product):
    """A-CART-03: ten sam produkt i rozmiar dodany dwa razy daje jedną pozycję z ilością 2."""
    shop.add_to_cart(product.slug, "36")
    lines = _lines(shop.add_to_cart(product.slug, "36"))
    assert len(lines) == 1
    assert lines[0]["quantity"] == 2


def test_two_sizes_make_two_lines(shop, product):
    """A-CART-04: ten sam produkt w dwóch rozmiarach daje dwie pozycje."""
    shop.add_to_cart(product.slug, "36")
    lines = _lines(shop.add_to_cart(product.slug, "38"))
    assert {line["size"] for line in lines} == {"36", "38"}
    assert len(lines) == 2


def test_add_without_size_is_rejected(shop, product):
    """A-CART-05: dodanie bez rozmiaru jest odrzucane."""
    response = shop.add_to_cart(product.slug, size="")
    assert response.status_code == 400
    assert response.json() == {"error": "Wybierz rozmiar"}
    assert _lines(shop.cart()) == []


def test_add_without_product_is_rejected(shop):
    """A-CART-06: dodanie bez produktu jest odrzucane."""
    response = shop.client.post(CART, json={"size": "36"})
    assert response.status_code == 400
    assert response.json() == {"error": "Brak produktu"}


def test_made_to_measure_line(shop, product):
    """A-CART-07: pozycja na miarę ma rozmiar „made-to-measure” i nie ma dopłaty za rozmiar."""
    lines = _lines(shop.add_to_cart(product.slug, MADE_TO_MEASURE, custom_fit=True))
    assert len(lines) == 1
    assert lines[0]["size"] == "made-to-measure"
    assert lines[0]["customFit"] is True
    assert lines[0]["sizeSurcharge"] == 0


def test_change_quantity(shop, product):
    """A-CART-08: zmiana ilości pozycji na 3."""
    line_id = _lines(shop.add_to_cart(product.slug))[0]["id"]
    lines = _lines(shop.set_quantity(line_id, 3))
    assert [line["quantity"] for line in lines] == [3]


def test_quantity_zero_removes_line(shop, product):
    """A-CART-09: ilość 0 usuwa pozycję."""
    line_id = _lines(shop.add_to_cart(product.slug))[0]["id"]
    assert _lines(shop.set_quantity(line_id, 0)) == []


@pytest.mark.parametrize(
    "body", [{"quantity": 2}, {"lineId": "x"}], ids=["bez-pozycji", "bez-ilosci"]
)
def test_patch_without_required_field_is_rejected(shop, body):
    """A-CART-10: zmiana ilości bez wskazania pozycji albo ilości jest odrzucana."""
    response = shop.client.patch(CART, json=body)
    assert response.status_code == 400
    assert response.json() == {"error": "Brak linii"}


def test_remove_line_keeps_other_lines(shop, product):
    """A-CART-11: usunięcie pozycji zostawia pozostałe."""
    shop.add_to_cart(product.slug, "36")
    lines = _lines(shop.add_to_cart(product.slug, "38"))
    first, second = lines
    remaining = _lines(shop.remove_line(first["id"]))
    assert [line["id"] for line in remaining] == [second["id"]]


def test_carts_are_separate_per_customer(make_shop, product):
    """A-CART-12: dwóch klientów ma osobne koszyki."""
    first, second = make_shop(), make_shop()
    assert len(_lines(first.add_to_cart(product.slug))) == 1
    assert _lines(second.cart()) == []


def test_cart_survives_next_request(shop, product):
    """A-CART-13: koszyk zachowuje się między żądaniami tego samego klienta."""
    added = shop.add_to_cart(product.slug)
    again = shop.cart()
    assert again.status_code == 200
    assert again.json() == added.json()
    assert len(again.json()["lines"]) == 1


@pytest.mark.parametrize(
    ("stock", "error"),
    [({"36": 2}, "Dostępnych jest 2 szt."), ({"36": 0, "38": 1}, "Brak stanu")],
    ids=["ponad-stan", "zerowy-stan"],
)
def test_add_above_stock_is_rejected(shop, make_product, stock, error):
    """A-CART-14: dodanie więcej sztuk, niż jest na stanie rozmiaru, jest odrzucane."""
    scarce = make_product(stock=stock)
    response = shop.add_to_cart(scarce.slug, "36", quantity=3)
    assert response.status_code == 400
    assert response.json() == {"error": error}
    assert _lines(shop.cart()) == []


def test_growing_quantity_above_stock_is_rejected(shop, make_product):
    """A-CART-14: kolejne dodanie albo zmiana ilości ponad stan rozmiaru jest odrzucana."""
    scarce = make_product(stock={"36": 2})
    line_id = _lines(shop.add_to_cart(scarce.slug, "36", quantity=2))[0]["id"]
    rejected = {"error": "Dostępnych jest 2 szt."}

    added = shop.add_to_cart(scarce.slug, "36", quantity=1)
    assert added.status_code == 400
    assert added.json() == rejected

    changed = shop.set_quantity(line_id, 3)
    assert changed.status_code == 400
    assert changed.json() == rejected
    assert [line["quantity"] for line in _lines(shop.cart())] == [2]


def test_made_to_measure_has_no_stock_limit(shop, make_product):
    """A-CART-14: szycie na miarę nie ma limitu stanu."""
    tailored = make_product(stock={"36": 0}, made_to_measure=True)
    lines = _lines(shop.add_to_cart(tailored.slug, MADE_TO_MEASURE, quantity=3, custom_fit=True))
    assert [line["quantity"] for line in lines] == [3]
