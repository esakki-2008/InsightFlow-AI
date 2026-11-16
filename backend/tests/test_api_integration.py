def test_health_endpoint_returns_healthy_status_and_security_headers(api_client):
    response = api_client("GET", "/api/v1/health")

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


def test_root_endpoint_returns_running_status(api_client):
    response = api_client("GET", "/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["message"] == "Welcome to InsightFlow AI"


def test_upload_endpoint_rejects_unsupported_file_type(auth_api_client):
    response = auth_api_client(
        "POST",
        "/api/v1/datasets/upload",
        files={"file": ("notes.txt", b"name\\nAda\\n", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Unsupported file format. Upload CSV, XLSX, or XLS."
    )


def test_valid_upload_registers_metadata_in_isolated_database(auth_api_client):
    response = auth_api_client(
        "POST",
        "/api/v1/datasets/upload",
        files={
            "file": (
                "test_students.csv",
                b"name,score" + bytes([10]) + b"Ada,91" + bytes([10]) + b"Linus,88" + bytes([10]),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()["dataset"]
    assert payload["total_rows"] == 2
    assert payload["total_columns"] == 2
    assert payload["filename"] == "test_students.csv"
    assert payload["registry_id"]

def test_history_create_list_detail_and_delete(auth_api_client):
    payload = {
        "filename": "students.csv",
        "analysis_type": "Data Quality",
        "row_count": 2,
        "column_count": 2,
        "summary": {"quality_score": 100},
        "notes": "Integration test",
    }

    created = auth_api_client("POST", "/api/v1/history", json=payload)
    assert created.status_code == 201
    item = created.json()["item"]
    history_id = item["id"]
    assert item["summary"] == {"quality_score": 100}

    listed = auth_api_client("GET", "/api/v1/history")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == history_id

    detail = auth_api_client("GET", f"/api/v1/history/{history_id}")
    assert detail.status_code == 200
    assert detail.json()["item"]["filename"] == "students.csv"

    deleted = auth_api_client("DELETE", f"/api/v1/history/{history_id}")
    assert deleted.status_code == 200
    missing = auth_api_client("GET", f"/api/v1/history/{history_id}")
    assert missing.status_code == 404


def test_history_rejects_negative_row_count(auth_api_client):
    response = auth_api_client(
        "POST",
        "/api/v1/history",
        json={
            "filename": "students.csv",
            "analysis_type": "EDA",
            "row_count": -1,
        },
    )

    assert response.status_code == 422


def test_dataset_registry_detail_and_delete(auth_api_client):
    uploaded = auth_api_client(
        "POST",
        "/api/v1/datasets/upload",
        files={
            "file": (
                "registry_test.csv",
                b"name,score" + bytes([10]) + b"Ada,91" + bytes([10]),
                "text/csv",
            )
        },
    )
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["dataset"]["registry_id"]

    listed = auth_api_client("GET", "/api/v1/datasets/registry")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = auth_api_client("GET", f"/api/v1/datasets/registry/{dataset_id}")
    assert detail.status_code == 200
    assert detail.json()["item"]["filename"] == "registry_test.csv"
    assert detail.json()["item"]["row_count"] == 1

    deleted = auth_api_client("DELETE", f"/api/v1/datasets/registry/{dataset_id}")
    assert deleted.status_code == 200
    missing = auth_api_client("GET", f"/api/v1/datasets/registry/{dataset_id}")
    assert missing.status_code == 404


def test_explore_endpoint_returns_dataset_overview(auth_api_client):
    response = auth_api_client(
        "POST",
        "/api/v1/datasets/explore",
        files={
            "file": (
                "explore_test.csv",
                b"category,amount" + bytes([10]) + b"A,10" + bytes([10]) + b"B,20" + bytes([10]),
                "text/csv",
            )
        },
        data={"page": "1", "page_size": "10", "search": ""},
    )

    assert response.status_code == 200
    payload = response.json()["exploration"]
    assert payload["overview"]["total_rows"] == 2
    assert payload["overview"]["total_columns"] == 2



def test_private_endpoints_require_authentication(api_client):
    upload = api_client(
        "POST", "/api/v1/datasets/upload",
        files={"file": ("private.csv", b"name\nAda\n", "text/csv")},
    )
    history = api_client("GET", "/api/v1/history")
    assert upload.status_code == 401
    assert history.status_code == 401


def test_history_and_dataset_registry_are_isolated_between_users(api_client, monkeypatch):
    monkeypatch.setenv("INSIGHTFLOW_JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")

    def register(email):
        response = api_client(
            "POST", "/api/v1/auth/register",
            json={"email": email, "password": "correct-horse-battery-staple"},
        )
        assert response.status_code == 201
        return response.json()["access_token"]

    token_a = register("account-a@example.com")
    token_b = register("account-b@example.com")

    def as_user(token):
        def request(method, path, **kwargs):
            headers = dict(kwargs.pop("headers", {}) or {})
            headers["Authorization"] = f"Bearer {token}"
            return api_client(method, path, headers=headers, **kwargs)
        return request

    user_a, user_b = as_user(token_a), as_user(token_b)
    created = user_a("POST", "/api/v1/history", json={
        "filename": "private-a.csv", "analysis_type": "EDA", "summary": {"secret": "A"}
    })
    assert created.status_code == 201
    history_id = created.json()["item"]["id"]

    assert user_a("GET", "/api/v1/history").json()["total"] == 1
    assert user_b("GET", "/api/v1/history").json()["total"] == 0
    assert user_b("GET", f"/api/v1/history/{history_id}").status_code == 404
    assert user_b("DELETE", f"/api/v1/history/{history_id}").status_code == 404
    assert user_a("GET", f"/api/v1/history/{history_id}").status_code == 200

    uploaded = user_a("POST", "/api/v1/datasets/upload", files={
        "file": ("private-a.csv", b"name,score\nAda,91\n", "text/csv")
    })
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["dataset"]["registry_id"]
    assert user_a("GET", "/api/v1/datasets/registry").json()["total"] == 1
    assert user_b("GET", "/api/v1/datasets/registry").json()["total"] == 0
    assert user_b("GET", f"/api/v1/datasets/registry/{dataset_id}").status_code == 404
    assert user_b("DELETE", f"/api/v1/datasets/registry/{dataset_id}").status_code == 404
    assert user_a("GET", f"/api/v1/datasets/registry/{dataset_id}").status_code == 200
