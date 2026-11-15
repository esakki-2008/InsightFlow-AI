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


DOMAIN_SIGNATURES = {
    "sales_business": {
        "label": "Sales & Business",
        "terms": ("revenue", "sales", "profit", "product", "customer", "order", "region", "quantity", "discount", "unit price"),
    },
    "finance_stock_market": {
        "label": "Finance & Stock Market",
        "terms": ("stock", "ticker", "symbol", "open", "high", "low", "close", "market cap", "dividend", "volume", "return"),
    },
    "cybersecurity_network": {
        "label": "Cybersecurity & Network Traffic",
        "terms": ("flow", "packet", "bytes", "destination port", "source port", "protocol", "flag", "attack", "ddos", "benign", "malware", "intrusion"),
    },
    "healthcare": {
        "label": "Healthcare",
        "terms": ("patient", "diagnosis", "glucose", "blood pressure", "bmi", "heart rate", "cholesterol", "medical", "hospital", "disease"),
    },
    "education": {
        "label": "Education & Student Performance",
        "terms": ("student", "grade", "exam", "score", "attendance", "subject", "marks", "gpa", "school", "course"),
    },
}


def _detect_domain(frame: pd.DataFrame) -> dict:
    names = [_clean_name(column) for column in frame.columns]
    # Small value samples help recognize datasets whose headers are generic.
    samples = []
    for column in frame.select_dtypes(include=["object", "category"]).columns[:8]:
        samples.extend(_clean_name(value) for value in frame[column].dropna().astype(str).head(20))
    haystack = " | ".join(names + samples)
    scores = {}
    for domain, signature in DOMAIN_SIGNATURES.items():
        score = sum(1 for term in signature["terms"] if term in haystack)
        scores[domain] = score
    best = max(scores, key=scores.get)
    if scores[best] < 2:
        return {"id": "generic", "label": "General Dataset", "confidence": "low", "scores": scores}
    ordered = sorted(scores.values(), reverse=True)
    confidence = "high" if scores[best] >= 4 and (len(ordered) == 1 or scores[best] > ordered[1]) else "medium"
    return {"id": best, "label": DOMAIN_SIGNATURES[best]["label"], "confidence": confidence, "scores": scores}


def _domain_suggestions(frame: pd.DataFrame, domain: str, numeric: list[str], categorical: list[str]) -> list[str]:
    suggestions = []
    normalized = {_clean_name(column): str(column) for column in frame.columns}

    def find_column(*terms: str) -> str | None:
        for term in terms:
            for cleaned, original in normalized.items():
                if term in cleaned:
                    return original
        return None

    if domain == "sales_business":
        for column in (find_column("revenue", "sales"), find_column("profit"), find_column("quantity"), find_column("discount")):
            if column and column in numeric:
                suggestions.append(f"What is the average {column}?")
        for column in (find_column("product"), find_column("region"), find_column("customer segment")):
            if column and column in categorical:
                suggestions.append(f"What is the most common value in {column}?")
    elif domain == "finance_stock_market":
        for column in (find_column("close", "adjusted close"), find_column("volume"), find_column("market cap", "market value")):
            if column and column in numeric:
                suggestions.append(f"What is the average {column}?")
        if len(numeric) > 1:
            suggestions.append(f"What is the correlation between {numeric[0]} and {numeric[1]}?")
    elif domain == "cybersecurity_network":
        for column in (find_column("flow duration"), find_column("flow bytes"), find_column("packet"), find_column("destination port")):
            if column and column in numeric:
                suggestions.append(f"What is the average {column}?")
        label = find_column("label", "attack type", "class", "traffic type")
        if label and label in categorical:
            suggestions.append(f"What is the most common value in {label}?")
            values = frame[label].dropna().astype(str).value_counts().head(2).index.tolist()
            if values:
                suggestions.append(f"How many {values[0]} records are present?")
    elif domain == "healthcare":
        for column in (find_column("glucose"), find_column("blood pressure"), find_column("bmi"), find_column("age"), find_column("heart rate")):
            if column and column in numeric:
                suggestions.append(f"What is the average {column}?")
        category = find_column("diagnosis", "disease", "outcome")
        if category and category in categorical:
            suggestions.append(f"What is the most common value in {category}?")
    elif domain == "education":
        for column in (find_column("exam score", "marks", "grade", "score"), find_column("attendance"), find_column("gpa")):
            if column and column in numeric:
                suggestions.append(f"What is the average {column}?")
        category = find_column("subject", "course", "grade", "class")
        if category and category in categorical:
            suggestions.append(f"What is the most common value in {category}?")
    return list(dict.fromkeys(suggestions))


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
    domain = _detect_domain(frame)
    domain_prompts = _domain_suggestions(frame, domain["id"], numeric, categorical)
    suggestions: list[str] = [
        "How many rows are in the dataset?",
        "How many missing values are there?",
        "How many duplicate rows are there?",
        "What columns are available in this dataset?",
    ]

    suggestions.extend(domain_prompts)

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
        "domain": domain,
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "suggestions": suggestions,
        "column_profile": column_details,
        "method": "Local Pandas schema and column profiling; no external AI or API key required.",
    }
