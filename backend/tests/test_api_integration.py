from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_healthy_status_and_security_headers():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "InsightFlow AI",
        "version": "0.1.0",
    }
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )


def test_root_endpoint_returns_running_status():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["message"] == "Welcome to InsightFlow AI"


def test_upload_endpoint_rejects_unsupported_file_type():
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("notes.txt", b"name\nAda\n", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Unsupported file format. Upload CSV, XLSX, or XLS."
    )
