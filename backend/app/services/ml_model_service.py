from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pandas as pd


ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "ml_models"


def save_model_bundle(
    estimators: dict,
    target_column: str,
    feature_columns: list[str],
    imputation_medians: dict,
    class_labels: list[str],
    random_state: int,
) -> str:
    """Persist fitted estimators and the metadata required for later prediction."""
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib is required to save trained models.") from exc

    model_id = str(uuid4())
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_id": model_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_column": target_column,
        "feature_columns": [str(column) for column in feature_columns],
        "imputation_medians": {
            str(key): float(value) for key, value in imputation_medians.items()
        },
        "class_labels": [str(label) for label in class_labels],
        "random_state": int(random_state),
        "estimators": estimators,
    }
    destination = ARTIFACT_DIR / f"{model_id}.joblib"
    temporary = ARTIFACT_DIR / f".{model_id}.tmp"
    try:
        joblib.dump(bundle, temporary)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return model_id


def load_model_bundle(model_id: str) -> dict:
    """Load a previously saved bundle using a strictly validated UUID."""
    try:
        safe_id = str(UUID(model_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid model_id. Use the model ID returned by training.") from exc

    path = ARTIFACT_DIR / f"{safe_id}.joblib"
    if not path.is_file():
        raise ValueError("Saved model not found. Train a model before requesting predictions.")

    try:
        import joblib
        bundle = joblib.load(path)
    except Exception as exc:
        raise RuntimeError("The saved model could not be loaded.") from exc

    if bundle.get("model_id") != safe_id:
        raise RuntimeError("Saved model metadata does not match its file.")
    return bundle


def predict_with_saved_model(
    dataframe: pd.DataFrame,
    model_id: str,
    model_name: str,
) -> dict:
    """Run predictions with a saved estimator and its original feature preparation."""
    if dataframe.empty:
        raise ValueError("The prediction dataset is empty.")

    bundle = load_model_bundle(model_id)
    estimators = bundle["estimators"]
    if model_name not in estimators:
        available = ", ".join(sorted(estimators))
        raise ValueError(f"Unknown model_name. Choose one of: {available}")

    feature_columns = bundle["feature_columns"]
    missing_columns = [name for name in feature_columns if name not in dataframe.columns]
    if missing_columns:
        preview = ", ".join(missing_columns[:10])
        raise ValueError(
            f"Prediction dataset is missing {len(missing_columns)} required feature "
            f"column(s): {preview}"
        )

    features = dataframe.loc[:, feature_columns].copy()
    for column in feature_columns:
        features[column] = pd.to_numeric(features[column], errors="coerce")
    features = features.replace([np.inf, -np.inf], np.nan)
    medians = pd.Series(bundle["imputation_medians"])
    features = features.fillna(medians.reindex(feature_columns).fillna(0))

    estimator = estimators[model_name]
    encoded_predictions = estimator.predict(features)
    class_labels = bundle["class_labels"]

    probability_rows = None
    if hasattr(estimator, "predict_proba"):
        probability_rows = estimator.predict_proba(features)

    predictions = []
    for index, encoded_value in enumerate(encoded_predictions):
        class_index = int(encoded_value)
        label = class_labels[class_index]
        item = {
            "row": index + 1,
            "predicted_label": label,
            "confidence": None,
            "class_probabilities": None,
        }
        if probability_rows is not None:
            probabilities = probability_rows[index]
            item["confidence"] = round(float(np.max(probabilities)), 6)
            item["class_probabilities"] = {
                class_labels[int(class_idx)]: round(float(probability), 6)
                for class_idx, probability in enumerate(probabilities)
            }
        predictions.append(item)

    counts = pd.Series([item["predicted_label"] for item in predictions]).value_counts()
    return {
        "model_id": bundle["model_id"],
        "model_name": model_name,
        "target_column": bundle["target_column"],
        "rows_predicted": len(predictions),
        "feature_count": len(feature_columns),
        "missing_feature_values_filled": int(
            dataframe.loc[:, feature_columns].apply(
                lambda column: pd.to_numeric(column, errors="coerce")
            ).replace([np.inf, -np.inf], np.nan).isna().sum().sum()
        ),
        "prediction_distribution": {
            str(label): int(count) for label, count in counts.items()
        },
        "predictions": predictions,
    }



def list_saved_models() -> dict:
    """List metadata for model bundles persisted in the local artifact directory."""
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib is required to list saved models.") from exc

    models = []
    if ARTIFACT_DIR.is_dir():
        for path in ARTIFACT_DIR.glob("*.joblib"):
            try:
                bundle = joblib.load(path)
                model_id = str(UUID(str(bundle.get("model_id", ""))))
                if path.stem != model_id:
                    continue
                estimators = bundle.get("estimators", {})
                models.append({
                    "model_id": model_id,
                    "created_at": bundle.get("created_at"),
                    "target_column": bundle.get("target_column"),
                    "feature_count": len(bundle.get("feature_columns", [])),
                    "class_labels": bundle.get("class_labels", []),
                    "model_names": sorted(estimators.keys()),
                })
            except Exception:
                continue

    models.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {"total_models": len(models), "models": models}
