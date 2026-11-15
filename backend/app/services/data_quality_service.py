import math
import re

import numpy as np
import pandas as pd


def generate_data_quality_report(dataframe: pd.DataFrame) -> dict:
    """Create a transparent, descriptive data-quality profile without mutating input."""
    if dataframe is None or dataframe.empty:
        raise ValueError("Cannot generate a data quality report for an empty dataset.")

    frame = dataframe.copy(deep=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Column names are duplicated after whitespace normalization.")

    rows, columns = frame.shape
    total_cells = rows * columns
    missing_by_column = frame.isna().sum()
    missing_cells = int(missing_by_column.sum())
    duplicate_rows = int(frame.duplicated().sum())

    column_profiles = []
    constant_columns = []
    high_missing_columns = []
    high_cardinality_columns = []
    findings = []

    for name in frame.columns:
        series = frame[name]
        missing = int(series.isna().sum())
        missing_pct = (missing / rows * 100) if rows else 0.0
        unique_count = int(series.nunique(dropna=True))
        unique_pct = (unique_count / max(rows, 1)) * 100
        is_constant = unique_count <= 1
        is_identifier = bool(re.search(
            r"(^id$|(^|[_ -])id($|[_ -])|uuid|guid|identifier|serial|roll[_ -]?no|student[_ -]?no|customer[_ -]?no|account[_ -]?no)",
            str(name), re.IGNORECASE
        ))
        if is_constant:
            constant_columns.append(str(name))
        if missing_pct >= 30:
            high_missing_columns.append(str(name))
        if unique_pct >= 95 and rows >= 20 and not is_identifier:
            high_cardinality_columns.append(str(name))

        column_profiles.append({
            "name": str(name),
            "data_type": str(series.dtype),
            "total_values": int(rows),
            "missing_values": missing,
            "missing_percentage": round(missing_pct, 2),
            "unique_values": unique_count,
            "unique_percentage": round(unique_pct, 2),
            "is_constant": bool(is_constant),
            "is_identifier_like": is_identifier,
        })

    completeness = max(0.0, 100.0 * (1 - missing_cells / max(total_cells, 1)))
    duplicate_rate = duplicate_rows / max(rows, 1) * 100
    constant_rate = len(constant_columns) / max(columns, 1) * 100
    high_missing_rate = len(high_missing_columns) / max(columns, 1) * 100

    # Weighted deductions make the score reproducible and interpretable.
    score = round(max(0.0, min(100.0,
        100 - (40 * (100 - completeness) / 100)
            - (25 * duplicate_rate / 100)
            - (15 * constant_rate / 100)
            - (20 * high_missing_rate / 100)
    )), 1)

    if missing_cells:
        findings.append({
            "severity": "warning",
            "title": "Missing values detected",
            "detail": f"{missing_cells:,} cells ({100 - completeness:.2f}% of all cells) are missing.",
            "recommendation": "Review missingness by column and choose an appropriate fill or removal strategy before modeling."
        })
    if duplicate_rows:
        findings.append({
            "severity": "warning",
            "title": "Duplicate rows detected",
            "detail": f"{duplicate_rows:,} exact duplicate rows ({duplicate_rate:.2f}% of records).",
            "recommendation": "Confirm whether repeated records are valid; remove only when duplicates are unintended."
        })
    if constant_columns:
        findings.append({
            "severity": "info",
            "title": "Constant columns found",
            "detail": f"{len(constant_columns)} column(s) contain one or fewer distinct non-missing values.",
            "recommendation": "Consider excluding constant columns from modeling because they provide no variation."
        })
    if high_missing_columns:
        findings.append({
            "severity": "critical",
            "title": "Columns with high missingness",
            "detail": "At least 30% of values are missing in: " + ", ".join(high_missing_columns[:10]),
            "recommendation": "Investigate collection issues and decide whether to impute or exclude these columns."
        })
    if high_cardinality_columns:
        findings.append({
            "severity": "info",
            "title": "High-cardinality columns",
            "detail": "Potentially high-cardinality fields: " + ", ".join(high_cardinality_columns[:10]),
            "recommendation": "Check whether these are identifiers or free-text fields before encoding or charting."
        })
    if not findings:
        findings.append({
            "severity": "success",
            "title": "No major quality issues detected",
            "detail": "No missing cells, duplicate rows, constant columns, or high-missingness columns were found.",
            "recommendation": "Continue with exploratory analysis and validate domain-specific rules."
        })

    if score >= 90:
        grade = "Excellent"
    elif score >= 75:
        grade = "Good"
    elif score >= 60:
        grade = "Fair"
    else:
        grade = "Needs attention"

    return {
        "summary": {
            "quality_score": score,
            "quality_grade": grade,
            "total_rows": int(rows),
            "total_columns": int(columns),
            "total_cells": int(total_cells),
            "missing_cells": missing_cells,
            "completeness_percentage": round(completeness, 2),
            "duplicate_rows": duplicate_rows,
            "duplicate_percentage": round(duplicate_rate, 2),
            "constant_columns": len(constant_columns),
            "high_missing_columns": len(high_missing_columns),
            "high_cardinality_columns": len(high_cardinality_columns),
        },
        "scoring_method": {
            "description": "Heuristic score: starts at 100 and deducts for missing cells (40% weight), duplicate rows (25%), constant columns (15%), and columns with at least 30% missing values (20%).",
            "note": "This is a screening metric, not a universal data-quality standard. Review findings in context."
        },
        "columns": column_profiles,
        "findings": findings,
    }
