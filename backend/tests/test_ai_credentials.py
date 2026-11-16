"""Security and ownership tests for encrypted AI provider credentials."""
from cryptography.fernet import Fernet


def _payload(api_key="test-provider-secret-1234", **overrides):
    body = {
        "display_name": "My AI",
        "provider_name": "Custom Provider",
        "protocol": "openai_compatible",
        "base_url": "https://api.example.com/v1",
        "model_id": "example/chat-model",
        "api_key": api_key,
    }
    body.update(overrides)
    return body


def _register(api_client, email):
    response = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_credentials_are_encrypted_and_never_returned(auth_api_client, api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    saved = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    assert saved.status_code == 201
    response_body = saved.json()
    assert response_body["credential"]["key_hint"] == "••••1234"
    assert "api_key" not in response_body["credential"]
    assert "encrypted_api_key" not in response_body["credential"]

    record = api_client.session_factory()
    try:
        from app.models import AIProviderCredential
        stored = record.query(AIProviderCredential).one()
        assert "test-provider-secret-1234" not in stored.encrypted_api_key
        from app.services.credential_crypto_service import decrypt_api_key
        assert decrypt_api_key(stored.encrypted_api_key) == "test-provider-secret-1234"
    finally:
        record.close()


def test_credentials_are_isolated_between_users(auth_api_client, api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]
    other_headers = _register(api_client, "other@example.com")

    other_list = api_client("GET", "/api/v1/ai/credentials", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

    other_get = api_client("PATCH", f"/api/v1/ai/credentials/{credential_id}", headers=other_headers, json={"display_name": "Stolen"})
    assert other_get.status_code == 404
    other_delete = api_client("DELETE", f"/api/v1/ai/credentials/{credential_id}", headers=other_headers)
    assert other_delete.status_code == 404


def test_credentials_require_authentication_and_encryption_configuration(api_client, monkeypatch):
    unauthenticated = api_client("GET", "/api/v1/ai/credentials")
    assert unauthenticated.status_code == 401

    headers = _register(api_client, "secure@example.com")
    monkeypatch.delenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", raising=False)
    unavailable = api_client("POST", "/api/v1/ai/credentials", headers=headers, json=_payload())
    assert unavailable.status_code == 503


def test_credentials_reject_invalid_urls_and_protocols(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    invalid_url = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(base_url="file:///etc/passwd"))
    assert invalid_url.status_code == 422
    invalid_protocol = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(protocol="native_unknown"))
    assert invalid_protocol.status_code == 422


def test_credential_update_rotates_key_without_exposing_it(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]
    updated = auth_api_client(
        "PATCH",
        f"/api/v1/ai/credentials/{credential_id}",
        json={"api_key": "rotated-secret-5678", "model_id": "another/model"},
    )
    assert updated.status_code == 200
    assert updated.json()["credential"]["key_hint"] == "••••5678"
    assert updated.json()["credential"]["model_id"] == "another/model"



def test_credential_owner_can_delete_saved_credential(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]

    deleted = auth_api_client("DELETE", f"/api/v1/ai/credentials/{credential_id}")
    assert deleted.status_code == 200
    assert deleted.json()["id"] == credential_id
    assert auth_api_client("GET", "/api/v1/ai/credentials").json()["items"] == []
