def test_email_registration_login_and_account_profile(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    credentials = {"email": "  Test.User@Example.com ", "password": "correct-horse-battery-staple"}

    registered = api_client("POST", "/api/v1/auth/register", json=credentials)
    assert registered.status_code == 201
    body = registered.json()
    assert body["user"]["email"] == "test.user@example.com"
    assert body["token_type"] == "bearer"
    assert "password_hash" not in body["user"]

    duplicate = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "TEST.USER@example.com", "password": credentials["password"]},
    )
    assert duplicate.status_code == 409

    logged_in = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "test.user@example.com", "password": credentials["password"]},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]

    profile = api_client("GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "test.user@example.com"


def test_auth_rejects_invalid_password_and_missing_token(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    created = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert created.status_code == 201

    wrong_password = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "incorrect-password-value"},
    )
    assert wrong_password.status_code == 401

    no_token = api_client("GET", "/api/v1/auth/me")
    assert no_token.status_code == 401


def test_auth_requires_strong_jwt_secret(api_client, monkeypatch):
    monkeypatch.delenv("INSIGHTFLOW_JWT_SECRET", raising=False)
    response = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "nobody@example.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 503
