from datetime import datetime
from typing import Any, Dict, List


WEAKNESSES_DB = {
    "dataset_understanding": {
        "description": "AI struggles to correctly identify dataset domain, schema, and structure",
        "common_causes": [
            "Column naming inconsistencies across datasets",
            "Lack of domain-specific heuristics for certain industry schemas",
            "Incomplete semantic profiling of dataset columns",
            "Missing or ambiguous column type detection",
        ],
        "improvements": [
            "Expand ENTITY_KEYWORD_MAP with domain-specific aliases for each industry",
            "Add confidence scoring to domain detection based on signal strength",
            "Implement cross-dataset schema comparison for better generalization",
            "Add a training phase that learns column-to-entity mappings from labeled examples",
        ],
    },
    "entity_detection": {
        "description": "Entity detection fails to identify all business entities in a dataset",
        "common_causes": [
            "Keyword matching is too rigid and misses synonyms",
            "No support for compound entity names",
            "Entity detection relies solely on column name patterns",
            "Missing support for multi-word entity references",
        ],
        "improvements": [
            "Add synonym expansion using a domain-specific thesaurus",
            "Implement ML-based column name embedding similarity",
            "Add support for regex patterns beyond simple keyword matching",
            "Incorporate data type analysis to disambiguate entity types",
        ],
    },
    "metric_detection": {
        "description": "Metric detection fails to identify all quantitative metrics",
        "common_causes": [
            "Metric keywords are domain-specific and not universally matched",
            "Numeric columns are sometimes misclassified as dimensions",
            "Aggregated columns (e.g., total_revenue) are not in the profiler",
            "No support for derived or computed metrics",
        ],
        "improvements": [
            "Add metric detection based on data type (high cardinality numeric = likely measure)",
            "Implement a metric name pattern classifier (percentage, ratio, rate, count, sum)",
            "Add support for detecting computed fields from column naming patterns",
            "Cross-reference metric names with common industry metric vocabularies",
        ],
    },
    "sql_generation": {
        "description": "SQL generation produces syntactically incorrect or semantically wrong queries",
        "common_causes": [
            "Column name resolution fails when entity names don't map directly to columns",
            "Aggregation function selection is heuristic-based and sometimes wrong",
            "GROUP BY and ORDER BY clauses are missing for top-N and breakdown queries",
            "Date truncation functions vary across SQL dialects",
        ],
        "improvements": [
            "Add schema-aware column aliasing in SQL generation",
            "Implement a SQL syntax validator before execution",
            "Add intent-specific SQL templates with fallbacks",
            "Incorporate user feedback loop to correct SQL generation errors",
        ],
    },
    "recommendations": {
        "description": "Recommendation quality is low - suggestions are generic or unsupported",
        "common_causes": [
            "Recommendation engine lacks domain-specific action logic",
            "Recommendations are generated from summary statistics rather than deep analysis",
            "No causal reasoning - correlations are mistaken for recommendations",
            "Lack of business context in recommendation generation",
        ],
        "improvements": [
            "Add domain-specific recommendation templates (e.g., retail: restock, price optimize)",
            "Implement causal analysis to distinguish correlation from causation",
            "Add business rule engine to validate recommendation feasibility",
            "Incorporate user feedback to rank recommendation quality over time",
        ],
    },
    "hallucination_prevention": {
        "description": "AI generates unsupported claims or fabricates data in responses",
        "common_causes": [
            "Validation layer does not trace all numeric claims to source queries",
            "Confidence scores are heuristic-based, not evidence-weighted",
            "No negative constraints on what the AI should not claim",
            "Missing cross-reference between answer text and actual SQL results",
        ],
        "improvements": [
            "Implement per-numeric-claim traceability requiring SQL snippet evidence",
            "Add a post-hoc fact-checking module that re-queries claimed values",
            "Lower confidence thresholds for questions with ambiguous schema matches",
            "Add a 'did not find' response mode when evidence is insufficient",
        ],
    },
    "visualization_quality": {
        "description": "Visualization generation produces incorrect or incomplete chart configurations",
        "common_causes": [
            "Chart type selection is based on simple intent matching, not data characteristics",
            "Missing support for some analysis types (e.g., distribution, forecast)",
            "Chart configurations lack proper scale and axis settings",
            "No validation that chart data columns exist in the dataset",
        ],
        "improvements": [
            "Add data-driven chart type selection based on column types and cardinality",
            "Implement chart configuration validation before rendering",
            "Add support for more chart types (heatmap, histogram, box plot, Sankey)",
            "Incorporate user-defined visualization preferences and constraints",
        ],
    },
}


def generate_weaknesses_report(evaluation_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a detailed weaknesses and suggestions report based on evaluation results.
    """
    dataset_results = evaluation_report.get("dataset_results", [])
    overall_scores = evaluation_report.get("overall_scores", {})

    dimension_scores = {}
    for result in dataset_results:
        for score_entry in result.get("scores", []):
            dim = score_entry.get("dimension", "")
            score = score_entry.get("score", 0.0)
            if dim not in dimension_scores:
                dimension_scores[dim] = []
            dimension_scores[dim].append(score)

    avg_dimension_scores = {
        dim: round(sum(scores) / len(scores), 4)
        for dim, scores in dimension_scores.items()
        if scores
    }

    domain_weaknesses = {}
    for result in dataset_results:
        domain = result.get("domain", "Unknown")
        if domain not in domain_weaknesses:
            domain_weaknesses[domain] = {"weaknesses": [], "suggestions": []}
        domain_weaknesses[domain]["weaknesses"].extend(result.get("weaknesses", []))
        domain_weaknesses[domain]["suggestions"].extend(result.get("suggestions", []))

    low_scoring_dimensions = {
        dim: score for dim, score in avg_dimension_scores.items()
        if score < 0.7
    }

    critical_weaknesses = []
    for dim, score in sorted(low_scoring_dimensions.items(), key=lambda x: x[1]):
        db_entry = WEAKNESSES_DB.get(dim, {})
        critical_weaknesses.append({
            "dimension": dim,
            "average_score": score,
            "description": db_entry.get("description", "No description available"),
            "common_causes": db_entry.get("common_causes", []),
            "suggested_improvements": db_entry.get("improvements", []),
        })

    report = {
        "generated_at": datetime.now().isoformat(),
        "overall_scores": overall_scores,
        "average_dimension_scores": avg_dimension_scores,
        "low_scoring_dimensions": low_scoring_dimensions,
        "domain_breakdown": {k: {"weakness_count": len(v["weaknesses"]), "suggestion_count": len(v["suggestions"])} for k, v in domain_weaknesses.items()},
        "critical_weaknesses": critical_weaknesses,
        "weaknesses_by_domain": domain_weaknesses,
        "global_suggestions": list(dict.fromkeys(
            s for result in dataset_results for s in result.get("suggestions", [])
        )),
    }

    return report


def generate_markdown_report(evaluation_report: Dict[str, Any]) -> str:
    """
    Generates a human-readable Markdown report from evaluation results.
    """
    overall_scores = evaluation_report.get("overall_scores", {})
    weakness_report = generate_weaknesses_report(evaluation_report)

    lines = []
    lines.append("# DecisionLens AI Evaluation Report")
    lines.append("")
    lines.append(f"**Generated:** {evaluation_report.get('generated_at', 'N/A')}")
    lines.append("")

    lines.append("## Overall AI Quality Scores")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    for metric, score in overall_scores.items():
        pct = f"{score * 100:.1f}%"
        lines.append(f"| {metric} | {pct} |")
    lines.append("")

    lines.append("## Dataset-Level Results")
    lines.append("")
    for result in evaluation_report.get("dataset_results", []):
        lines.append(f"### {result.get('domain', 'Unknown')} ({result.get('dataset_name', 'unknown')})")
        lines.append("")
        lines.append(f"- **Overall Accuracy:** {result.get('overall_accuracy', 0):.4f}")
        lines.append(f"- **Business Understanding:** {result.get('business_understanding', 0):.4f}")
        lines.append(f"- **Recommendation Quality:** {result.get('recommendation_quality', 0):.4f}")
        lines.append(f"- **SQL Accuracy:** {result.get('sql_accuracy', 0):.4f}")
        lines.append(f"- **Visualization Quality:** {result.get('visualization_quality', 0):.4f}")

        if result.get("weaknesses"):
            lines.append("")
            lines.append("**Weaknesses:**")
            for w in result.get("weaknesses", [])[:5]:
                lines.append(f"- {w}")

        if result.get("suggestions"):
            lines.append("")
            lines.append("**Suggestions:**")
            for s in result.get("suggestions", [])[:5]:
                lines.append(f"- {s}")

        lines.append("")

    lines.append("## Critical Weaknesses")
    lines.append("")
    for cw in weakness_report.get("critical_weaknesses", []):
        lines.append(f"### {cw.get('dimension', 'Unknown')} (Score: {cw.get('average_score', 0):.4f})")
        lines.append("")
        lines.append(f"{cw.get('description', '')}")
        lines.append("")

        if cw.get("common_causes"):
            lines.append("**Common Causes:**")
            for cause in cw.get("common_causes", []):
                lines.append(f"- {cause}")
            lines.append("")

        if cw.get("suggested_improvements"):
            lines.append("**Suggested Improvements:**")
            for imp in cw.get("suggested_improvements", []):
                lines.append(f"- {imp}")
            lines.append("")

    lines.append("## Global Improvement Suggestions")
    lines.append("")
    for i, suggestion in enumerate(weakness_report.get("global_suggestions", []), 1):
        lines.append(f"{i}. {suggestion}")
    lines.append("")

    return "\n".join(lines)