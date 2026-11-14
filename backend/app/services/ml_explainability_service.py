from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.ml_model_service import load_model_bundle


def explain_prediction(
    dataframe: pd.DataFrame,
    model_id: str,
    model_name: str,
    row_index: int = 0,
    top_n: int = 10,
) -> dict:
    """Explain one row with median-replacement probability sensitivity.

    This is a model-sensitivity aid, not a causal explanation.
    """
    if dataframe.empty:
        raise ValueError("The explanation dataset is empty.")
    if row_index < 0 or row_index >= len(dataframe):
        raise ValueError(
            f"row_index must be between 0 and {len(dataframe) - 1}."
        )

    bundle = load_model_bundle(model_id)
    estimators = bundle["estimators"]
    if model_name not in estimators:
        available = ", ".join(sorted(estimators))
        raise ValueError(f"Unknown model_name. Choose one of: {available}")

    feature_columns = bundle["feature_columns"]
    missing_columns = [
        name for name in feature_columns if name not in dataframe.columns
    ]
    if missing_columns:
        preview = ", ".join(missing_columns[:10])
        raise ValueError(
            f"Prediction dataset is missing {len(missing_columns)} required "
            f"feature column(s): {preview}"
        )

    features = dataframe.loc[:, feature_columns].iloc[[row_index]].copy()
    for column in feature_columns:
        features[column] = pd.to_numeric(features[column], errors="coerce")
    features = features.replace([np.inf, -np.inf], np.nan)

    medians = pd.Series(bundle["imputation_medians"]).reindex(feature_columns)
    features = features.fillna(medians.fillna(0))

    estimator = estimators[model_name]
    if not hasattr(estimator, "predict_proba"):
        raise ValueError(
            "This model does not provide class probabilities for explanations."
        )

    baseline_probabilities = estimator.predict_proba(features)[0]
    predicted_encoded = int(estimator.predict(features)[0])
    class_labels = bundle["class_labels"]
    predicted_label = class_labels[predicted_encoded]
    predicted_probability = float(baseline_probabilities[predicted_encoded])

    impacts = []
    for column in feature_columns:
        perturbed = features.copy()
        original_value = float(features.iloc[0][column])
        replacement_value = float(medians.get(column, 0))
        perturbed.loc[perturbed.index[0], column] = replacement_value
        changed_probabilities = estimator.predict_proba(perturbed)[0]
        changed_probability = float(changed_probabilities[predicted_encoded])
        impact = (predicted_probability - changed_probability) * 100.0

        impacts.append({
            "feature": column,
            "feature_value": original_value,
            "reference_value": replacement_value,
            "probability_impact_percentage_points": round(impact, 4),
            "direction": (
                "supports_prediction" if impact > 0.0001
                else "opposes_prediction" if impact < -0.0001
                else "no_material_change"
            ),
        })

    impacts.sort(
        key=lambda item: abs(item["probability_impact_percentage_points"]),
        reverse=True,
    )
    selected_impacts = impacts[:max(1, min(top_n, len(impacts)))]

    probabilities = {
        class_labels[index]: round(float(value), 6)
        for index, value in enumerate(baseline_probabilities)
    }
    return {
        "model_id": bundle["model_id"],
        "model_name": model_name,
        "row": row_index + 1,
        "predicted_label": predicted_label,
        "confidence": round(predicted_probability, 6),
        "class_probabilities": probabilities,
        "explanation_method": "single-feature median-replacement sensitivity",
        "top_feature_sensitivities": selected_impacts,
        "interpretation_note": (
            "A positive impact means replacing this feature with its training "
            "median lowered the predicted-class probability. This indicates "
            "model sensitivity, not causation. Feature effects can interact."
        ),
    }
