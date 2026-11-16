from __future__ import annotations

from uuid import uuid4

from app import models


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
    assert second_user("GET", "/api/v1/history").json()["total"] == 0

    owner_read = auth_api_client("GET", f"/api/v1/history/{history_id}")
    assert owner_read.status_code == 200
    assert owner_read.json()["item"]["summary"]["private_metric"] == "owner-one"
    assert auth_api_client("GET", "/api/v1/history").json()["total"] == 1


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
    assert second_user("GET", "/api/v1/datasets/registry").json()["total"] == 0

    owner_read = auth_api_client("GET", f"/api/v1/datasets/registry/{dataset_id}")
    assert owner_read.status_code == 200
    assert owner_read.json()["item"]["filename"] == "owner-private.csv"



def _create_model_record(api_client, owner_email="owner@example.com", user_id=None):
    """Insert model metadata into this test's isolated database."""
    model_id = str(uuid4())

    with api_client.session_factory() as db:
        if user_id is None:
            owner = db.query(models.User).filter_by(email=owner_email).one()
            user_id = owner.id

        db.add(
            models.MLModelRecord(
                id=model_id,
                user_id=user_id,
                dataset_filename="private-training.csv",
                target_column="label",
                feature_count=1,
                test_rows=2,
                class_labels=["normal", "attack"],
                model_names=["Random Forest"],
                metrics=[],
            )
        )
        db.commit()

    return model_id


def test_user_cannot_see_another_users_ml_model_metadata(auth_api_client, api_client):
    model_id = _create_model_record(api_client)
    second_user = _register_second_user(api_client)

    response = second_user("GET", "/api/v1/ml/models")

    assert response.status_code == 200
    assert response.json()["registered_models"] == 0
    assert all(item["model_id"] != model_id for item in response.json()["models"])


def test_user_cannot_predict_with_another_users_model(auth_api_client, api_client):
    model_id = _create_model_record(api_client)
    second_user = _register_second_user(api_client)

    response = second_user(
        "POST",
        "/api/v1/ml/predict",
        data={"model_id": model_id},
        files={"file": ("prediction.csv", b"feature\n1\n2\n", "text/csv")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Saved model not found."


def test_user_cannot_explain_another_users_model(auth_api_client, api_client):
    model_id = _create_model_record(api_client)
    second_user = _register_second_user(api_client)

    response = second_user(
        "POST",
        "/api/v1/ml/explain",
        data={"model_id": model_id, "row_index": "0"},
        files={"file": ("prediction.csv", b"feature\n1\n2\n", "text/csv")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Saved model not found."


def test_ownerless_legacy_records_are_invisible_to_all_users(auth_api_client, api_client):
    history_id = str(uuid4())
    dataset_id = str(uuid4())
    model_id = str(uuid4())

    # Simulate records created before per-user ownership was introduced.
    with api_client.session_factory() as db:
        db.add(
            models.AnalysisHistory(
                id=history_id,
                user_id=None,
                filename="legacy.csv",
                analysis_type="Data Quality",
                row_count=2,
                column_count=1,
                summary={"legacy": True},
            )
        )
        db.add(
            models.DatasetRecord(
                id=dataset_id,
                user_id=None,
                filename="legacy.csv",
                file_type="csv",
                file_size_bytes=20,
                row_count=2,
                column_count=1,
                columns=["value"],
                data_types={"value": "int64"},
                missing_values={"value": 0},
                total_missing_values=0,
                duplicate_rows=0,
            )
        )
        db.add(
            models.MLModelRecord(
                id=model_id,
                user_id=None,
                dataset_filename="legacy.csv",
                target_column="label",
                feature_count=1,
                test_rows=2,
                class_labels=["normal"],
                model_names=["Random Forest"],
                metrics=[],
            )
        )
        db.commit()

    second_user = _register_second_user(api_client)

    for user_request in (auth_api_client, second_user):
        history = user_request("GET", "/api/v1/history")
        datasets = user_request("GET", "/api/v1/datasets/registry")
        models_response = user_request("GET", "/api/v1/ml/models")

        assert history.status_code == 200
        assert history.json()["total"] == 0
        assert datasets.status_code == 200
        assert datasets.json()["total"] == 0
        assert models_response.status_code == 200
        assert models_response.json()["registered_models"] == 0

        assert user_request("GET", f"/api/v1/history/{history_id}").status_code == 404
        assert user_request("DELETE", f"/api/v1/history/{history_id}").status_code == 404
        assert user_request("GET", f"/api/v1/datasets/registry/{dataset_id}").status_code == 404
        assert user_request("DELETE", f"/api/v1/datasets/registry/{dataset_id}").status_code == 404
