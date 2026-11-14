from __future__ import annotations

import numpy as np
import pandas as pd


SUPPORTED_CHARTS = {"bar", "line", "pie", "donut", "histogram", "scatter"}
SUPPORTED_AGGREGATIONS = {"sum", "mean", "median", "count"}


def generate_chart_data(
    dataframe: pd.DataFrame,
    x_column: str,
    y_column: str = "",
    chart_type: str = "bar",
    aggregation: str = "sum",
    filter_column: str = "",
    filter_value: str = "",
) -> dict:
    """Build chart-ready aggregates from the full uploaded dataset."""
    if dataframe.empty:
        raise ValueError("Cannot build a chart from an empty dataset.")

    frame = dataframe.copy(deep=False)
    frame.columns = [str(column).strip() for column in frame.columns]

    if chart_type not in SUPPORTED_CHARTS:
        raise ValueError(f"Unsupported chart type. Choose: {', '.join(sorted(SUPPORTED_CHARTS))}.")
    if aggregation not in SUPPORTED_AGGREGATIONS:
        raise ValueError("Aggregation must be sum, mean, median, or count.")
    if x_column not in frame.columns:
        raise ValueError(f"X-axis column '{x_column}' was not found.")
    if y_column and y_column not in frame.columns:
        raise ValueError(f"Y-axis column '{y_column}' was not found.")

    if filter_column:
        if filter_column not in frame.columns:
            raise ValueError(f"Filter column '{filter_column}' was not found.")
        if filter_value.strip():
            frame = frame[frame[filter_column].astype("string").fillna("(Missing)") == filter_value]
        if frame.empty:
            raise ValueError("No records match the selected filter.")

    if chart_type == "histogram":
        values = pd.to_numeric(frame[x_column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        if values.empty:
            raise ValueError("Histogram requires a numeric X-axis column with valid values.")
        bins = min(20, max(5, int(np.sqrt(len(values)))))
        counts, edges = np.histogram(values.to_numpy(), bins=bins)
        points = [
            {"label": f"{edges[i]:.4g} – {edges[i + 1]:.4g}", "value": int(counts[i])}
            for i in range(len(counts))
        ]
        return {"chart_type": chart_type, "x_column": x_column, "y_column": "",
                "aggregation": "count", "points": points, "total_records": int(len(frame)), "filtered_records": int(len(values)), "filter_column": filter_column, "filter_value": filter_value}

    if chart_type == "scatter":
        if not y_column:
            raise ValueError("Scatter charts require both X-axis and Y-axis columns.")
        x_values = pd.to_numeric(frame[x_column], errors="coerce")
        y_values = pd.to_numeric(frame[y_column], errors="coerce")
        pairs = pd.DataFrame({"x": x_values, "y": y_values}).replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        if pairs.empty:
            raise ValueError("Scatter charts require numeric X and Y columns with valid values.")
        if len(pairs) > 500:
            pairs = pairs.sample(n=500, random_state=42).sort_index()
        points = [{"label": str(i), "x": float(row.x), "value": float(row.y)}
                  for i, row in enumerate(pairs.itertuples(index=False))]
        return {"chart_type": chart_type, "x_column": x_column, "y_column": y_column,
                "aggregation": "none", "points": points, "total_records": int(len(frame)), "filtered_records": int(len(pairs)), "filter_column": filter_column, "filter_value": filter_value}

    x_values = frame[x_column].astype("string").fillna("(Missing)")
    if y_column and aggregation != "count":
        y_values = pd.to_numeric(frame[y_column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        working = pd.DataFrame({"label": x_values, "value": y_values}).dropna(subset=["value"])
        if working.empty:
            raise ValueError("Y-axis column has no valid numeric values for this aggregation.")
        grouped = working.groupby("label", dropna=False)["value"].agg(aggregation)
    else:
        working = pd.DataFrame({"label": x_values})
        grouped = working.groupby("label", dropna=False).size()

    grouped = grouped.sort_values(ascending=False).head(20)
    points = [{"label": str(label), "value": float(value)}
              for label, value in grouped.items()]
    return {"chart_type": chart_type, "x_column": x_column, "y_column": y_column,
            "aggregation": aggregation if y_column and aggregation != "count" else "count",
            "y_column": y_column if aggregation != "count" else "",
            "points": points, "total_records": int(len(frame)), "filtered_records": int(len(frame)),
            "filter_column": filter_column, "filter_value": filter_value,
            "note": "Showing the top 20 groups by value."}
