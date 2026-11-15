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

    # Prefer columns whose names indicate useful business measures or dates/prices.
    priority_terms = (
        "price", "close", "open", "high", "low", "volume", "revenue",
        "sales", "profit", "amount", "cost", "salary", "score", "duration",
        "rate", "count", "total", "temperature", "rain", "age", "quantity",
    )

    def score_column(name: str) -> int:
        normalized = _clean_name(name)
        return sum(1 for term in priority_terms if term in normalized)

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
        elif pd.api.types.is_datetime64_any_dtype(series):
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
