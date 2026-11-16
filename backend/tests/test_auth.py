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


def test_registration_rejects_invalid_email_and_short_password(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")

    invalid_email = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "correct-horse-battery-staple"},
    )
    assert invalid_email.status_code == 422

    short_password = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert short_password.status_code == 422


def test_auth_rejects_expired_and_tampered_tokens(api_client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    import jwt

    secret = "test-secret-that-is-at-least-32-characters-long"
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", secret)

    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "iss": "insightflow-ai",
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(minutes=1),
        },
        secret,
        algorithm="HS256",
    )
    expired = api_client(
        "GET",
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired.status_code == 401

    created = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "token@example.com", "password": "correct-horse-battery-staple"},
    )
    assert created.status_code == 201
    token = created.json()["access_token"]
    tampered = api_client(
        "GET",
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}tampered"},
    )
    assert tampered.status_code == 401


def test_auth_rejects_non_bearer_authorization_scheme(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    response = api_client(
        "GET",
        "/api/v1/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401



def test_login_rate_limit_returns_429_and_retry_after(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")

    responses = [
        api_client(
            "POST",
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "incorrect-password-value"},
        )
        for _ in range(5)
    ]
    assert all(response.status_code == 401 for response in responses)

    limited = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password-value"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_registration_rate_limit_blocks_excessive_attempts(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")

    for index in range(3):
        response = api_client(
            "POST",
            "/api/v1/auth/register",
            json={
                "email": f"rate-limit-{index}@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
        assert response.status_code == 201

    limited = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "rate-limit-extra@example.com", "password": "correct-horse-battery-staple"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_auth_rejects_placeholder_jwt_secret(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "change-me")
    response = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "placeholder@example.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 503


def test_production_auth_requires_shared_rate_limiter(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    monkeypatch.setenv("INSIGHTFLOW_ENV", "production")
    monkeypatch.delenv("REDIS_URL", raising=False)

    response = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password-value"},
    )
    assert response.status_code == 503
    assert "REDIS_URL" in response.json()["detail"]


def test_redis_rate_limiter_uses_shared_atomic_script(api_client, monkeypatch):
    import app.auth as auth_module

    class FakeRedis:
        def __init__(self):
            self.calls = []

        def eval(self, *args):
            self.calls.append(args)
            return [1, 0]

    fake_redis = FakeRedis()
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("INSIGHTFLOW_ENV", "production")
    monkeypatch.setattr(auth_module, "_redis_client", fake_redis)

    response = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password-value"},
    )
    assert response.status_code == 401
    assert len(fake_redis.calls) == 1
    assert fake_redis.calls[0][1] == 1
    assert "insightflow:auth-rate-limit:login:" in fake_redis.calls[0][2]


def test_redis_rate_limiter_returns_retry_after_when_blocked(api_client, monkeypatch):
    import app.auth as auth_module

    class BlockingRedis:
        def eval(self, *args):
            return [0, 42]

    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(auth_module, "_redis_client", BlockingRedis())

    response = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password-value"},
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"


def test_redis_rate_limiter_fails_closed_when_store_is_unavailable(api_client, monkeypatch):
    import app.auth as auth_module
    import redis

    class BrokenRedis:
        def eval(self, *args):
            raise redis.ConnectionError("unavailable")

    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(auth_module, "_redis_client", BrokenRedis())

    response = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password-value"},
    )
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_redis_rate_limiter_fails_closed_for_invalid_url(api_client, monkeypatch):
    import app.auth as auth_module

    def invalid_redis_client():
        raise ValueError("Invalid Redis URL")

    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    monkeypatch.setenv("REDIS_URL", "not-a-valid-redis-url")
    monkeypatch.setattr(auth_module, "_get_redis_client", invalid_redis_client)

    response = api_client(
        "POST",
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password-value"},
    )
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
