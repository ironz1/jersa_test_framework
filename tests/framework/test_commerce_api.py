from jersa.clients.commerce import (
    BUYER,
    EMAIL,
    SHIPPING,
    SHIPPING_METHODS,
    CommerceApi,
    checkout_body,
)


def test_add_to_cart_sends_all_fields(recording_client):
    client = recording_client
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


def test_add_to_cart_defaults(recording_client):
    client = recording_client
    CommerceApi(client).add_to_cart("p")
    assert client.calls[0][2] == {
        "json": {"productSlug": "p", "size": "36", "quantity": 1, "customFit": False}
    }


def test_create_order_defaults_to_standard_customer(recording_client):
    client = recording_client
    CommerceApi(client).create_order()
    method, path, kwargs = client.calls[0]
    assert (method, path) == ("POST", "/api/commerce/orders")
    assert kwargs == {"json": {"email": EMAIL, "shipping": SHIPPING}}
    assert kwargs["json"]["shipping"] is not SHIPPING


def test_notify_sends_order_id_twice(recording_client):
    client = recording_client
    CommerceApi(client).notify("o-1", "COMPLETED")
    assert client.calls == [
        (
            "POST",
            "/api/commerce/payu/notify",
            {"json": {"orderId": "o-1", "extOrderId": "o-1", "status": "COMPLETED"}},
        )
    ]


def test_search_uses_query_param(recording_client):
    client = recording_client
    CommerceApi(client).search("x")
    assert client.calls == [("GET", "/api/commerce/search", {"params": {"q": "x"}})]


def test_remove_wish_uses_delete(recording_client):
    client = recording_client
    CommerceApi(client).remove_wish("p")
    assert client.calls == [("DELETE", "/api/commerce/wishlist", {"json": {"productSlug": "p"}})]


def test_apply_discount_sends_code(recording_client):
    client = recording_client
    CommerceApi(client).apply_discount("LATO10")
    assert client.calls == [("POST", "/api/commerce/discount", {"json": {"code": "LATO10"}})]


def test_checkout_order_wraps_body_in_checkout(recording_client):
    client = recording_client
    CommerceApi(client).checkout_order({"email": "a@b.pl"})
    assert client.calls == [
        ("POST", "/api/commerce/orders", {"json": {"checkout": {"email": "a@b.pl"}}})
    ]


def test_notify_sends_total_amount_only_when_given(recording_client):
    client = recording_client
    api = CommerceApi(client)
    api.notify("o1", "COMPLETED")
    api.notify("o1", "COMPLETED", total_amount="19500")
    plain, with_amount = (call[2]["json"] for call in client.calls)
    assert "totalAmount" not in plain
    assert with_amount == {
        "orderId": "o1",
        "extOrderId": "o1",
        "status": "COMPLETED",
        "totalAmount": "19500",
    }


# Pola `CheckoutDraft` sklepu (src/lib/checkout.ts): pełne poprawne pole `checkout`.
CHECKOUT_KEYS = {
    "buyerKind", "firstName", "lastName", "email", "phone", "companyName", "nip", "street",
    "postalCode", "city", "country", "shipToDifferentAddress", "shipStreet", "shipPostalCode",
    "shipCity", "shipCountry", "notes", "termsAccepted", "shippingMethodId",
}  # fmt: skip


def test_checkout_body_is_complete_and_overridable():
    body = checkout_body()
    assert set(body) == CHECKOUT_KEYS
    assert body["email"] == EMAIL
    assert body["termsAccepted"] is True
    assert body["shippingMethodId"] in SHIPPING_METHODS
    assert checkout_body(nip="1")["nip"] == "1"
    body["firstName"] = "zmienione"
    assert checkout_body()["firstName"] == BUYER["firstName"]
