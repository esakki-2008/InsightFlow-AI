"""Security and ownership tests for encrypted AI provider credentials."""
import json
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
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
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



def test_saved_credential_connection_uses_decrypted_key_without_returning_it(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import ai_credentials

    calls = {}

    def fake_test(**kwargs):
        calls.update(kwargs)
        return {
            "provider": kwargs["provider_name"],
            "model": kwargs["model"],
            "connected": True,
            "message": "Provider connection successful.",
        }

    monkeypatch.setattr(ai_credentials, "test_openai_compatible_connection", fake_test)
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]

    tested = auth_api_client("POST", f"/api/v1/ai/credentials/{credential_id}/test")
    assert tested.status_code == 200
    assert tested.json()["connected"] is True
    assert calls["api_key"] == "test-provider-secret-1234"
    assert "api_key" not in tested.json()
    assert "test-provider-secret-1234" not in tested.text


def test_saved_credential_connection_is_owner_scoped(auth_api_client, api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import ai_credentials

    def should_not_run(**kwargs):
        raise AssertionError("Provider call must not run for another user's credential")

    monkeypatch.setattr(ai_credentials, "test_openai_compatible_connection", should_not_run)
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]
    other_headers = _register(api_client, "different-owner@example.com")

    response = api_client(
        "POST",
        f"/api/v1/ai/credentials/{credential_id}/test",
        headers=other_headers,
    )
    assert response.status_code == 404


def test_credentials_reject_http_local_and_ip_urls(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    for url in (
        "http://api.example.com/v1",
        "https://localhost/v1",
        "https://127.0.0.1/v1",
        "https://service.internal/v1",
    ):
        response = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(base_url=url))
        assert response.status_code == 422


def test_openai_compatible_connection_builds_chat_completion_request(monkeypatch):
    from app.services import openai_compatible_service as provider

    captured = {}

    def fake_post_json(url, api_key, payload):
        captured.update({"url": url, "api_key": api_key, "payload": payload})
        return {"choices": [{"message": {"content": "OK"}}]}

    monkeypatch.setattr(provider, "_post_json", fake_post_json)
    result = provider.test_openai_compatible_connection(
        api_key="secret-test-key",
        base_url="https://api.example.com/v1",
        model="demo/chat-model",
        provider_name="Demo Provider",
    )
    assert result["connected"] is True
    assert result["provider"] == "Demo Provider"
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["api_key"] == "secret-test-key"
    assert captured["payload"]["model"] == "demo/chat-model"
    assert captured["payload"]["stream"] is False


def test_openai_compatible_connection_rejects_non_public_dns(monkeypatch):
    import socket
    from app.services import openai_compatible_service as provider

    def private_address(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 0))]

    monkeypatch.setattr(provider.socket, "getaddrinfo", private_address)
    try:
        provider._resolve_public_address("provider.example")
    except ValueError as exc:
        assert "public IP" in str(exc)
    else:
        raise AssertionError("Private provider address should be rejected")


def test_advanced_dataset_qa_uses_only_the_authenticated_users_saved_provider(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import main

    calls = {}

    def fake_answer(**kwargs):
        calls.update(kwargs)
        return {
            "question": kwargs["question"],
            "answer": "There are two rows.",
            "query_type": "row_count",
            "result": {"rows": 2},
            "rows_analyzed": 2,
            "provider": kwargs["provider_name"],
            "model": kwargs["model"],
        }

    monkeypatch.setattr(main, "answer_advanced_dataset_question", fake_answer)
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]

    response = auth_api_client(
        "POST",
        "/api/v1/datasets/ask/advanced",
        data={"question": "How many rows?", "credential_id": credential_id},
        files={"file": ("sample.csv", b"value\n1\n2\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["qa"]["provider"] == "Custom Provider"
    assert calls["api_key"] == "test-provider-secret-1234"
    assert calls["base_url"] == "https://api.example.com/v1"
    assert calls["model"] == "example/chat-model"
    assert calls["provider_name"] == "Custom Provider"
    assert "test-provider-secret-1234" not in response.text


def test_advanced_dataset_qa_cannot_use_another_users_saved_provider(auth_api_client, api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import main

    def should_not_run(**kwargs):
        raise AssertionError("Provider call must not run for another user's credential")

    monkeypatch.setattr(main, "answer_advanced_dataset_question", should_not_run)
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload())
    credential_id = created.json()["credential"]["id"]
    other_headers = _register(api_client, "dataset-qa-other@example.com")

    response = api_client(
        "POST",
        "/api/v1/datasets/ask/advanced",
        headers=other_headers,
        data={"question": "How many rows?", "credential_id": credential_id},
        files={"file": ("sample.csv", b"value\n1\n2\n", "text/csv")},
    )

    assert response.status_code == 404


def test_native_gemini_adapter_uses_native_endpoint_and_api_key_header(monkeypatch):
    from app.services import native_provider_service as native

    captured = {}

    def fake_post(url, payload, headers):
        captured.update({"url": url, "payload": payload, "headers": headers})
        return {"steps": [{"type": "model_output", "content": [{"type": "text", "text": "Gemini response"}]}]}

    monkeypatch.setattr(native, "_post_json_with_headers", fake_post)
    answer = native.native_provider_chat(
        protocol="native_gemini",
        api_key="gemini-test-secret",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com",
        messages=[
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Count rows."},
        ],
    )

    assert answer == "Gemini response"
    assert captured["url"] == "https://generativelanguage.googleapis.com/v1beta/interactions"
    assert captured["headers"] == {"x-goog-api-key": "gemini-test-secret"}
    assert captured["payload"]["system_instruction"] == "Be concise."
    assert captured["payload"]["model"] == "gemini-2.5-flash"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["input"] == "User: Count rows."


def test_native_anthropic_adapter_uses_messages_api_and_version_header(monkeypatch):
    from app.services import native_provider_service as native

    captured = {}

    def fake_post(url, payload, headers):
        captured.update({"url": url, "payload": payload, "headers": headers})
        return {"content": [{"type": "text", "text": "Claude response"}]}

    monkeypatch.setattr(native, "_post_json_with_headers", fake_post)
    answer = native.native_provider_chat(
        protocol="native_anthropic",
        api_key="anthropic-test-secret",
        model="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        messages=[
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Count rows."},
        ],
    )

    assert answer == "Claude response"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"] == {
        "x-api-key": "anthropic-test-secret",
        "anthropic-version": "2023-06-01",
    }
    assert captured["payload"]["system"] == "Be concise."
    assert captured["payload"]["messages"] == [{"role": "user", "content": "Count rows."}]


def test_native_provider_credential_connection_test_dispatches_by_protocol(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import ai_credentials

    calls = {}

    def fake_native_test(**kwargs):
        calls.update(kwargs)
        return {
            "provider": kwargs["provider_name"],
            "model": kwargs["model"],
            "connected": True,
            "message": "Native provider connection successful.",
        }

    monkeypatch.setattr(ai_credentials, "test_native_provider_connection", fake_native_test)
    created = auth_api_client(
        "POST",
        "/api/v1/ai/credentials",
        json=_payload(
            provider_name="Google Gemini",
            protocol="native_gemini",
            base_url="https://generativelanguage.googleapis.com",
            model_id="gemini-2.5-flash",
        ),
    )
    assert created.status_code == 201
    assert created.json()["credential"]["protocol"] == "native_gemini"

    tested = auth_api_client("POST", f"/api/v1/ai/credentials/{created.json()['credential']['id']}/test")
    assert tested.status_code == 200
    assert tested.json()["connected"] is True
    assert calls["protocol"] == "native_gemini"
    assert calls["api_key"] == "test-provider-secret-1234"


def test_advanced_question_service_routes_native_protocol_to_native_adapter(monkeypatch):
    from app.services import advanced_question_service as advanced

    calls = {}

    def fake_native(**kwargs):
        calls.update(kwargs)
        return "native response"

    monkeypatch.setattr(advanced, "native_provider_chat", fake_native)
    answer = advanced._provider_chat(
        api_key="native-secret",
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "hello"}],
        base_url="https://generativelanguage.googleapis.com",
        protocol="native_gemini",
    )
    assert answer == "native response"
    assert calls["protocol"] == "native_gemini"
    assert calls["api_key"] == "native-secret"


def test_advanced_dataset_qa_accepts_native_gemini_credential(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import main

    captured = {}

    def fake_answer(**kwargs):
        captured.update(kwargs)
        return {
            "question": kwargs["question"],
            "answer": "There are two rows.",
            "query_type": "row_count",
            "result": {"rows": 2},
            "rows_analyzed": 2,
            "provider": kwargs["provider_name"],
            "model": kwargs["model"],
        }

    monkeypatch.setattr(main, "answer_advanced_dataset_question", fake_answer)
    created = auth_api_client(
        "POST",
        "/api/v1/ai/credentials",
        json=_payload(
            provider_name="Google Gemini",
            protocol="native_gemini",
            base_url="https://generativelanguage.googleapis.com",
            model_id="gemini-2.5-flash",
        ),
    )
    credential_id = created.json()["credential"]["id"]

    response = auth_api_client(
        "POST",
        "/api/v1/datasets/ask/advanced",
        data={"question": "How many rows?", "credential_id": credential_id},
        files={"file": ("sample.csv", b"value\n1\n2\n", "text/csv")},
    )

    assert response.status_code == 200
    assert captured["protocol"] == "native_gemini"
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["base_url"] == "https://generativelanguage.googleapis.com"


def test_custom_headers_are_encrypted_and_never_returned(auth_api_client, api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    headers = {"X-Workspace-ID": "workspace-42", "X-Environment": "staging"}
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(custom_headers=headers))
    assert created.status_code == 201
    credential = created.json()["credential"]
    assert credential["has_custom_headers"] is True
    assert "custom_headers" not in credential
    assert "encrypted_custom_headers" not in credential
    assert "workspace-42" not in created.text

    db = api_client.session_factory()
    try:
        from app.models import AIProviderCredential
        from app.services.credential_crypto_service import decrypt_secret_text
        record = db.query(AIProviderCredential).one()
        assert record.encrypted_custom_headers
        assert "workspace-42" not in record.encrypted_custom_headers
        assert json.loads(decrypt_secret_text(record.encrypted_custom_headers)) == headers
    finally:
        db.close()


def test_custom_headers_reject_reserved_invalid_and_duplicate_names(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    invalid_sets = [
        {"Authorization": "Bearer attacker-value"},
        {"X-Api-Key": "override"},
        {"Host": "internal.example"},
        {"Bad Header": "value"},
        {"X-Test": "line1\r\nInjected: yes"},
        {"X-Test": "one", "x-test": "two"},
    ]
    for headers in invalid_sets:
        response = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(custom_headers=headers))
        assert response.status_code == 422


def test_custom_headers_are_used_by_saved_provider_connection_test(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import ai_credentials
    calls = {}

    def fake_test(**kwargs):
        calls.update(kwargs)
        return {"provider": kwargs["provider_name"], "model": kwargs["model"], "connected": True, "message": "OK"}

    monkeypatch.setattr(ai_credentials, "test_openai_compatible_connection", fake_test)
    headers = {"X-Workspace-ID": "workspace-42"}
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(custom_headers=headers))
    credential_id = created.json()["credential"]["id"]
    tested = auth_api_client("POST", f"/api/v1/ai/credentials/{credential_id}/test")
    assert tested.status_code == 200
    assert calls["custom_headers"] == headers
    assert "workspace-42" not in tested.text


def test_custom_headers_can_be_updated_and_cleared(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(custom_headers={"X-Old": "old"}))
    credential_id = created.json()["credential"]["id"]

    updated = auth_api_client(
        "PATCH", f"/api/v1/ai/credentials/{credential_id}",
        json={"custom_headers": {"X-New": "new"}},
    )
    assert updated.status_code == 200
    assert updated.json()["credential"]["has_custom_headers"] is True

    cleared = auth_api_client(
        "PATCH", f"/api/v1/ai/credentials/{credential_id}",
        json={"custom_headers": {}},
    )
    assert cleared.status_code == 200
    assert cleared.json()["credential"]["has_custom_headers"] is False


def test_advanced_dataset_qa_passes_saved_custom_headers_to_provider(auth_api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    from app import main
    calls = {}

    def fake_answer(**kwargs):
        calls.update(kwargs)
        return {
            "question": kwargs["question"], "answer": "Two rows.", "query_type": "row_count",
            "result": {"rows": 2}, "rows_analyzed": 2,
            "provider": kwargs["provider_name"], "model": kwargs["model"],
        }

    monkeypatch.setattr(main, "answer_advanced_dataset_question", fake_answer)
    headers = {"X-Workspace-ID": "workspace-42"}
    created = auth_api_client("POST", "/api/v1/ai/credentials", json=_payload(custom_headers=headers))
    credential_id = created.json()["credential"]["id"]
    response = auth_api_client(
        "POST", "/api/v1/datasets/ask/advanced",
        data={"question": "How many rows?", "credential_id": credential_id},
        files={"file": ("sample.csv", b"value\n1\n2\n", "text/csv")},
    )
    assert response.status_code == 200
    assert calls["custom_headers"] == headers
    assert "workspace-42" not in response.text


def test_provider_transport_rejects_custom_auth_header_override(monkeypatch):
    from app.services import openai_compatible_service as provider
    monkeypatch.setattr(provider, "_resolve_public_address", lambda hostname: "93.184.216.34")
    try:
        provider._post_json_with_headers(
            "https://provider.example/v1/test",
            {},
            {"Authorization": "Bearer correct-key"},
            custom_headers={"Authorization": "Bearer attacker-key"},
        )
    except ValueError as exc:
        assert "reserved header" in str(exc)
    else:
        raise AssertionError("Custom headers must not override provider authentication")


def test_native_provider_adapter_forwards_safe_custom_headers(monkeypatch):
    from app.services import native_provider_service as native
    captured = {}

    def fake_post(url, payload, headers, custom_headers=None):
        captured.update({"url": url, "headers": headers, "custom_headers": custom_headers})
        return {"content": [{"type": "text", "text": "Claude response"}]}

    monkeypatch.setattr(native, "_post_json_with_headers", fake_post)
    answer = native.native_provider_chat(
        protocol="native_anthropic",
        api_key="anthropic-test-secret",
        model="claude-sonnet-4-5",
        base_url="https://api.anthropic.com",
        messages=[{"role": "user", "content": "hello"}],
        custom_headers={"X-Workspace-ID": "workspace-42"},
    )
    assert answer == "Claude response"
    assert captured["headers"]["x-api-key"] == "anthropic-test-secret"
    assert captured["custom_headers"] == {"X-Workspace-ID": "workspace-42"}
