from __future__ import annotations

import numpy as np
import pandas as pd


def prepare_classification_dataset(
    dataframe: pd.DataFrame,
    target_column: str = "Label",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Validate a binary classification dataset and create a leakage-safe split.

    Only numeric predictors are used in this first baseline workflow. Median
    imputation values are learned from the training partition only.
    """
    # Keep the API server importable even before optional ML dependencies are
    # installed. The ML endpoint will provide an actionable error if absent.
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import LabelEncoder
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is not installed in the backend environment. "
            "Run: python -m pip install -r backend/requirements.txt"
        ) from exc

    if dataframe.empty:
        raise ValueError("Cannot prepare an empty dataset.")
    if not 0.1 <= test_size <= 0.4:
        raise ValueError("test_size must be between 0.1 and 0.4.")

    frame = dataframe.copy(deep=True)
    frame.columns = [str(column).strip() for column in frame.columns]

    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Column names are duplicated after whitespace normalization.")
    if target_column not in frame.columns:
        raise ValueError(
            f"Target column '{target_column}' was not found. "
            f"Available columns: {', '.join(frame.columns[:20])}"
        )

    original_rows = len(frame)
    frame = frame.dropna(subset=[target_column]).copy()
    dropped_target_rows = original_rows - len(frame)
    if frame.empty:
        raise ValueError("Every row has a missing target value.")

    labels = frame[target_column].astype("string").str.strip()
    valid_labels = labels.notna() & labels.ne("")
    dropped_blank_labels = int((~valid_labels).sum())
    frame = frame.loc[valid_labels].copy()
    labels = labels.loc[valid_labels]

    classes = sorted(labels.unique().tolist())
    if len(classes) != 2:
        raise ValueError(
            "This first ML workflow supports binary classification only. "
            f"Found {len(classes)} target classes: {classes}"
        )

    class_counts = labels.value_counts()
    if int(class_counts.min()) < 2:
        raise ValueError(
            "Each target class needs at least 2 records for a stratified split."
        )

    candidate_columns = [
        column for column in frame.select_dtypes(include="number").columns
        if column != target_column
    ]
    if not candidate_columns:
        raise ValueError("No numeric predictor columns were found.")

    features = frame[candidate_columns].apply(pd.to_numeric, errors="coerce")
    features = features.replace([np.inf, -np.inf], np.nan)

    all_missing = features.columns[features.isna().all()].tolist()
    features = features.drop(columns=all_missing)
    constant_columns = [
        column for column in features.columns
        if features[column].nunique(dropna=True) <= 1
    ]
    features = features.drop(columns=constant_columns)

    if features.shape[1] == 0:
        raise ValueError("No usable numeric features remain after validation.")

    encoder = LabelEncoder()
    encoded_labels = encoder.fit_transform(labels.astype(str))

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            features,
            encoded_labels,
            test_size=test_size,
            random_state=random_state,
            stratify=encoded_labels,
        )
    except ValueError as exc:
        raise ValueError(f"Unable to create the train/test split: {exc}") from exc

    medians = X_train.median().fillna(0)
    train_missing_before = int(X_train.isna().sum().sum())
    test_missing_before = int(X_test.isna().sum().sum())
    X_train = X_train.fillna(medians)
    X_test = X_test.fillna(medians)

    def distribution(values: np.ndarray) -> dict:
        counts = pd.Series(values).value_counts().sort_index()
        return {
            str(encoder.classes_[int(encoded)]): int(count)
            for encoded, count in counts.items()
        }

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "summary": {
            "task": "binary_classification",
            "target_column": target_column,
            "original_rows": int(original_rows),
            "usable_rows": int(len(features)),
            "rows_dropped_missing_target": int(dropped_target_rows + dropped_blank_labels),
            "feature_count": int(features.shape[1]),
            "features": [str(column) for column in features.columns],
            "dropped_all_missing_features": [str(column) for column in all_missing],
            "dropped_constant_features": [str(column) for column in constant_columns],
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "test_size": float(test_size),
            "random_state": int(random_state),
            "target_classes": [str(value) for value in encoder.classes_],
            "target_encoding": {
                str(value): int(index)
                for index, value in enumerate(encoder.classes_)
            },
            "class_distribution": distribution(encoded_labels),
            "train_class_distribution": distribution(y_train),
            "test_class_distribution": distribution(y_test),
            "missing_feature_values_imputed_train": train_missing_before,
            "missing_feature_values_imputed_test": test_missing_before,
            "imputation_strategy": "training-set median",
        },
    }
