from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _clean_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _numeric_columns(frame: pd.DataFrame) -> list[str]:
    columns = []
    for column in frame.columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if int(values.notna().sum()) >= 2 and values.nunique(dropna=True) > 1:
            columns.append(str(column))
    return columns


def _categorical_columns(frame: pd.DataFrame) -> list[str]:
    result = []
    for column in frame.columns:
        series = frame[column]
        if (
            not pd.api.types.is_numeric_dtype(series)
            and series.nunique(dropna=True) >= 2
            and series.nunique(dropna=True) <= min(50, max(2, len(frame) // 2))
        ):
            result.append(str(column))
    return result



def _looks_like_date(series: pd.Series) -> bool:
    """Recognize common date strings without misclassifying numeric identifiers."""
    if pd.api.types.is_numeric_dtype(series):
        return False
    non_null = series.dropna()
    if len(non_null) < 2:
        return False
    sample = non_null.astype(str).head(min(200, len(non_null)))
    date_hint = sample.str.contains(
        r"(?:[-/]|\\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\b)",
        case=False,
        regex=True,
    ).mean()
    if date_hint < 0.7:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return float(parsed.notna().mean()) >= 0.8

def generate_question_suggestions(dataframe: pd.DataFrame) -> dict:
    """Profile a dataset locally and suggest only questions supported by Standard Q&A."""
    if dataframe.empty:
        raise ValueError("The uploaded dataset has no rows.")

    frame = dataframe.copy(deep=False)
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Column names must be unique to generate question suggestions.")

    rows, columns = frame.shape
    numeric = _numeric_columns(frame)
    categorical = _categorical_columns(frame)

    # Rank business measures by usefulness. Specific measures outrank generic
    # tokens so Total_Cost does not accidentally outrank Revenue or Profit.
    priority_weights = {
        "revenue": 120, "sales": 115, "profit": 110, "net income": 108,
        "amount": 100, "market cap": 98, "close": 95, "price": 90,
        "volume": 85, "quantity": 80, "units sold": 80, "total cost": 72,
        "cost": 65, "salary": 65, "score": 60, "duration": 55,
        "rate": 50, "count": 45, "temperature": 40, "rain": 40,
        "age": 30, "open": 25, "high": 25, "low": 25,
    }

    def score_column(name: str) -> int:
        normalized = _clean_name(name)
        matches = [
            weight for term, weight in priority_weights.items()
            if term in normalized
        ]
        return max(matches, default=0)

    numeric = sorted(numeric, key=lambda name: (-score_column(name), name.lower()))
    suggestions: list[str] = [
        "How many rows are in the dataset?",
        "How many missing values are there?",
        "How many duplicate rows are there?",
        "What columns are available in this dataset?",
    ]

    if numeric:
        primary = numeric[0]
        suggestions.extend([
            f"What is the average {primary}?",
            f"What is the maximum {primary}?",
            f"What is the minimum {primary}?",
        ])
        if len(numeric) > 1:
            second = numeric[1]
            suggestions.append(f"What is the correlation between {primary} and {second}?")

    if categorical:
        category = categorical[0]
        suggestions.append(f"What is the most common value in {category}?")
        values = frame[category].dropna().astype(str).value_counts().head(3).index.tolist()
        # A category count is useful only when the observed label is a real value
        # and the existing deterministic Q&A engine can resolve it unambiguously.
        if values:
            suggestions.append(f"How many {values[0]} records are present?")

    # Add more useful numeric measures without overwhelming the interface.
    for column in numeric[1:3]:
        candidate = f"What is the average {column}?"
        if candidate not in suggestions:
            suggestions.append(candidate)

    # Keep a compact set and avoid duplicate prompts.
    suggestions = list(dict.fromkeys(suggestions))[:12]

    column_details = []
    for column in frame.columns:
        series = frame[column]
        numeric_values = pd.to_numeric(series, errors="coerce")
        if int(numeric_values.notna().sum()) >= max(2, int(rows * 0.5)):
            kind = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series) or _looks_like_date(series):
            kind = "date"
        elif series.nunique(dropna=True) <= min(50, max(2, len(frame) // 2)):
            kind = "categorical"
        else:
            kind = "text_or_identifier"
        column_details.append({
            "name": str(column),
            "type": kind,
            "missing": int(series.isna().sum()),
            "unique_values": int(series.nunique(dropna=True)),
        })

    return {
        "rows": int(rows),
        "columns": int(columns),
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "suggestions": suggestions,
        "column_profile": column_details,
        "method": "Local Pandas schema and column profiling; no external AI or API key required.",
    }
