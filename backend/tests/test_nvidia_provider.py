import json

import pytest

from app.services import llm_provider_service as nvidia


class FakeResponse:
    def __init__(self, status=200, body=b"{}"):
        self.status = status
        self._body = body
        self.read_limit = None

    def read(self, limit):
        self.read_limit = limit
        return self._body[:limit]


class FakeConnection:
    def __init__(self, response):
        self.response = response
        self.request_args = None
        self.closed = False

    def request(self, *args, **kwargs):
        self.request_args = (args, kwargs)

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def install_fake_connection(monkeypatch, response):
    connection = FakeConnection(response)
    monkeypatch.setattr(nvidia.http.client, "HTTPSConnection", lambda *args, **kwargs: connection)
    return connection


def test_nvidia_connection_success_uses_fixed_https_endpoint_and_closes(monkeypatch):
    body = json.dumps({
        "choices": [{"message": {"content": "InsightFlow connection successful"}}]
    }).encode()
    connection = install_fake_connection(monkeypatch, FakeResponse(200, body))

    result = nvidia.test_nvidia_connection("test-secret", "test-model")

    assert result["connected"] is True
    assert result["provider"] == "NVIDIA"
    args, kwargs = connection.request_args
    assert args[0:2] == ("POST", "/v1/chat/completions")
    assert kwargs["headers"]["Authorization"] == "Bearer test-secret"
    assert connection.closed is True


def test_nvidia_connection_does_not_follow_redirects(monkeypatch):
    connection = install_fake_connection(monkeypatch, FakeResponse(302, b'{"location":"https://attacker.invalid"}'))

    with pytest.raises(ValueError, match="status 302"):
        nvidia.test_nvidia_connection("test-secret")

    assert connection.closed is True
    assert connection.request_args[0][0:2] == ("POST", "/v1/chat/completions")


def test_nvidia_connection_rejects_oversized_response(monkeypatch):
    connection = install_fake_connection(
        monkeypatch,
        FakeResponse(200, b"x" * (nvidia.MAX_RESPONSE_BYTES + 1)),
    )

    with pytest.raises(ValueError, match="exceeded the allowed size"):
        nvidia.test_nvidia_connection("test-secret")

    assert connection.closed is True


def test_nvidia_connection_does_not_expose_provider_error_body(monkeypatch):
    secret = "test-secret"
    body = json.dumps({"detail": f"invalid token {secret}"}).encode()
    connection = install_fake_connection(monkeypatch, FakeResponse(500, body))

    with pytest.raises(ValueError) as error:
        nvidia.test_nvidia_connection(secret)

    assert "test-secret" not in str(error.value)
    assert "invalid token" not in str(error.value)
    assert "status 500" in str(error.value)
    assert connection.closed is True
