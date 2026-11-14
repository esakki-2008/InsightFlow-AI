import json

import numpy as np
import pandas as pd


def generate_exploration(dataframe: pd.DataFrame, page: int = 1,
                         page_size: int = 25, search: str = "") -> dict:
    """Return paginated records and descriptive EDA without changing the data."""

    if dataframe.empty:
        raise ValueError("Cannot explore an empty dataset.")
    if page < 1:
        raise ValueError("Page must be 1 or greater.")
    if page_size not in (10, 25, 50, 100):
        raise ValueError("Page size must be 10, 25, 50, or 100.")

    frame = dataframe.copy(deep=True)
    frame.columns = [str(column).strip() for column in frame.columns]

    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError(
            "Column names are duplicated after whitespace normalization. "
            "Clean the column names before exploring this dataset."
        )

    total_rows = len(frame)
    numeric_columns = frame.select_dtypes(include="number").columns.tolist()
    categorical_columns = frame.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    numeric_stats = {}
    outlier_stats = {}
    for column in numeric_columns:
        # Infinite values occur in some real-world flow datasets (for example,
        # rate columns with a zero denominator). Exclude them from descriptive
        # statistics so the API always returns standards-compliant JSON.
        values = pd.to_numeric(frame[column], errors="coerce")
        values = values.replace([np.inf, -np.inf], np.nan).dropna()
        if values.empty:
            continue
        numeric_stats[str(column)] = {
            "count": int(values.count()),
            "mean": float(values.mean()),
            "median": float(values.median()),
            "std": float(values.std()) if values.count() > 1 else 0.0,
            "min": float(values.min()),
            "max": float(values.max()),
        }
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        outlier_count = int(((values < q1 - 1.5 * iqr) |
                             (values > q3 + 1.5 * iqr)).sum())
        outlier_stats[str(column)] = outlier_count

    categorical_stats = {}
    for column in categorical_columns[:30]:
        counts = frame[column].astype("string").fillna("(Missing)").value_counts().head(5)
        categorical_stats[str(column)] = [
            {"value": str(value), "count": int(count)}
            for value, count in counts.items()
        ]

    correlation_columns = numeric_columns[:15]
    correlation = {}
    if len(correlation_columns) >= 2:
        correlation_frame = frame[correlation_columns].replace(
            [np.inf, -np.inf], np.nan
        )
        matrix = correlation_frame.corr(numeric_only=True)
        # Pandas' JSON writer converts NaN correlation values to JSON null.
        correlation = json.loads(matrix.to_json())

    filtered = frame
    term = search.strip()
    if term:
        mask = frame.astype("string").apply(
            lambda column: column.str.contains(term, case=False, na=False, regex=False)
        ).any(axis=1)
        filtered = frame.loc[mask]

    filtered_rows = len(filtered)
    total_pages = max(1, (filtered_rows + page_size - 1) // page_size)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * page_size
    records_frame = filtered.iloc[start:start + page_size]
    records = json.loads(records_frame.to_json(
        orient="records", date_format="iso", double_precision=15
    ))

    return {
        "overview": {
            "total_rows": int(total_rows),
            "total_columns": int(len(frame.columns)),
            "numeric_columns": int(len(numeric_columns)),
            "categorical_columns": int(len(categorical_columns)),
            "missing_values": int(frame.isna().sum().sum()),
            "duplicate_rows": int(frame.duplicated().sum()),
        },
        "columns": [
            {"name": str(column), "dtype": str(frame[column].dtype),
             "missing": int(frame[column].isna().sum())}
            for column in frame.columns
        ],
        "numeric_statistics": numeric_stats,
        "categorical_statistics": categorical_stats,
        "outlier_counts_iqr": outlier_stats,
        "correlation": correlation,
        "table": {
            "rows": records,
            "page": int(safe_page),
            "page_size": int(page_size),
            "total_rows": int(filtered_rows),
            "total_pages": int(total_pages),
            "search": term,
        },
    }
