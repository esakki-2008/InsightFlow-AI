import asyncio

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models  # noqa: F401 - ensure all test tables are registered
from app.main import app


@pytest.fixture
def api_client():
    """Provide an API requester backed by a fresh in-memory database per test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    def request(method: str, path: str, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    request.session_factory = TestingSessionLocal

    try:
        yield request
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def auth_api_client(api_client, monkeypatch):
    """Provide a client authenticated as an isolated test account."""
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
    registered = api_client(
        "POST",
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]

    def request(method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {token}"
        return api_client(method, path, headers=headers, **kwargs)

    return request
