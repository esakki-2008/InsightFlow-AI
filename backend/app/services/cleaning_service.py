
import pandas as pd


def generate_cleaning_preview(dataframe: pd.DataFrame) -> dict:
    """
    Generate a cleaning preview without modifying the original dataframe.

    Proposed operations:
    1. Trim whitespace from column names.
    2. Identify duplicate rows.
    3. Fill numeric missing values with the median.
    4. Fill categorical missing values with the mode.
    5. Report columns that cannot be safely filled automatically.
    """

    if dataframe.empty:
        raise ValueError("Cannot clean an empty dataset.")

    original = dataframe.copy(deep=True)
    cleaned = dataframe.copy(deep=True)

    original_columns = [str(column) for column in original.columns]
    cleaned_names = [column.strip() for column in original_columns]

    # Avoid silently creating duplicate column names.
    if len(cleaned_names) != len(set(cleaned_names)):
        raise ValueError(
            "Column names become duplicated after removing whitespace. "
            "Please resolve these column names manually."
        )

    # 1. Clean column names.
    cleaned.columns = cleaned_names

    renamed_columns = [
        {
            "old_name": old,
            "new_name": new,
        }
        for old, new in zip(original_columns, cleaned_names)
        if old != new
    ]

    # 2. Detect and remove duplicate rows in the preview copy.
    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates().copy()

    # 3. Handle missing values.
    missing_before = int(cleaned.isna().sum().sum())
    filled_columns = []
    unresolved_columns = []

    for column in cleaned.columns:
        missing_count = int(cleaned[column].isna().sum())

        if missing_count == 0:
            continue

        if pd.api.types.is_numeric_dtype(cleaned[column]):
            fill_value = cleaned[column].median()

            if pd.isna(fill_value):
                unresolved_columns.append({
                    "column": str(column),
                    "missing_values": missing_count,
                    "reason": "Column contains no usable numeric values.",
                })
                continue

            cleaned[column] = cleaned[column].fillna(fill_value)
            method = "median"

        else:
            modes = cleaned[column].mode(dropna=True)

            if modes.empty:
                unresolved_columns.append({
                    "column": str(column),
                    "missing_values": missing_count,
                    "reason": "Column contains no available value for mode filling.",
                })
                continue

            fill_value = modes.iloc[0]
            cleaned[column] = cleaned[column].fillna(fill_value)
            method = "mode"

        filled_columns.append({
            "column": str(column),
            "missing_values_filled": missing_count,
            "method": method,
        })

    missing_after = int(cleaned.isna().sum().sum())

    # 4. Identify numeric and categorical columns.
    numeric_columns = [
        str(column)
        for column in cleaned.select_dtypes(include="number").columns
    ]

    categorical_columns = [
        str(column)
        for column in cleaned.select_dtypes(
            include=["object", "category", "bool"]
        ).columns
    ]

    # 5. Return preview and report.
    preview = cleaned.head(10).copy()

    preview = preview.astype(object).where(
        pd.notna(preview),
        None,
    )

    return {
        "summary": {
            "original_rows": int(len(original)),
            "preview_rows": int(len(cleaned)),
            "original_columns": int(len(original.columns)),
            "cleaned_columns": int(len(cleaned.columns)),
            "duplicate_rows_detected": duplicate_count,
            "missing_values_before": missing_before,
            "missing_values_after": missing_after,
        },
        "operations": {
            "renamed_columns": renamed_columns,
            "duplicates_to_remove": duplicate_count,
            "filled_columns": filled_columns,
            "unresolved_columns": unresolved_columns,
        },
        "column_types": {
            "numeric": numeric_columns,
            "categorical": categorical_columns,
        },
        "preview": {
            "columns": [str(column) for column in preview.columns],
            "rows": preview.to_dict(orient="records"),
        },
    }


def apply_cleaning(dataframe: pd.DataFrame):
    """
    Apply the same cleaning operations to a copy of the dataset.
    The original dataframe is never modified.
    """

    if dataframe.empty:
        raise ValueError("Cannot clean an empty dataset.")

    cleaned = dataframe.copy(deep=True)

    # 1. Trim whitespace from column names.
    original_columns = [str(column) for column in cleaned.columns]
    cleaned_names = [column.strip() for column in original_columns]

    if len(cleaned_names) != len(set(cleaned_names)):
        raise ValueError(
            "Column names become duplicated after trimming whitespace. "
            "Please resolve them manually."
        )

    cleaned.columns = cleaned_names

    renamed_columns = [
        {"old_name": old, "new_name": new}
        for old, new in zip(original_columns, cleaned_names)
        if old != new
    ]

    # 2. Remove duplicate rows.
    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates().copy()

    # 3. Fill missing values.
    filled_columns = []
    unresolved_columns = []

    for column in cleaned.columns:
        missing_count = int(cleaned[column].isna().sum())

        if missing_count == 0:
            continue

        if pd.api.types.is_numeric_dtype(cleaned[column]):
            fill_value = cleaned[column].median()
            method = "median"
        else:
            modes = cleaned[column].mode(dropna=True)
            fill_value = modes.iloc[0] if not modes.empty else None
            method = "mode"

        if fill_value is None or pd.isna(fill_value):
            unresolved_columns.append({
                "column": str(column),
                "missing_values": missing_count,
                "reason": "No usable value available for filling.",
            })
            continue

        cleaned[column] = cleaned[column].fillna(fill_value)

        filled_columns.append({
            "column": str(column),
            "missing_values_filled": missing_count,
            "method": method,
        })

    report = {
        "original_rows": int(len(dataframe)),
        "cleaned_rows": int(len(cleaned)),
        "columns": int(len(cleaned.columns)),
        "duplicate_rows_removed": duplicate_count,
        "missing_values_remaining": int(cleaned.isna().sum().sum()),
        "renamed_columns": renamed_columns,
        "filled_columns": filled_columns,
        "unresolved_columns": unresolved_columns,
    }

    return cleaned, report
