from __future__ import annotations

import re
from difflib import get_close_matches

import numpy as np
import pandas as pd


AGGREGATIONS = {
    "average": "mean",
    "mean": "mean",
    "median": "median",
    "minimum": "min",
    "min": "min",
    "maximum": "max",
    "max": "max",
    "sum": "sum",
    "total": "sum",
    "standard deviation": "std",
    "std": "std",
}


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _resolve_column(frame: pd.DataFrame, text: str) -> str | None:
    """Resolve a user-mentioned column without executing user-supplied code."""
    cleaned = _normalise(text)
    if not cleaned:
        return None

    normalized = {_normalise(column): str(column) for column in frame.columns}
    if cleaned in normalized:
        return normalized[cleaned]

    # Prefer the longest exact column-name phrase contained in the question.
    matches = [
        (len(name), column)
        for name, column in normalized.items()
        if name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", cleaned)
    ]
    if matches:
        return max(matches)[1]

    # Fuzzy matching is only accepted for a clear, high-similarity match.
    words = cleaned.split()
    candidates = list(normalized)
    for size in range(min(8, len(words)), 0, -1):
        for start in range(len(words) - size + 1):
            phrase = " ".join(words[start:start + size])
            close = get_close_matches(phrase, candidates, n=1, cutoff=0.88)
            if close:
                return normalized[close[0]]
    return None


def _format_number(value) -> int | float | None:
    if pd.isna(value) or not np.isfinite(float(value)):
        return None
    number = float(value)
    return int(number) if number.is_integer() else round(number, 6)


def answer_dataset_question(dataframe: pd.DataFrame, question: str) -> dict:
    """Answer a limited set of natural-language questions using safe Pandas operations."""
    if dataframe.empty:
        raise ValueError("The uploaded dataset has no rows.")
    if not question or not question.strip():
        raise ValueError("Enter a question about your dataset.")

    frame = dataframe.copy(deep=False)
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Column names must be unique to query this dataset.")

    q = _normalise(question)
    rows, columns = frame.shape

    def response(query_type: str, answer: str, result: dict) -> dict:
        return {
            "question": question.strip(),
            "answer": answer,
            "query_type": query_type,
            "result": result,
            "rows_analyzed": int(rows),
        }

    if any(term in q for term in ("missing value", "missing data", "null value", "null count", "empty value")):
        total = int(frame.isna().sum().sum())
        by_column = frame.isna().sum()
        details = [
            {"column": str(name), "missing": int(count)}
            for name, count in by_column.items() if count > 0
        ]
        details.sort(key=lambda item: item["missing"], reverse=True)
        return response("missing_values", f"The dataset contains {total:,} missing value(s).", {
            "missing_values": total, "columns_with_missing_values": details[:20]
        })

    if "duplicate" in q:
        count = int(frame.duplicated().sum())
        return response("duplicates", f"The dataset contains {count:,} exact duplicate row(s).", {
            "duplicate_rows": count
        })

    if any(term in q for term in ("how many rows", "number of rows", "row count", "records are there", "dataset size")):
        return response("row_count", f"The dataset contains {rows:,} rows and {columns:,} columns.", {
            "rows": int(rows), "columns": int(columns)
        })

    if "column" in q and any(term in q for term in ("list", "show", "what are", "available")):
        names = [str(name) for name in frame.columns]
        return response("columns", f"The dataset has {columns} columns: {', '.join(names)}.", {
            "columns": names
        })

    correlation_match = re.search(r"(?:correlation|correlate|relationship) between (.+?) and (.+)", question, re.I)
    if correlation_match:
        left = _resolve_column(frame, correlation_match.group(1))
        right = _resolve_column(frame, correlation_match.group(2))
        if not left or not right:
            raise ValueError("I couldn't identify both column names. Use their exact dataset column names.")
        if left == right:
            raise ValueError("Choose two different columns for correlation.")
        left_values = pd.to_numeric(frame[left], errors="coerce")
        right_values = pd.to_numeric(frame[right], errors="coerce")
        valid = left_values.notna() & right_values.notna() & np.isfinite(left_values) & np.isfinite(right_values)
        if int(valid.sum()) < 2:
            raise ValueError("At least two rows with numeric values in both columns are required.")
        corr = float(left_values[valid].corr(right_values[valid]))
        strength = "strong" if abs(corr) >= 0.7 else "moderate" if abs(corr) >= 0.4 else "weak"
        direction = "positive" if corr > 0 else "negative" if corr < 0 else "zero"
        return response("correlation", f"{left} and {right} have a {strength} {direction} correlation (r = {corr:.3f}) based on {int(valid.sum()):,} rows.", {
            "column_a": left, "column_b": right, "correlation": round(corr, 6),
            "strength": strength, "direction": direction, "valid_rows": int(valid.sum())
        })

    agg = next((value for phrase, value in sorted(AGGREGATIONS.items(), key=lambda item: -len(item[0])) if re.search(rf"\b{re.escape(phrase)}\b", q)), None)
    if agg:
        # Remove aggregation words and common filler before resolving the requested column.
        remainder = q
        for phrase in sorted(AGGREGATIONS, key=len, reverse=True):
            remainder = re.sub(rf"\b{re.escape(phrase)}\b", " ", remainder)
        remainder = re.sub(r"\b(of|for|the|in|on|column|values|value|is|what|are|calculate|give|me)\b", " ", remainder)
        column = _resolve_column(frame, remainder)
        if not column:
            raise ValueError("I couldn't identify the column. Include its exact name, for example: What is the mean Flow Duration?")
        values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if values.empty:
            raise ValueError(f"{column} does not contain usable numeric values.")
        calculated = getattr(values, agg)()
        value = _format_number(calculated)
        label = {"mean": "average", "median": "median", "min": "minimum", "max": "maximum", "sum": "sum", "std": "standard deviation"}[agg]
        return response("numeric_aggregation", f"The {label} of {column} is {value:,} (from {len(values):,} valid numeric values)." if isinstance(value, int) else f"The {label} of {column} is {value} (from {len(values):,} valid numeric values).", {
            "column": column, "aggregation": agg, "value": value, "valid_values": int(len(values))
        })

    if any(term in q for term in ("most common", "most frequent", "top category", "dominant value", "most popular")):
        remainder = re.sub(r"\b(what|is|are|the|most|common|frequent|top|category|dominant|value|popular|in|for|of|column|show|me)\b", " ", q)
        column = _resolve_column(frame, remainder)
        if not column:
            # If no column is named, choose the first categorical column only when unambiguous.
            categorical = frame.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
            if len(categorical) == 1:
                column = str(categorical[0])
            else:
                raise ValueError("Specify the categorical column, for example: What is the most common value in Label?")
        counts = frame[column].astype("string").fillna("(Missing)").value_counts(dropna=False)
        if counts.empty:
            raise ValueError(f"{column} has no values to summarize.")
        value = str(counts.index[0])
        count = int(counts.iloc[0])
        pct = round(count / rows * 100, 2)
        return response("most_common_value", f"The most common value in {column} is {value} ({count:,} rows, {pct:.2f}% of the dataset).", {
            "column": column, "value": value, "count": count, "percentage": pct,
            "top_values": [{"value": str(index), "count": int(count)} for index, count in counts.head(10).items()]
        })

    # Count a named class/category, e.g. "How many DDoS records are present?"
    value_match = re.search(
        r"how many (.+?)(?: records?| rows?| samples?)?(?: are present| is present| exist| present| in the dataset)?$",
        q,
    )
    if value_match:
        requested = value_match.group(1).strip()
        requested = re.sub(r"\b(the|there|are|is|present|in|dataset)\b", " ", requested).strip()
        categorical = frame.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
        matches = []
        for column in categorical:
            series = frame[column].astype("string")
            mask = series.str.casefold() == requested.casefold()
            if bool(mask.any()):
                matches.append((str(column), int(mask.sum())))
        if len(matches) == 1:
            column, count = matches[0]
            return response("category_count", f"There are {count:,} {requested} records in {column}.", {
                "column": column, "value": requested, "count": count,
                "percentage": round(count / rows * 100, 2)
            })
        if len(matches) > 1:
            details = [{"column": name, "count": count} for name, count in matches]
            return response("category_count", f"The value {requested} appears in multiple categorical columns.", {
                "value": requested, "matches": details
            })
    raise ValueError(
        "I couldn't interpret that question yet. Try asking for a row count, missing values, "
        "duplicate rows, the most common value in a column, a numeric average/minimum/maximum, "
        "a category count, or the correlation between two numeric columns."
    )
