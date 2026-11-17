from __future__ import annotations

from time import perf_counter

import numpy as np
import pandas as pd

from app.services.ml_model_service import save_model_bundle


def train_classification_models(
    prepared: dict,
    user_id: str,
    random_state: int = 42,
) -> dict:
    """Train baseline classifiers and evaluate them on the held-out test set."""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
        )
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.tree import DecisionTreeClassifier
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is not installed. Run: "
            "python -m pip install -r backend/requirements.txt"
        ) from exc

    X_train = prepared["X_train"]
    X_test = prepared["X_test"]
    y_train = prepared["y_train"]
    y_test = prepared["y_test"]
    classes = [str(value) for value in prepared["summary"]["target_classes"]]

    estimators = {
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            random_state=random_state,
            n_jobs=-1,
            class_weight="balanced",
        ),
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=random_state,
            )),
        ]),
        "Decision Tree": DecisionTreeClassifier(
            random_state=random_state,
            class_weight="balanced",
            max_depth=12,
        ),
    }

    results = []
    for name, estimator in estimators.items():
        started = perf_counter()
        estimator.fit(X_train, y_train)
        training_seconds = perf_counter() - started

        prediction_started = perf_counter()
        predictions = estimator.predict(X_test)
        prediction_seconds = perf_counter() - prediction_started

        results.append({
            "model": name,
            "accuracy": round(float(accuracy_score(y_test, predictions)), 6),
            "precision_macro": round(float(precision_score(
                y_test, predictions, average="macro", zero_division=0
            )), 6),
            "recall_macro": round(float(recall_score(
                y_test, predictions, average="macro", zero_division=0
            )), 6),
            "f1_macro": round(float(f1_score(
                y_test, predictions, average="macro", zero_division=0
            )), 6),
            "confusion_matrix": confusion_matrix(
                y_test, predictions, labels=np.arange(len(classes))
            ).tolist(),
            "class_labels": classes,
            "training_time_seconds": round(training_seconds, 4),
            "prediction_time_seconds": round(prediction_seconds, 4),
        })

        if name == "Random Forest":
            importances = estimator.feature_importances_
            ranked = sorted(
                zip(X_train.columns.astype(str), importances),
                key=lambda item: item[1],
                reverse=True,
            )[:15]
            feature_importance = [
                {"feature": feature, "importance": round(float(score), 6)}
                for feature, score in ranked
            ]

    model_id = save_model_bundle(
        user_id=user_id,
        estimators=estimators,
        target_column=prepared["summary"]["target_column"],
        feature_columns=list(X_train.columns.astype(str)),
        imputation_medians=prepared["imputation_medians"],
        class_labels=classes,
        random_state=random_state,
    )

    results.sort(key=lambda item: item["f1_macro"], reverse=True)
    return {
        "task": "binary_classification",
        "model_id": model_id,
        "saved_models": list(estimators.keys()),
        "models_trained": len(results),
        "test_rows": int(len(X_test)),
        "feature_count": int(X_train.shape[1]),
        "class_labels": classes,
        "evaluation_metric": "macro averages give both classes equal weight",
        "results": results,
        "random_forest_feature_importance": feature_importance,
    }
