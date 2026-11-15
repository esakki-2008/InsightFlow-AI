import math
import re

import numpy as np
import pandas as pd
from scipy import stats


_IDENTIFIER = re.compile(
    r"(^id$|(^|[_\\s-])id($|[_\\s-])|uuid|guid|identifier|serial|roll[_\\s-]?no|student[_\\s-]?no|customer[_\\s-]?no|account[_\\s-]?no)",
    re.IGNORECASE,
)


def generate_statistical_analysis(dataframe: pd.DataFrame) -> dict:
    """Generate distribution, correlation, and group-significance summaries."""
    if dataframe is None or dataframe.empty:
        raise ValueError("Cannot analyze an empty dataset.")

    frame = dataframe.copy(deep=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Column names are duplicated after whitespace normalization.")

    numeric_columns = [
        name for name in frame.select_dtypes(include="number").columns
        if not _IDENTIFIER.search(str(name))
    ][:30]
    categorical_columns = [
        name for name in frame.select_dtypes(include=["object", "category", "bool"]).columns
        if not _IDENTIFIER.search(str(name))
    ][:12]

    distributions = []
    for name in numeric_columns:
        values = pd.to_numeric(frame[name], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        if values.empty:
            continue
        q1, median, q3 = (float(values.quantile(q)) for q in (0.25, 0.5, 0.75))
        std = float(values.std()) if len(values) > 1 else 0.0
        mean = float(values.mean())
        skew = float(values.skew()) if len(values) > 2 else None
        kurtosis = float(values.kurt()) if len(values) > 3 else None
        normality = None
        if 3 <= len(values) <= 5000 and values.nunique() > 1:
            sample = values.to_numpy()
            try:
                statistic, p_value = stats.shapiro(sample)
                normality = {
                    "test": "Shapiro-Wilk",
                    "statistic": round(float(statistic), 5),
                    "p_value": round(float(p_value), 6),
                    "interpretation": (
                        "Evidence against a normal distribution at 5% significance"
                        if p_value < 0.05 else
                        "Insufficient evidence to reject normality at 5% significance"
                    ),
                }
            except (ValueError, FloatingPointError):
                normality = None
        distributions.append({
            "column": str(name),
            "count": int(len(values)),
            "mean": round(mean, 6),
            "median": round(median, 6),
            "std_dev": round(std, 6),
            "min": round(float(values.min()), 6),
            "q1": round(q1, 6),
            "q3": round(q3, 6),
            "max": round(float(values.max()), 6),
            "skewness": round(skew, 6) if skew is not None and math.isfinite(skew) else None,
            "kurtosis": round(kurtosis, 6) if kurtosis is not None and math.isfinite(kurtosis) else None,
            "normality_test": normality,
        })

    correlations = []
    for i, left in enumerate(numeric_columns):
        for right in numeric_columns[i + 1:]:
            pair = frame[[left, right]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(pair) < 3 or pair[left].nunique() < 2 or pair[right].nunique() < 2:
                continue
            pearson, pearson_p = stats.pearsonr(pair[left], pair[right])
            spearman, spearman_p = stats.spearmanr(pair[left], pair[right])
            if not all(math.isfinite(float(v)) for v in (pearson, pearson_p, spearman, spearman_p)):
                continue
            correlations.append({
                "left": str(left), "right": str(right), "sample_size": int(len(pair)),
                "pearson_r": round(float(pearson), 5),
                "pearson_p_value": round(float(pearson_p), 7),
                "spearman_rho": round(float(spearman), 5),
                "spearman_p_value": round(float(spearman_p), 7),
                "strength": "strong" if abs(pearson) >= 0.7 else "moderate" if abs(pearson) >= 0.4 else "weak",
                "significant_at_5_percent": bool(pearson_p < 0.05),
            })
    correlations.sort(key=lambda item: abs(item["pearson_r"]), reverse=True)

    group_comparisons = []
    for category in categorical_columns:
        groups = frame[category].dropna().unique().tolist()
        if len(groups) < 2 or len(groups) > 10:
            continue
        for numeric in numeric_columns[:10]:
            samples = []
            labels = []
            for group in groups:
                values = pd.to_numeric(
                    frame.loc[frame[category] == group, numeric], errors="coerce"
                ).replace([np.inf, -np.inf], np.nan).dropna()
                if len(values) >= 2:
                    samples.append(values.to_numpy())
                    labels.append(str(group))
            if len(samples) < 2:
                continue
            try:
                statistic, p_value = stats.f_oneway(*samples)
            except (ValueError, FloatingPointError):
                continue
            if not math.isfinite(float(statistic)) or not math.isfinite(float(p_value)):
                continue
            group_comparisons.append({
                "category_column": str(category),
                "numeric_column": str(numeric),
                "groups": [
                    {"name": label, "count": int(len(sample)), "mean": round(float(np.mean(sample)), 5)}
                    for label, sample in zip(labels, samples)
                ],
                "test": "One-way ANOVA",
                "f_statistic": round(float(statistic), 5),
                "p_value": round(float(p_value), 7),
                "significant_at_5_percent": bool(p_value < 0.05),
            })

    group_comparisons.sort(key=lambda item: item["p_value"])
    return {
        "overview": {
            "numeric_features_analyzed": len(distributions),
            "correlation_pairs_analyzed": len(correlations),
            "group_comparisons_analyzed": len(group_comparisons),
        },
        "distributions": distributions,
        "correlations": correlations[:50],
        "group_comparisons": group_comparisons[:50],
        "methodology": {
            "normality": "Shapiro-Wilk test, only for columns with 3 to 5,000 valid observations.",
            "correlation": "Pearson linear correlation and Spearman rank correlation, pairwise complete observations.",
            "group_comparison": "One-way ANOVA for numeric features across categorical groups with at least two valid observations each.",
            "significance": "p < 0.05 is flagged as statistically significant; this does not establish causation.",
            "limits": "P-values are unadjusted for multiple comparisons. Check assumptions, sample design, outliers, and practical effect size before drawing conclusions.",
        },
    }
