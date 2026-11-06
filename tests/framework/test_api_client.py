import pytest

from jersa.clients.api_client import ApiClient


def test_url_joins_without_double_slash():
    assert ApiClient("http://h:1").url("/api/x") == "http://h:1/api/x"


def test_path_must_start_with_slash():
    with pytest.raises(ValueError, match="api/x"):
        ApiClient("http://h:1").url("api/x")


def test_requests_use_default_timeout(monkeypatch):
    client = ApiClient("http://h:1")
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return "response"

    monkeypatch.setattr(client._session, "request", fake_request)
    assert client.get("/x") == "response"
    assert seen["method"] == "GET"
    assert seen["url"] == "http://h:1/x"
    assert seen["timeout"] == 10.0
