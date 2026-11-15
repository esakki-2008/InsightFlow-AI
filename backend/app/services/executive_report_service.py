import pandas as pd

from app.services.data_quality_service import generate_data_quality_report
from app.services.insights_service import generate_dataset_insights
from app.services.statistical_analysis_service import generate_statistical_analysis


def generate_executive_report(dataframe: pd.DataFrame, filename: str) -> dict:
    """Build a deterministic executive report from local dataset analysis."""
    if dataframe is None or dataframe.empty:
        raise ValueError("Cannot create a report from an empty dataset.")

    quality = generate_data_quality_report(dataframe)
    insight_result = generate_dataset_insights(dataframe)
    statistical = generate_statistical_analysis(dataframe)

    q = quality["summary"]
    summary = (
        f"The dataset {filename} contains {q['total_rows']:,} records across "
        f"{q['total_columns']:,} columns, with {q['completeness_percentage']:.2f}% "
        f"cell completeness and a heuristic quality score of {q['quality_score']}/100 "
        f"({q['quality_grade']}). The analysis generated "
        f"{len(insight_result['insights'])} descriptive insight(s), evaluated "
        f"{statistical['overview']['correlation_pairs_analyzed']} numeric relationships, "
        f"and ran {statistical['overview']['group_comparisons_analyzed']} eligible group comparisons."
    )

    findings = []
    for item in quality.get("findings", []):
        findings.append({
            "area": "Data quality",
            "priority": item.get("severity", "info"),
            "title": item.get("title", "Data quality observation"),
            "detail": item.get("detail", ""),
            "recommendation": item.get("recommendation", ""),
        })
    for item in insight_result.get("insights", []):
        findings.append({
            "area": item.get("category", "Dataset insight").replace("_", " ").title(),
            "priority": item.get("severity", "info"),
            "title": item.get("title", "Dataset observation"),
            "detail": item.get("description", ""),
            "recommendation": "Review the supporting evidence and validate the observation with domain knowledge.",
        })

    significant = [
        item for item in statistical.get("correlations", [])
        if item.get("significant_at_5_percent")
    ]
    for item in significant[:5]:
        findings.append({
            "area": "Statistical relationship",
            "priority": "info",
            "title": f"{item['left']} and {item['right']} are associated",
            "detail": (
                f"Pearson r={item['pearson_r']}; Spearman rho={item['spearman_rho']}; "
                f"n={item['sample_size']}; Pearson p={item['pearson_p_value']:.3g}."
            ),
            "recommendation": "Treat this as an association, not evidence that one feature causes the other.",
        })

    recommendations = []
    if q["missing_cells"] or q["duplicate_rows"] or q["constant_columns"]:
        recommendations.append("Resolve or document missing values, duplicate records, and constant fields before downstream modeling.")
    if q["high_cardinality_columns"]:
        recommendations.append("Review high-cardinality fields to distinguish identifiers from meaningful categorical variables.")
    if not recommendations:
        recommendations.append("Proceed to exploratory analysis while validating domain-specific ranges, labels, and data collection rules.")
    if significant:
        recommendations.append("Investigate the strongest statistical relationships with domain context; check for leakage, derived fields, and confounding.")
    if statistical["overview"]["group_comparisons_analyzed"]:
        recommendations.append("For group differences, inspect group sizes, ANOVA assumptions, effect sizes, and multiple-testing adjustments before making decisions.")

    return {
        "filename": filename,
        "summary": summary,
        "kpis": {
            "rows": q["total_rows"],
            "columns": q["total_columns"],
            "quality_score": q["quality_score"],
            "completeness_percentage": q["completeness_percentage"],
            "missing_cells": q["missing_cells"],
            "duplicate_rows": q["duplicate_rows"],
            "insights_count": len(insight_result["insights"]),
            "correlation_pairs": statistical["overview"]["correlation_pairs_analyzed"],
            "group_comparisons": statistical["overview"]["group_comparisons_analyzed"],
        },
        "findings": findings[:20],
        "recommendations": recommendations,
        "limitations": [
            "This report is generated from descriptive and statistical calculations; it is not a causal analysis.",
            "The data-quality score is a heuristic screening metric, not a universal standard.",
            "P-values are unadjusted for multiple comparisons; validate assumptions, sample design, and practical effect sizes.",
            "Derived or target-like columns can create circular relationships or data leakage.",
            "Recommendations are prompts for review and do not replace domain expertise.",
        ],
        "generation": "Deterministic local analysis; no external AI provider is called and raw dataset rows are not transmitted to an LLM.",
    }
