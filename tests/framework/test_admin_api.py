from jersa.clients.admin import AdminApi

CODES = "/api/admin/discount-codes"


def test_codes_lists_codes(recording_client):
    client = recording_client
    AdminApi(client).codes()
    assert client.calls == [("GET", CODES, {})]


def test_create_code_sends_all_fields_and_remembers_code(recording_client):
    client = recording_client
    admin = AdminApi(client)
    admin.create_code("test-a", "amount", 20, ends_on="2030-12-31")
    admin.create_code("test-b", "percent", 10)
    first = {"code": "test-a", "kind": "amount", "value": 20, "endsOn": "2030-12-31"}
    second = {"code": "test-b", "kind": "percent", "value": 10, "endsOn": None}
    assert client.calls == [("POST", CODES, {"json": first}), ("POST", CODES, {"json": second})]
    assert admin.created_codes == ["test-a", "test-b"]


def test_disable_code_sends_id_and_inactive(recording_client):
    client = recording_client
    AdminApi(client).disable_code("id-1")
    assert client.calls == [("POST", CODES, {"json": {"id": "id-1", "active": False}})]
