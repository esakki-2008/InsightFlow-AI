from __future__ import annotations


def _register_second_user(api_client):
    response = api_client(
        "POST",
        "/api/v1/auth/register",
        json={
            "email": "second-owner@example.com",
            "password": "another-correct-horse-battery",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    def request(method: str, path: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {token}"
        return api_client(method, path, headers=headers, **kwargs)

    return request


def test_private_dataset_and_history_routes_require_authentication(api_client):
    assert api_client("GET", "/api/v1/history").status_code == 401
    assert api_client("GET", "/api/v1/datasets/registry").status_code == 401
    assert api_client("GET", "/api/v1/ml/models").status_code == 401


def test_user_cannot_read_or_delete_another_users_history(auth_api_client, api_client):
    created = auth_api_client(
        "POST",
        "/api/v1/history",
        json={
            "filename": "owner-private.csv",
            "analysis_type": "Data Quality",
            "row_count": 2,
            "column_count": 2,
            "summary": {"private_metric": "owner-one"},
        },
    )
    assert created.status_code == 201
    history_id = created.json()["item"]["id"]
    second_user = _register_second_user(api_client)

    assert second_user("GET", f"/api/v1/history/{history_id}").status_code == 404
    assert second_user("DELETE", f"/api/v1/history/{history_id}").status_code == 404

    owner_read = auth_api_client("GET", f"/api/v1/history/{history_id}")
    assert owner_read.status_code == 200
    assert owner_read.json()["item"]["summary"]["private_metric"] == "owner-one"


def test_user_cannot_read_or_delete_another_users_dataset_registry_item(auth_api_client, api_client):
    uploaded = auth_api_client(
        "POST",
        "/api/v1/datasets/upload",
        files={"file": ("owner-private.csv", b"age,score\n20,90\n21,80\n", "text/csv")},
    )
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["dataset"]["registry_id"]
    second_user = _register_second_user(api_client)

    assert second_user("GET", f"/api/v1/datasets/registry/{dataset_id}").status_code == 404
    assert second_user("DELETE", f"/api/v1/datasets/registry/{dataset_id}").status_code == 404

    owner_read = auth_api_client("GET", f"/api/v1/datasets/registry/{dataset_id}")
    assert owner_read.status_code == 200
    assert owner_read.json()["item"]["filename"] == "owner-private.csv"
