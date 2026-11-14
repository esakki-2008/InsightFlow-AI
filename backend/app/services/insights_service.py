import math

import numpy as np
import pandas as pd


def _safe_number(value):
    number = float(value)
    return number if math.isfinite(number) else None


def generate_dataset_insights(dataframe: pd.DataFrame) -> dict:
    """Generate evidence-backed, plain-English observations from dataset statistics.

    This is deterministic analysis, not an external LLM response. Every insight
    is calculated from the uploaded data and includes supporting evidence.
    """
    if dataframe.empty:
        raise ValueError("Cannot generate insights for an empty dataset.")

    frame = dataframe.copy(deep=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError(
            "Column names are duplicated after whitespace normalization. "
            "Clean the column names before generating insights."
        )

    row_count, column_count = frame.shape
    missing_total = int(frame.isna().sum().sum())
    duplicate_total = int(frame.duplicated().sum())
    numeric_columns = frame.select_dtypes(include="number").columns.tolist()
    categorical_columns = frame.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    insights = []

    if missing_total:
        missing_by_column = frame.isna().sum().sort_values(ascending=False)
        affected = [
            {"column": str(column), "missing": int(count),
             "percentage": round(float(count) / row_count * 100, 2)}
            for column, count in missing_by_column.items() if count > 0
        ][:5]
        top = affected[0]
        insights.append({
            "category": "data_quality",
            "severity": "warning",
            "title": "Missing values need attention",
            "description": (
                f"{missing_total:,} missing values were found across "
                f"{len(affected)} or more columns. "
                f"{top['column']} has the largest count ({top['missing']:,}, "
                f"{top['percentage']:.2f}% of rows). Review how these values "
                "should be handled before analysis or model training."
            ),
            "evidence": affected,
        })
    else:
        insights.append({
            "category": "data_quality",
            "severity": "positive",
            "title": "No missing values detected",
            "description": (
                f"All {row_count:,} rows have populated values across "
                f"{column_count:,} columns."
            ),
            "evidence": [{"missing_values": 0}],
        })

    if duplicate_total:
        insights.append({
            "category": "data_quality",
            "severity": "warning",
            "title": "Duplicate records detected",
            "description": (
                f"{duplicate_total:,} rows are exact duplicates "
                f"({duplicate_total / row_count * 100:.2f}% of the dataset). "
                "Check whether they represent repeated events or accidental duplicates."
            ),
            "evidence": [{"duplicate_rows": duplicate_total}],
        })
    else:
        insights.append({
            "category": "data_quality",
            "severity": "positive",
            "title": "No exact duplicate rows",
            "description": "Every row is unique when all columns are considered together.",
            "evidence": [{"duplicate_rows": 0}],
        })

    numeric_frame = frame[numeric_columns].replace([np.inf, -np.inf], np.nan)
    outlier_candidates = []
    skew_candidates = []
    for column in numeric_columns:
        values = pd.to_numeric(numeric_frame[column], errors="coerce").dropna()
        if values.empty:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr > 0:
            count = int(((values < q1 - 1.5 * iqr) |
                         (values > q3 + 1.5 * iqr)).sum())
            if count:
                outlier_candidates.append({
                    "column": str(column),
                    "count": count,
                    "percentage": round(count / len(values) * 100, 2),
                })
        if len(values) >= 3:
            skewness = _safe_number(values.skew())
            if skewness is not None and abs(skewness) >= 1:
                skew_candidates.append({
                    "column": str(column),
                    "skewness": round(skewness, 3),
                    "direction": "right" if skewness > 0 else "left",
                })

    outlier_candidates.sort(key=lambda item: item["count"], reverse=True)
    if outlier_candidates:
        top_outliers = outlier_candidates[:5]
        top = top_outliers[0]
        insights.append({
            "category": "anomaly",
            "severity": "warning",
            "title": "Potential outliers found",
            "description": (
                f"The IQR rule flags {top['count']:,} potential outliers in "
                f"{top['column']} ({top['percentage']:.2f}% of its valid values). "
                "These may be unusual observations; inspect them before removing anything."
            ),
            "evidence": top_outliers,
        })

    if skew_candidates:
        skew_candidates.sort(key=lambda item: abs(item["skewness"]), reverse=True)
        top_skew = skew_candidates[:5]
        top = top_skew[0]
        insights.append({
            "category": "distribution",
            "severity": "info",
            "title": "Some numeric distributions are skewed",
            "description": (
                f"{top['column']} has {top['direction']}-skewed values "
                f"(skewness {top['skewness']:.3f}). Consider robust summaries "
                "or transformations if your analysis assumes symmetric data."
            ),
            "evidence": top_skew,
        })

    if len(numeric_columns) >= 2:
        correlation = numeric_frame.corr(numeric_only=True)
        pairs = []
        for left_index, left in enumerate(correlation.columns):
            for right in correlation.columns[left_index + 1:]:
                value = correlation.loc[left, right]
                if pd.notna(value) and abs(float(value)) >= 0.7:
                    pairs.append({
                        "column_a": str(left),
                        "column_b": str(right),
                        "correlation": round(float(value), 3),
                        "strength": "strong",
                        "direction": "positive" if value > 0 else "negative",
                    })
        pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        if pairs:
            top_pairs = pairs[:5]
            top = top_pairs[0]
            relationship = "positive" if top["correlation"] > 0 else "negative"
            insights.append({
                "category": "relationship",
                "severity": "info",
                "title": "Strong numeric relationships detected",
                "description": (
                    f"{top['column_a']} and {top['column_b']} have a strong "
                    f"{relationship} correlation (r = {top['correlation']:.3f}). "
                    "Correlation describes association and does not establish causation."
                ),
                "evidence": top_pairs,
            })

    category_summaries = []
    for column in categorical_columns[:30]:
        counts = frame[column].astype("string").fillna("(Missing)").value_counts()
        if counts.empty:
            continue
        top_value = str(counts.index[0])
        share = float(counts.iloc[0]) / row_count * 100
        category_summaries.append({
            "column": str(column),
            "top_value": top_value,
            "count": int(counts.iloc[0]),
            "percentage": round(share, 2),
            "unique_values": int(frame[column].nunique(dropna=False)),
        })
    dominant = [item for item in category_summaries if item["percentage"] >= 80]
    if dominant:
        top = sorted(dominant, key=lambda item: item["percentage"], reverse=True)[0]
        insights.append({
            "category": "distribution",
            "severity": "info",
            "title": "A categorical value dominates its column",
            "description": (
                f"{top['top_value']} accounts for {top['percentage']:.2f}% "
                f"of {top['column']} values. This imbalance may affect comparisons "
                "or downstream classification."
            ),
            "evidence": dominant[:5],
        })

    if not outlier_candidates and not skew_candidates and not missing_total and not duplicate_total:
        insights.append({
            "category": "overview",
            "severity": "positive",
            "title": "No major quality flags from these checks",
            "description": (
                "The checks found no missing values, exact duplicate rows, "
                "IQR outliers, or strongly skewed numeric columns. This does not "
                "replace domain-specific validation."
            ),
            "evidence": [],
        })

    return {
        "summary": {
            "rows": int(row_count),
            "columns": int(column_count),
            "numeric_columns": int(len(numeric_columns)),
            "categorical_columns": int(len(categorical_columns)),
            "missing_values": missing_total,
            "duplicate_rows": duplicate_total,
            "insights_generated": len(insights),
        },
        "insights": insights,
        "method": (
            "Deterministic statistical profiling (missingness, exact duplicates, "
            "IQR outliers, numeric skewness, Pearson correlations, and categorical "
            "frequency). These observations are descriptive, not causal."
        ),
    }
