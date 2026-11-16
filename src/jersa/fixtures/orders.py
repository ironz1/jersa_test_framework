from dataclasses import dataclass

import pytest

from jersa.clients.commerce import CommerceApi
from jersa.db.products import OwnProduct


@dataclass(frozen=True)
class PlacedOrder:
    id: str
    public_token: str
    size: str
    quantity: int


@pytest.fixture
def placed_order(shop: CommerceApi, product: OwnProduct) -> PlacedOrder:
    """Złożone, nieopłacone zamówienie: 1 sztuka rozmiaru 36 własnego produktu.

    Zamówienie usuwa fixture produktu, bo należy do jej produktu.
    """
    size, quantity = "36", 1
    added = shop.add_to_cart(product.slug, size=size, quantity=quantity)
    assert added.status_code == 200, added.text
    created = shop.create_order()
    assert created.status_code == 200, created.text
    order = created.json()["order"]
    return PlacedOrder(
        id=order["id"], public_token=order["publicToken"], size=size, quantity=quantity
    )
