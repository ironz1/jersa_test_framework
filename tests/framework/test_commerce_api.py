from jersa.clients.commerce import EMAIL, SHIPPING, CommerceApi


class RecordingClient:
    """Atrapa `ApiClient`: zapisuje wywołania zamiast wysyłać żądania."""

    def __init__(self):
        self.calls = []

    def _record(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return "response"

    def get(self, path, **kwargs):
        return self._record("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self._record("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self._record("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self._record("DELETE", path, **kwargs)


def test_add_to_cart_sends_all_fields():
    client = RecordingClient()
    assert (
        CommerceApi(client).add_to_cart("p", size="38", quantity=2, custom_fit=True) == "response"
    )
    assert client.calls == [
        (
            "POST",
            "/api/commerce/cart",
            {"json": {"productSlug": "p", "size": "38", "quantity": 2, "customFit": True}},
        )
    ]


def test_add_to_cart_defaults():
    client = RecordingClient()
    CommerceApi(client).add_to_cart("p")
    assert client.calls[0][2] == {
        "json": {"productSlug": "p", "size": "36", "quantity": 1, "customFit": False}
    }


def test_create_order_defaults_to_standard_customer():
    client = RecordingClient()
    CommerceApi(client).create_order()
    method, path, kwargs = client.calls[0]
    assert (method, path) == ("POST", "/api/commerce/orders")
    assert kwargs == {"json": {"email": EMAIL, "shipping": SHIPPING}}
    assert kwargs["json"]["shipping"] is not SHIPPING


def test_notify_sends_order_id_twice():
    client = RecordingClient()
    CommerceApi(client).notify("o-1", "COMPLETED")
    assert client.calls == [
        (
            "POST",
            "/api/commerce/payu/notify",
            {"json": {"orderId": "o-1", "extOrderId": "o-1", "status": "COMPLETED"}},
        )
    ]


def test_search_uses_query_param():
    client = RecordingClient()
    CommerceApi(client).search("x")
    assert client.calls == [("GET", "/api/commerce/search", {"params": {"q": "x"}})]


def test_remove_wish_uses_delete():
    client = RecordingClient()
    CommerceApi(client).remove_wish("p")
    assert client.calls == [("DELETE", "/api/commerce/wishlist", {"json": {"productSlug": "p"}})]
