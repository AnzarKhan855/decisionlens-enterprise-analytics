from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import UTC, datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from app.ai.explainable_ai_engine import ExplainableAIEngine
from app.ai.evidence_builder import EvidenceBuilder
from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.analytics.anomaly_engine import StatisticalAnomalyEngine
from app.analytics.variance_engine import VarianceDecompositionEngine
from app.analytics.recommendation_engine import RecommendationEngine, MetricDetector
from app.analytics.health_engine import BusinessHealthEngine
from app.analytics.chart_engine import ChartEngine
from app.analytics.derived_metrics import discover_derived_metrics, discover_transaction_identifier
from app.database.duckdb_engine import DuckDBEngine
from app.ml.prediction_engine import UniversalPredictionEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.semantic_model.core import SemanticModel
from app.schemas.analytics import (
    AnalyticsResult,
    KPIMetric,
    RootCause,
    DriverContribution,
    BusinessAnomaly,
    Outlier,
    Prediction,
    Recommendation,
    RiskItem,
    OpportunityItem,
    HealthScore,
    TrendPoint,
    DistributionItem,
    GrowthDecline,
    RankItem,
    Correlation,
    SegmentComparison,
)
from app.logging.logger import get_logger
logger = get_logger(__name__)


class UniversalAnalyticsEngine:
    """
    Universal Analytics & Intelligence Engine.
    Input: SemanticModel + parquet_path + optional profile
    Output: AnalyticsResult (Canonical Analytics Object)

    Orchestrates all existing statistical engines into one unified result
    that answers:
      1. What happened?
      2. Why did it happen?
      3. What will happen?
      4. What should we do?

    No module may analyze datasets independently.
    Every analysis flows through this engine.
    """

    @classmethod
    def analyze(
        cls,
        semantic_model: SemanticModel,
        parquet_path: Optional[Path] = None,
        dataset_id: Optional[str] = None,
        profile: Optional[Dict[str, Any]] = None,
        workspace_id: str = "",
    ) -> AnalyticsResult:
        errors: List[str] = []

        path = parquet_path or cls._resolve_parquet_path(semantic_model, dataset_id)
        if not path or not path.exists():
            return cls._empty_result(semantic_model, workspace_id, "No dataset available for analysis")

        if profile is None:
            try:
                from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
                cached_intelligence = DatasetIntelligenceLayer.get_cached(
                    semantic_model.workspace_id or dataset_id or workspace_id or ""
                )
                if cached_intelligence is not None:
                    profile = {
                        "total_rows": cached_intelligence.profile.total_records,
                        "total_columns": cached_intelligence.profile.total_columns,
                        "column_categories": {
                            "measures": cached_intelligence.profile.detected_measures,
                            "dimensions": cached_intelligence.profile.detected_dimensions,
                            "temporal": cached_intelligence.profile.detected_temporal,
                            "identifiers": [c.name for c in cached_intelligence.columns if c.is_identifier],
                        },
                        "columns": {
                            c.name: {
                                "data_type": c.data_type,
                                "category": "measure" if c.is_measure else "dimension" if c.is_dimension else "temporal" if c.is_temporal else "identifier" if c.is_identifier else "dimension",
                                "null_percentage": c.null_percentage,
                                "distinct_count": c.distinct_count,
                            }
                            for c in cached_intelligence.columns
                        },
                    }
            except Exception as e:
                logger.debug("[UniversalAnalytics] Could not load cached profile: %s", e)

        if profile is None:
            try:
                profile = SemanticDataProfiler.profile(path)
            except Exception as e:
                errors.append(f"Profiling failed: {str(e)}")
                profile = {}

        total_rows = profile.get("total_rows", 0)
        measures = profile.get("column_categories", {}).get("measures", [])
        dimensions = profile.get("column_categories", {}).get("dimensions", [])
        temporal = profile.get("column_categories", {}).get("temporal", [])
        domain = semantic_model.domain or "Generic Business"
        dataset_name = path.name

        # =====================================================================
        # 1. WHAT HAPPENED (parallelized)
        # =====================================================================
        kpis = distributions = trends = growth = decline = rankings = correlations = None
        volume = total_rows
        utilization = performance = summary_statistics = None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "kpis": executor.submit(cls._compute_kpis, path, profile, dataset_name, total_rows, measures),
                "distributions": executor.submit(cls._compute_distributions, path, profile, dimensions, measures),
                "trends": executor.submit(cls._compute_trends, path, profile, temporal, measures),
                "rankings": executor.submit(cls._compute_rankings, path, profile, dimensions, measures),
                "correlations": executor.submit(cls._compute_correlations, path, measures),
                "utilization": executor.submit(cls._compute_utilization, path, profile, measures, dimensions),
                "summary_statistics": executor.submit(cls._compute_summary_statistics, profile, measures),
            }
            for name, future in futures.items():
                try:
                    result = future.result()
                    if name == "kpis":
                        kpis = result
                    elif name == "distributions":
                        distributions = result
                    elif name == "trends":
                        trends = result
                    elif name == "rankings":
                        rankings = result
                    elif name == "correlations":
                        correlations = result
                    elif name == "utilization":
                        utilization = result
                    elif name == "summary_statistics":
                        summary_statistics = result
                except Exception as e:
                    errors.append(f"{name} failed: {str(e)}")

        # growth/decline depend on trends
        try:
            growth, decline = cls._compute_growth_decline(path, profile, temporal, measures)
        except Exception as e:
            errors.append(f"growth_decline failed: {str(e)}")
            growth, decline = [], []

        # performance depends on kpis
        try:
            performance = cls._compute_performance(profile, kpis or [])
        except Exception as e:
            errors.append(f"performance failed: {str(e)}")
            performance = {}

        # =====================================================================
        # 2. WHY DID IT HAPPEN (parallelized)
        # =====================================================================
        root_causes = drivers = dimension_impact = segment_comparisons = None
        outliers = anomalies = None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "root_causes": executor.submit(cls._compute_root_causes, path, profile, dimensions, measures),
                "dimension_impact": executor.submit(cls._compute_dimension_impact, path, profile, dimensions, measures),
                "segment_comparisons": executor.submit(cls._compute_segment_comparisons, path, profile, dimensions, measures),
                "anomalies": executor.submit(cls._compute_anomalies, path, profile, temporal, measures, errors),
            }
            for name, future in futures.items():
                try:
                    result = future.result()
                    if name == "root_causes":
                        root_causes = result
                    elif name == "dimension_impact":
                        dimension_impact = result
                    elif name == "segment_comparisons":
                        segment_comparisons = result
                    elif name == "anomalies":
                        anomalies_result = result
                        outliers = anomalies_result.get("outliers", [])
                        anomalies = anomalies_result.get("anomalies", [])
                except Exception as e:
                    errors.append(f"{name} failed: {str(e)}")

        drivers = cls._compute_drivers(root_causes or [])
        patterns = cls._compute_patterns(trends or {}, anomalies or [], growth or [], decline or [])

        # =====================================================================
        # Charts (from ChartEngine)
        # =====================================================================
        charts: List[Dict[str, Any]] = []
        try:
            raw_charts = ChartEngine.generate_from_parquet(path, profile)
            charts = cls._normalize_charts(raw_charts or [])
            if charts:
                from app.validation.chart_validator import validate_charts
                charts = validate_charts(charts)
        except Exception as e:
            errors.append(f"charts failed: {str(e)}")

        # =====================================================================
        # Health
        # =====================================================================
        try:
            health_result = BusinessHealthEngine.calculate_health_score(profile, kpis or [], None)
            health_score = HealthScore(
                overall_score=health_result.get("overall_score", 0.0),
                grade=health_result.get("grade", "N/A"),
                status=health_result.get("status", "No Data"),
                breakdown=health_result.get("breakdown", []),
            )
        except Exception as e:
            errors.append(f"Health score failed: {str(e)}")
            health_score = HealthScore(overall_score=0.0, grade="N/A", status="Error")

        # =====================================================================
        # 3. WHAT WILL HAPPEN (predictions)
        # =====================================================================
        from types import SimpleNamespace
        partial_for_prediction = SimpleNamespace(
            trends=trends or {},
            correlations=correlations or [],
            root_causes=root_causes or [],
            drivers=drivers,
            anomalies=anomalies or [],
            outliers=outliers or [],
            kpis=kpis or [],
            volume=volume,
            confidence_score=0.0,
            evidence={},
        )
        try:
            horizons = [20, 30, 90, 180]
            predictions = UniversalPredictionEngine.generate(
                analytics_result=partial_for_prediction,
                semantic_model=semantic_model,
                horizons=horizons,
                temporal=temporal or [],
            )
            prediction_strategy = "universal_prediction_engine"
            prediction_feasible = any(p.feasible for p in predictions) if predictions else False
            prediction_limitation = next((p.limitation for p in predictions if p.limitation), None)
        except Exception as e:
            errors.append(f"Prediction engine failed: {str(e)}")
            predictions = []
            prediction_strategy = "none"
            prediction_feasible = False
            prediction_limitation = str(e)

        # =====================================================================
        # Forecast Summary (executive outlook)
        # =====================================================================
        forecast_summary = cls._compute_forecast_summary(predictions, temporal, measures, domain)

        # =====================================================================
        # 4. WHAT SHOULD WE DO
        # =====================================================================
        recommendations = cls._compute_recommendations(path, profile, dimensions, measures, root_causes or [], anomalies or [], errors)
        risks = cls._compute_risks(root_causes or [], anomalies or [], drivers, profile)
        opportunities = cls._compute_opportunities(domain, drivers, anomalies or [], growth or [], total_rows)
        key_drivers = cls._compute_key_drivers(drivers, root_causes or [])

        # =====================================================================
        # Confidence (computed after all analysis)
        # =====================================================================
        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=profile,
            kpis=kpis or [],
            predictions=predictions,
            recommendations=recommendations,
            anomalies=anomalies or [],
            errors=errors,
        )
        confidence_score = round(confidence_result.overall_score * 100.0, 1)
        evidence = cls._compute_evidence(path, profile, measures, dimensions, errors)
        evidence["confidence_factors"] = confidence_result.factors

        tables_used = evidence.get("tables_used", [])
        columns_used = evidence.get("columns_used", [])

        # =====================================================================
        # Evidence Builder (final step before executive response)
        # =====================================================================
        analytics_dict_for_evidence = {
            "kpis": [k.to_dict() if hasattr(k, "to_dict") else {k: v for k, v in k.__dict__.items()} for k in (kpis or [])],
            "trends": {k: [v.to_dict() if hasattr(v, "to_dict") else {kk: vv for kk, vv in v.__dict__.items()} for v in vals] for k, vals in (trends or {}).items()},
            "anomalies": [a.to_dict() if hasattr(a, "to_dict") else {k: v for k, v in a.__dict__.items()} for a in (anomalies or [])],
            "outliers": [o.to_dict() if hasattr(o, "to_dict") else {k: v for k, v in o.__dict__.items()} for o in (outliers or [])],
            "predictions": [p.to_dict() if hasattr(p, "to_dict") else {k: v for k, v in p.__dict__.items()} for p in predictions],
            "recommendations": [r.to_dict() if hasattr(r, "to_dict") else {k: v for k, v in r.__dict__.items()} for r in recommendations],
            "root_causes": [rc.to_dict() if hasattr(rc, "to_dict") else {k: v for k, v in rc.__dict__.items()} for rc in (root_causes or [])],
            "drivers": drivers,
            "growth": [g.to_dict() if hasattr(g, "to_dict") else {k: v for k, v in g.__dict__.items()} for g in (growth or [])],
            "decline": [d.to_dict() if hasattr(d, "to_dict") else {k: v for k, v in d.__dict__.items()} for d in (decline or [])],
            "volume": volume,
            "confidence_score": confidence_score,
        }

        evidence_report = EvidenceBuilder.build(
            analytics_dict=analytics_dict_for_evidence,
            predictions=predictions,
            recommendations=recommendations,
            evidence_rows=[],
            sql_query=evidence.get("sql", ""),
            tables_used=tables_used,
            columns_used=columns_used,
            validation={"status": "COMPUTED", "rows_returned": volume},
            profile=profile,
            domain=domain,
        )

        # =====================================================================
        # Findings & Summary
        # =====================================================================
        critical_findings, positive_findings, negative_findings, executive_summary = (
            cls._compute_findings(anomalies or [], recommendations, trends or {}, growth or [], decline or [], drivers, domain, total_rows)
        )

        # =====================================================================
        # Copilot Context
        # =====================================================================
        copilot_context = cls._compute_copilot_context(
            domain=domain,
            dataset_name=dataset_name,
            total_rows=total_rows,
            measures=measures,
            dimensions=dimensions,
            temporal=temporal,
            kpis=kpis or [],
            trends=trends or {},
            anomalies=anomalies or [],
            root_causes=root_causes or [],
            drivers=drivers,
            recommendations=recommendations,
            risks=risks,
            opportunities=opportunities,
            growth=growth or [],
            decline=decline or [],
            predictions=predictions,
            correlations=correlations or [],
            profile=profile,
        )

        # =====================================================================
        # Dataset Summary
        # =====================================================================
        dataset_summary = cls._compute_dataset_summary(
            domain=domain,
            dataset_name=dataset_name,
            total_rows=total_rows,
            measures=measures,
            dimensions=dimensions,
            temporal=temporal,
            volume=volume,
            kpi_count=len(kpis or []),
            anomaly_count=len(anomalies or []),
            recommendation_count=len(recommendations),
            prediction_count=len(predictions),
            health_score=health_score,
            confidence_score=confidence_score,
            profile=profile,
        )

        # Readiness flags
        forecast_ready = bool(temporal and measures)
        recommendation_ready = bool(measures)
        report_ready = bool(total_rows > 0)

        result = AnalyticsResult(
            workspace_id=workspace_id or semantic_model.workspace_id or "",
            executive_summary=executive_summary,
            dataset_summary=dataset_summary,
            metrics=measures,
            dimensions=dimensions,
            entities=cls._extract_entities(profile),
            kpis=kpis or [],
            summary_statistics=summary_statistics or {},
            distributions=distributions or {},
            trends=trends or {},
            growth=growth or [],
            decline=decline or [],
            rankings=rankings or {},
            volume=volume,
            utilization=utilization or {},
            performance=performance or {},
            root_causes=root_causes or [],
            drivers=drivers,
            correlations=correlations or [],
            relationships=[],
            dimension_impact=dimension_impact or [],
            segment_comparisons=segment_comparisons or [],
            outliers=outliers or [],
            anomalies=anomalies or [],
            patterns=patterns,
            charts=charts,
            predictions=predictions,
            prediction_strategy=prediction_strategy,
            prediction_feasible=prediction_feasible,
            prediction_limitation=prediction_limitation,
            recommendations=recommendations,
            critical_findings=critical_findings,
            positive_findings=positive_findings,
            negative_findings=negative_findings,
            risks=risks,
            opportunities=opportunities,
            key_drivers=key_drivers,
            copilot_context=copilot_context,
            forecast_ready=forecast_ready,
            forecast_summary=forecast_summary,
            recommendation_ready=recommendation_ready,
            report_ready=report_ready,
            health_score=health_score,
            confidence_score=confidence_score,
            confidence=confidence_score / 100.0 if confidence_score > 1 else confidence_score,
            confidence_factors=confidence_result.factors,
            evidence=evidence,
            evidence_report=evidence_report,
            tables_used=tables_used,
            columns_used=columns_used,
            sql_query=evidence.get("sql", ""),
            domain=domain,
            dataset_type=semantic_model.dataset_type,
            semantic_model=semantic_model,
            generated_at=datetime.now(timezone.utc).isoformat(),
            errors=errors,
        )
        return result

    # =========================================================================
    # WHAT HAPPENED
    # =========================================================================
    @staticmethod
    def _compute_kpis(path: Path, profile: Dict[str, Any], dataset_name: str, total_rows: int, measures: List[str]) -> List[KPIMetric]:
        kpis: List[KPIMetric] = []
        stage = "kpis_computation"
        try:
            summary = SemanticAnalyticsEngine.get_summary_kpis(path, profile)
            confidence_result = ExplainableAIEngine.compute_confidence(profile=profile)
            base_confidence = confidence_result.evidence_score

            dimensions = profile.get("column_categories", {}).get("dimensions", [])
            temporal = profile.get("column_categories", {}).get("temporal", [])
            column_classifications = profile.get("column_classifications", [])
            entities = profile.get("column_categories", {}).get("identifiers", [])

            tx_info = discover_transaction_identifier(
                list(profile.get("columns", {}).keys()),
                column_classifications,
                profile,
            )
            if tx_info:
                tx_col = tx_info["column"]
                distinct_count = tx_info.get("distinct_count", 0)
                if distinct_count > 0:
                    kpis.append(KPIMetric(
                        name="Total Orders",
                        value=distinct_count,
                        formatted_value=f"{distinct_count:,}",
                        metric_type="Order Count",
                        source_column=tx_col,
                        formula=f"COUNT(DISTINCT {tx_col})",
                        rows_analyzed=total_rows,
                        confidence=round(tx_info.get("confidence", 0.8), 2),
                        available=True,
                        evidence=tx_info.get("evidence", ""),
                        business_meaning=f"Number of unique transactions identified by '{tx_col}'.",
                    ))
                elif total_rows > 0:
                    kpis.append(KPIMetric(
                        name="Total Orders",
                        value=total_rows,
                        formatted_value=f"{total_rows:,}",
                        metric_type="Record Count",
                        source_column=tx_col,
                        formula=f"COUNT(DISTINCT {tx_col})",
                        rows_analyzed=total_rows,
                        confidence=round(tx_info.get("confidence", 0.5), 2),
                        available=True,
                        evidence=tx_info.get("evidence", ""),
                        business_meaning=f"Transaction count estimated from '{tx_col}'.",
                    ))

            for ent in entities[:2]:
                ent_col = ent
                col_prof = profile.get("columns", {}).get(ent_col, {})
                distinct_count = col_prof.get("distinct_count", 0)
                kpis.append(KPIMetric(
                    name=f"Unique {ent.replace('_', ' ').title()}s",
                    value=distinct_count,
                    formatted_value=f"{distinct_count:,}",
                    metric_type="Entity Count",
                    source_column=ent_col,
                    formula=f"COUNT(DISTINCT {ent_col})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    available=True,
                    evidence=f"Distinct count from identifier column '{ent_col}'",
                    business_meaning=f"Number of unique {ent.replace('_', ' ').title()}s in the dataset.",
                ))

            for m in measures[:6]:
                stats = {}
                metrics_dict = summary.get("metrics") or profile.get("measure_stats", {})
                if m in metrics_dict:
                    stats = metrics_dict[m]
                else:
                    for k, v in metrics_dict.items():
                        if k.lower() == m.lower():
                            stats = v
                            break

                total_val = stats.get("sum")
                if total_val is None or (total_val == 0 and total_rows > 0):
                    try:
                        from app.database.duckdb_engine import DuckDBEngine
                        path_str = str(path).replace("\\", "/")
                        res = DuckDBEngine.query(f'SELECT SUM("{m}") FROM read_parquet(\'{path_str}\')')
                        if res and len(res) > 0 and list(res[0].values())[0] is not None:
                            total_val = float(list(res[0].values())[0])
                    except Exception:
                        pass

                if total_val is None or abs(float(total_val)) < 1e-9:
                    total_val = 0.0
                else:
                    total_val = float(total_val)

                col_prof = profile.get("columns", {}).get(m, {})
                is_currency = col_prof.get("semantic_type", "").lower() in ("currency", "percentage", "measure")
                is_whole_number = float(total_val) == int(float(total_val)) if total_val is not None else True
                if is_currency or (isinstance(total_val, (int, float)) and not is_whole_number):
                    fmt = f"{total_val:,.2f}"
                else:
                    fmt = f"{total_val:,.0f}"
                kpis.append(KPIMetric(
                    name=m.replace("_", " ").title(),
                    value=total_val,
                    formatted_value=fmt,
                    metric_type=MetricDetector.detect_metric_type(m),
                    source_column=m,
                    formula=f"SUM({m})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    available=True,
                ))

            derived_metrics = discover_derived_metrics(
                measures=measures,
                dimensions=dimensions,
                column_classifications=column_classifications,
                profile=profile,
            )
            for dm in derived_metrics[:4]:
                dm_name = dm.get("metric_name", "Derived Metric")
                dm_formula = dm.get("formula", "")
                dm_sources = dm.get("source_columns", [])
                dm_confidence = dm.get("confidence", 0.7)
                dm_meaning = dm.get("business_meaning", "")
                dm_evidence = dm.get("evidence", "")
                dm_method = dm.get("calculation_method", "")

                computed_value = None
                if len(dm_sources) == 2:
                    src_a, src_b = dm_sources[0], dm_sources[1]
                    stats_a = summary.get("metrics", {}).get(src_a, {})
                    stats_b = summary.get("metrics", {}).get(src_b, {})
                    if dm_method == "row_level_product_aggregated":
                        computed_value = stats_a.get("sum", 0) * stats_b.get("sum", 0) if stats_a.get("sum") is not None and stats_b.get("sum") is not None else None
                    elif dm_method == "aggregate_ratio":
                        sum_a = stats_a.get("sum", 0)
                        distinct_b = profile.get("columns", {}).get(src_b, {}).get("distinct_count", 0)
                        if distinct_b and distinct_b > 0:
                            computed_value = sum_a / distinct_b

                if computed_value is None:
                    try:
                        import duckdb
                        con = duckdb.connect(":memory:")
                        path_str = str(path).replace("\\", "/")
                        escaped_sources = [f'"{s}"' for s in dm_sources]
                        if dm_method == "row_level_product_aggregated" and len(escaped_sources) == 2:
                            sql = f"SELECT SUM({escaped_sources[0]} * {escaped_sources[1]}) as val FROM read_parquet('{path_str}') WHERE {escaped_sources[0]} IS NOT NULL AND {escaped_sources[1]} IS NOT NULL"
                            row = con.execute(sql).fetchone()
                            if row and row[0] is not None:
                                computed_value = float(row[0])
                        elif dm_method == "column_difference" and len(escaped_sources) == 2:
                            sql = f"SELECT SUM({escaped_sources[0]} - {escaped_sources[1]}) as val FROM read_parquet('{path_str}')"
                            row = con.execute(sql).fetchone()
                            if row and row[0] is not None:
                                computed_value = float(row[0])
                        con.close()
                    except Exception:
                        computed_value = None

                if computed_value is not None:
                    col_profiles = profile.get("columns", {})
                    src_sem_types = [col_profiles.get(s, {}).get("semantic_type", "").lower() for s in dm_sources]
                    is_currency = any(st in ("currency", "percentage") for st in src_sem_types)
                    kpis.append(KPIMetric(
                        name=dm_name,
                        value=computed_value,
                        formatted_value=f"{computed_value:,.2f}" if is_currency else f"{computed_value:,.0f}",
                        metric_type=MetricDetector.detect_metric_type(dm_name),
                        source_column=" | ".join(dm_sources),
                        formula=dm_formula,
                        rows_analyzed=total_rows,
                        confidence=round(dm_confidence, 2),
                        available=True,
                        evidence=dm_evidence,
                        business_meaning=dm_meaning,
                    ))

            if not kpis and total_rows > 0:
                kpis.append(KPIMetric(
                    name="Total Verified Rows",
                    value=total_rows,
                    formatted_value=f"{total_rows:,}",
                    metric_type="Record Count",
                    source_column="*",
                    formula="COUNT(*)",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    available=True,
                ))
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
            kpis.append(KPIMetric(
                name="Dataset Summary",
                value="Unavailable",
                formatted_value="Error",
                metric_type="Record Count",
                source_column="*",
                formula="N/A",
                rows_analyzed=total_rows,
                confidence=0.0,
                available=False,
            ))
        return kpis

    @staticmethod
    def _compute_distributions(path: Path, profile: Dict[str, Any], dimensions: List[str], measures: List[str]) -> Dict[str, List[DistributionItem]]:
        distributions: Dict[str, List[DistributionItem]] = {}
        stage = "distributions_computation"
        try:
            for dim in dimensions[:3]:
                items: List[DistributionItem] = []
                rows = SemanticAnalyticsEngine.get_dimension_breakdown(path, dim, measures[0] if measures else None, top_n=10)
                total = sum(r.get("value", 0) for r in rows) if rows else 0
                for r in rows:
                    cat = str(r.get("category") or r.get("label") or r.get("cat") or "Unknown")
                    val = float(r.get("value", 0))
                    pct = (val / total * 100) if total > 0 else 0.0
                    items.append(DistributionItem(category=cat, value=val, percentage=round(pct, 2)))
                distributions[dim] = items
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return distributions

    @staticmethod
    def _normalize_period(row: Dict[str, Any], index: int) -> str:
        """
        Normalizes period identifier from a data row using a canonical precedence order:
        'period', 'date', 'order_date', 'timestamp', 'time', 'label', 'datetime'.
        Returns a clean ISO/string representation if present; otherwise returns 'Period {index}'.
        """
        if isinstance(row, dict):
            for key in ("period", "date", "order_date", "timestamp", "time", "label", "datetime"):
                val = row.get(key)
                if val is not None:
                    val_str = str(val).strip()
                    if val_str and val_str.lower() not in ("none", "null", "nan", "nat", ""):
                        return val_str
        return f"Period {index}"

    @staticmethod
    def _compute_trends(path: Path, profile: Dict[str, Any], temporal: List[str], measures: List[str]) -> Dict[str, List[TrendPoint]]:
        trends: Dict[str, List[TrendPoint]] = {}
        stage = "trends_computation"
        try:
            t_col = temporal[0] if temporal else None
            if not t_col:
                logger.info("[Analytics] No temporal column available for trend computation.")
                return trends
            logger.info("[Analytics] Time column detected: %s", t_col)
            for m in measures[:2]:
                rows = SemanticAnalyticsEngine.get_time_series_trend(path, t_col, m)
                if not rows:
                    logger.info("[Analytics] No trend data for measure: %s", m)
                    continue
                pts = []
                for i, r in enumerate(rows):
                    period_str = UniversalAnalyticsEngine._normalize_period(r, i)
                    val = float(r.get("value", 0) or 0)
                    prev_val = float(rows[i - 1].get("value", 0) or 0) if i > 0 else 0.0
                    change_pct = None
                    if i > 0 and prev_val != 0:
                        change_pct = round((val - prev_val) / prev_val * 100, 2)
                    pts.append(TrendPoint(period=period_str, value=val, change_pct=change_pct))
                trends[m] = pts
                logger.info("[Analytics] Trend rows generated for %s: %d", m, len(pts))
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return trends

    @staticmethod
    def _compute_growth_decline(path: Path, profile: Dict[str, Any], temporal: List[str], measures: List[str]) -> tuple[List[GrowthDecline], List[GrowthDecline]]:
        stage = "growth_decline_computation"
        growth: List[GrowthDecline] = []
        decline: List[GrowthDecline] = []
        try:
            t_col = temporal[0] if temporal else None
            for m in measures[:2]:
                if not t_col:
                    continue
                rows = SemanticAnalyticsEngine.get_time_series_trend(path, t_col, m)
                if not rows:
                    continue
                for i in range(1, len(rows)):
                    prev_val = rows[i - 1].get("value")
                    curr_val = rows[i].get("value")
                    if prev_val is None or curr_val is None:
                        continue
                    prev = float(prev_val)
                    curr = float(curr_val)
                    if prev == 0:
                        continue
                    pct = round((curr - prev) / prev * 100, 2)
                    period_str = UniversalAnalyticsEngine._normalize_period(rows[i], i)
                    item = GrowthDecline(period=period_str, value=curr, previous_value=prev, change_pct=pct, direction="growth" if pct > 0 else "decline")
                    if pct > 5:
                        growth.append(item)
                    elif pct < -5:
                        decline.append(item)
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return growth, decline

    @staticmethod
    def _compute_rankings(path: Path, profile: Dict[str, Any], dimensions: List[str], measures: List[str]) -> Dict[str, List[RankItem]]:
        stage = "rankings_computation"
        rankings: Dict[str, List[RankItem]] = {}
        try:
            for dim in dimensions[:2]:
                items: List[RankItem] = []
                rows = SemanticAnalyticsEngine.get_dimension_breakdown(path, dim, measures[0] if measures else None, top_n=10)
                total = sum(r.get("value", 0) for r in rows) if rows else 0
                for idx, r in enumerate(rows, 1):
                    cat = str(r.get("category") or r.get("label") or r.get("cat") or "Unknown")
                    val = float(r.get("value", 0))
                    pct = (val / total * 100) if total > 0 else 0.0
                    items.append(RankItem(rank=idx, category=cat, value=val, percentage=round(pct, 2)))
                rankings[dim] = items
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return rankings

    @staticmethod
    def _compute_correlations(path: Path, measures: List[str]) -> List[Correlation]:
        stage = "correlations_computation"
        correlations: List[Correlation] = []
        try:
            path_str = str(path).replace("\\", "/")
            pairs = []
            for i in range(len(measures)):
                for j in range(i + 1, len(measures)):
                    pairs.append((measures[i], measures[j]))

            if not pairs:
                return correlations

            union_sql = " UNION ALL ".join(
                f'SELECT CORR("{m1}", "{m2}") as c FROM read_parquet(\'{path_str}\') WHERE "{m1}" IS NOT NULL AND "{m2}" IS NOT NULL'
                for m1, m2 in pairs
            )
            rows = DuckDBEngine.query(union_sql)
            for idx, (m1, m2) in enumerate(pairs):
                if idx < len(rows) and rows[idx].get("c") is not None:
                    corr = float(rows[idx]["c"])
                    strength = "strong positive" if corr > 0.6 else "strong negative" if corr < -0.6 else "moderate" if abs(corr) > 0.3 else "weak"
                    correlations.append(Correlation(column_a=m1, column_b=m2, coefficient=round(corr, 4), strength=strength))
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return correlations

    @staticmethod
    def _compute_utilization(path: Path, profile: Dict[str, Any], measures: List[str], dimensions: List[str]) -> Dict[str, Any]:
        total_rows = profile.get("total_rows", 0)
        return {
            "total_rows": total_rows,
            "measures_utilized": len(measures),
            "dimensions_utilized": len(dimensions),
            "data_density": round(total_rows * max(len(measures), 1) / max(total_rows, 1), 2) if total_rows > 0 else 0,
        }

    @staticmethod
    def _compute_performance(profile: Dict[str, Any], kpis: List[KPIMetric]) -> Dict[str, Any]:
        available = [k for k in kpis if k.available]
        return {
            "metrics_available": len(available),
            "metrics_total": len(kpis),
            "coverage": round(len(available) / max(len(kpis), 1) * 100, 1),
        }

    @staticmethod
    def _compute_summary_statistics(profile: Dict[str, Any], measures: List[str]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for m in measures[:5]:
            ms = profile.get("measure_stats", {}).get(m, {})
            stats[m] = {
                "sum": ms.get("sum", 0),
                "avg": ms.get("avg", 0),
                "min": ms.get("min", 0),
                "max": ms.get("max", 0),
            }
        return stats

    # =========================================================================
    # WHY DID IT HAPPEN
    # =========================================================================
    @staticmethod
    def _compute_root_causes(path: Path, profile: Dict[str, Any], dimensions: List[str], measures: List[str]) -> List[RootCause]:
        stage = "root_causes_computation"
        root_causes: List[RootCause] = []
        try:
            for dim in dimensions[:2]:
                m = measures[0] if measures else None
                if not m:
                    continue
                result = VarianceDecompositionEngine.analyze_drivers(path, dim, m, top_n=5)
                drivers = []
                cumulative = 0.0
                for d in result.get("drivers", []):
                    cumulative += d.get("contribution_percentage", 0.0)
                    drivers.append(DriverContribution(
                        category=d.get("category", ""),
                        amount=float(d.get("amount", 0)),
                        contribution_percentage=float(d.get("contribution_percentage", 0)),
                        cumulative_percentage=round(cumulative, 2),
                    ))
                top_driver = result.get("top_driver")
                root_causes.append(RootCause(
                    dimension=dim,
                    measure=m,
                    grand_total=float(result.get("grand_total", 0)),
                    top_driver=top_driver,
                    concentration_risk=result.get("has_concentration_risk", False),
                    drivers=drivers,
                ))
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return root_causes

    @staticmethod
    def _compute_drivers(root_causes: List[RootCause]) -> List[Dict[str, Any]]:
        drivers: List[Dict[str, Any]] = []
        for rc in root_causes:
            if rc.top_driver:
                drivers.append({
                    "dimension": rc.dimension,
                    "measure": rc.measure,
                    "top_driver": rc.top_driver,
                    "concentration_risk": rc.concentration_risk,
                    "driver_count": len(rc.drivers),
                })
        return drivers

    @staticmethod
    def _compute_dimension_impact(path: Path, profile: Dict[str, Any], dimensions: List[str], measures: List[str]) -> List[Dict[str, Any]]:
        stage = "dimension_impact_computation"
        impact: List[Dict[str, Any]] = []
        try:
            for dim in dimensions[:2]:
                m = measures[0] if measures else None
                if m:
                    rows = SemanticAnalyticsEngine.get_dimension_breakdown(path, dim, m, top_n=5)
                    impact.append({"dimension": dim, "measure": m, "breakdown": rows})
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return impact

    @staticmethod
    def _compute_segment_comparisons(path: Path, profile: Dict[str, Any], dimensions: List[str], measures: List[str]) -> List[SegmentComparison]:
        stage = "segment_comparisons_computation"
        comparisons: List[SegmentComparison] = []
        try:
            dim = dimensions[0] if dimensions else None
            m = measures[0] if measures else None
            if dim and m:
                rows = SemanticAnalyticsEngine.get_dimension_breakdown(path, dim, m, top_n=10)
                if len(rows) >= 2:
                    for i in range(0, len(rows) - 1, 2):
                        a, b = rows[i], rows[i + 1]
                        val_a = float(a.get("value", 0))
                        val_b = float(b.get("value", 0))
                        cat_a = str(a.get("category") or a.get("label") or a.get("cat") or "Segment A")
                        cat_b = str(b.get("category") or b.get("label") or b.get("cat") or "Segment B")
                        diff = 0.0
                        if val_b != 0:
                            diff = round((val_a - val_b) / val_b * 100, 2)
                        comparisons.append(SegmentComparison(
                            segment_a=cat_a,
                            segment_b=cat_b,
                            metric=m,
                            value_a=val_a,
                            value_b=val_b,
                            difference_pct=diff,
                            winner="a" if val_a >= val_b else "b",
                        ))
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
        return comparisons

    @staticmethod
    def _compute_anomalies(path: Path, profile: Dict[str, Any], temporal: List[str], measures: List[str], errors: List[str]) -> Dict[str, Any]:
        result = {"outliers": [], "anomalies": []}
        try:
            t_col = temporal[0] if temporal else None
            m = measures[0] if measures else None
            if t_col and m:
                anomalies = StatisticalAnomalyEngine.detect_anomalies(path, t_col, m)
                for a in anomalies:
                    result["anomalies"].append(BusinessAnomaly(
                        period=str(a.get("period", "")),
                        title=str(a.get("title", "")),
                        category=str(a.get("category", "")),
                        severity=str(a.get("severity", "")),
                        type=str(a.get("type", "")),
                        actual_value=float(a.get("actual_value", 0)),
                        expected_value=float(a.get("expected_value", 0)),
                        z_score=float(a.get("z_score", 0)),
                        pct_change=float(a.get("pct_change", 0)),
                        explanation=str(a.get("explanation", "")),
                        business_impact=str(a.get("business_impact", "")),
                        possible_causes=a.get("possible_causes", []),
                        recommendation=str(a.get("recommendation", "")),
                        confidence_score=float(a.get("confidence_score", 0)),
                    ))
                    result["outliers"].append(Outlier(
                        period=str(a.get("period", "")),
                        value=float(a.get("actual_value", 0)),
                        expected_value=float(a.get("expected_value", 0)),
                        z_score=float(a.get("z_score", 0)),
                        direction=str(a.get("type", "")),
                        severity=str(a.get("severity", "")),
                        pct_change=float(a.get("pct_change", 0)),
                    ))
        except Exception as e:
            errors.append(f"Anomaly detection failed: {str(e)}")
        return result

    @staticmethod
    def _compute_patterns(trends: Dict[str, List[TrendPoint]], anomalies: List[BusinessAnomaly], growth: List[GrowthDecline], decline: List[GrowthDecline]) -> List[str]:
        patterns: List[str] = []
        if trends:
            for m, pts in trends.items():
                if len(pts) >= 3:
                    up = sum(1 for p in pts if p.change_pct and p.change_pct > 0)
                    down = sum(1 for p in pts if p.change_pct and p.change_pct < 0)
                    if up > down:
                        patterns.append(f"Overall upward trend detected in {m} ({up} up periods vs {down} down).")
                    elif down > up:
                        patterns.append(f"Overall downward trend detected in {m} ({down} down periods vs {up} up).")
        if anomalies:
            dips = sum(1 for a in anomalies if a.type == "DIP")
            spikes = sum(1 for a in anomalies if a.type == "SPIKE")
            if dips:
                patterns.append(f"Detected {dips} decline period(s) requiring attention for primary metric.")
            if spikes:
                patterns.append(f"Detected {spikes} surge period(s) with potential strain on primary metric.")
        if growth:
            patterns.append(f"{len(growth)} significant growth periods identified with strong upward momentum.")
        if decline:
            patterns.append(f"{len(decline)} significant decline periods identified with negative momentum.")
        return patterns

    # =========================================================================
    # WHAT SHOULD WE DO
    # =========================================================================
    @staticmethod
    def _compute_recommendations(
        path: Path, profile: Dict[str, Any], dimensions: List[str], measures: List[str], root_causes: List[RootCause], anomalies: List[BusinessAnomaly], errors: List[str]
    ) -> List[Recommendation]:
        stage = "recommendations_computation"
        recommendations: List[Recommendation] = []
        confidence_result = ExplainableAIEngine.compute_confidence(profile=profile, anomalies=anomalies)
        rec_confidence = confidence_result.recommendation_score
        try:
            recs = RecommendationEngine.generate_recommendations(path, profile)
            for r in recs.get("recommendations", []):
                recommendations.append(Recommendation(
                    id=str(r.get("id", "REC-UNKNOWN")),
                    title=str(r.get("title", "")),
                    category="Strategy",
                    priority="HIGH" if recs.get("has_valid_strategy", False) else "LOW",
                    reason=str(r.get("business_rationale", "")),
                    action=str(r.get("title", "")),
                    expected_roi=str(r.get("expected_roi", "Insufficient evidence")),
                    financial_impact=str(r.get("financial_impact", "Insufficient evidence")),
                    investment_required=str(r.get("investment_required", "Insufficient evidence")),
                    timeline=str(r.get("timeline", "Insufficient evidence")),
                    confidence=round(rec_confidence, 2),
                    risk_level="LOW",
                    owner="Data Team",
                    implementation_difficulty="Medium",
                    evidence=str(r.get("evidence_panel", {})),
                ))
            if not recs.get("has_valid_strategy", False):
                recommendations.append(Recommendation(
                    id="REC-999",
                    title="Insufficient Numeric Metrics",
                    category="Data Strategy",
                    priority="HIGH",
                    reason=recs.get("disclaimer", "") or "Dataset lacks sufficient numeric measures for strategic recommendations.",
                    action="Add numeric measure columns to enable evidence-based strategic recommendations.",
                    expected_roi="Insufficient evidence",
                    financial_impact="Insufficient evidence",
                    investment_required="Insufficient evidence",
                    timeline="Insufficient evidence",
                    confidence=round(rec_confidence, 2),
                    risk_level="LOW",
                    owner="Data Team",
                    implementation_difficulty="Low",
                ))
        except Exception as e:
            logger.error(f"{stage} (generic recommendations) failed: {str(e)}")
            errors.append(f"{stage} (generic): {str(e)}")

        # Root cause based recommendations
        for rc in root_causes:
            if rc.top_driver and rc.concentration_risk:
                recommendations.append(Recommendation(
                    id="REC-CONCENTRATION",
                    title=f"Diversify Metrics Away from '{rc.top_driver.get('category', 'Top Category')}'",
                    category="Portfolio Risk",
                    priority="CRITICAL",
                    reason=f"Concentration risk: '{rc.top_driver.get('category', '')}' contributes {rc.top_driver.get('contribution_percentage', 0)}% of total {rc.measure}.",
                    action=f"Reallocate budget to secondary growth segments to reduce dependency on '{rc.top_driver.get('category', '')}'.",
                    expected_roi="Insufficient evidence",
                    financial_impact="Insufficient evidence",
                    investment_required="Insufficient evidence",
                    timeline="Insufficient evidence",
                    confidence=round(confidence_result.overall_score * 100.0, 1),
                    risk_level="LOW",
                    owner="CEO & CFO",
                    implementation_difficulty="High",
                ))

        # Anomaly-based recommendations
        for a in anomalies:
            if a.severity in ("CRITICAL", "HIGH") and a.recommendation:
                recommendations.append(Recommendation(
                    id=f"REC-ANOMALY-{a.period}",
                    title=f"Address {a.title}",
                    category="Operations",
                    priority="CRITICAL" if a.severity == "CRITICAL" else "HIGH",
                    reason=a.explanation,
                    action=a.recommendation,
                    expected_roi="Insufficient evidence",
                    financial_impact=a.business_impact,
                    investment_required="Insufficient evidence",
                    timeline="Insufficient evidence",
                    confidence=round(a.confidence_score / 100.0, 2) if a.confidence_score > 1 else round(a.confidence_score, 2),
                    risk_level="MEDIUM",
                    owner="Operations",
                    implementation_difficulty="Medium",
                ))

        return recommendations

    @staticmethod
    def _compute_risks(root_causes: List[RootCause], anomalies: List[BusinessAnomaly], drivers: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[RiskItem]:
        risks: List[RiskItem] = []
        for rc in root_causes:
            if rc.concentration_risk:
                risks.append(RiskItem(
                    id="RISK-CONCENTRATION",
                    title=f"Concentration Risk in {rc.dimension}",
                    category="Business Concentration",
                    severity="HIGH",
                    description=f"Top driver in {rc.dimension} contributes {rc.top_driver.get('contribution_percentage', 0) if rc.top_driver else 0}% of total {rc.measure}.",
                    impact="Single-point-of-failure vulnerability to market shifts.",
                    causes=[f"Over-reliance on '{rc.top_driver.get('category', '')}" if rc.top_driver else ""],
                    mitigation=f"Diversify {rc.measure} distribution across secondary {rc.dimension} categories.",
                ))
        for a in anomalies:
            if a.severity == "CRITICAL":
                risks.append(RiskItem(
                    id=f"RISK-ANOMALY-{a.period}",
                    title=a.title,
                    category="Operational Risk",
                    severity="CRITICAL",
                    description=a.explanation,
                    impact=a.business_impact,
                    causes=a.possible_causes,
                    mitigation=a.recommendation,
                ))
        if not risks:
            return risks

        return risks

    @staticmethod
    def _compute_opportunities(domain: str, drivers: List[Dict[str, Any]], anomalies: List[BusinessAnomaly], growth: List[GrowthDecline], total_rows: int) -> List[OpportunityItem]:
        opportunities: List[OpportunityItem] = []
        for d in drivers:
            td = d.get("top_driver")
            if td and not d.get("concentration_risk"):
                opportunities.append(OpportunityItem(
                    id="OPP-GROWTH",
                    title=f"Expand '{td.get('category', '')}' Presence",
                    category="Growth",
                    priority="HIGH",
                    description=f"Top segment '{td.get('category', '')}' leads contribution at {td.get('contribution_percentage', 0)}%.",
                    impact=f"Potential to expand {d.get('dimension', 'segment')} distribution in core category for immediate performance gain.",
                    action=f"Increase investment in '{td.get('category', '')}' to capitalize on strong performance.",
                    timeline="90 Days",
                ))
        spikes = [a for a in anomalies if a.type == "SPIKE"]
        if spikes:
            opportunities.append(OpportunityItem(
                id="OPP-SPIKE",
                title="Capitalize on Performance Surges",
                category="Performance Opportunity",
                priority="HIGH",
                description=f"Detected {len(spikes)} statistical surge period(s).",
                impact="Expand capacity and capitalize on peak demand windows.",
                action="Launch targeted campaigns and ensure resource buffers.",
                timeline="14 Days",
            ))
        if growth:
            opportunities.append(OpportunityItem(
                id="OPP-TREND",
                title="Sustain Upward Momentum",
                category="Growth",
                priority="MEDIUM",
                description=f"{len(growth)} significant growth periods identified.",
                impact="Reinforce positive momentum drivers.",
                action="Analyze growth catalysts and replicate success factors.",
                timeline="60 Days",
            ))
        return opportunities

    @staticmethod
    def _compute_key_drivers(drivers: List[Dict[str, Any]], root_causes: List[RootCause]) -> List[Dict[str, Any]]:
        key_drivers: List[Dict[str, Any]] = []
        for rc in root_causes:
            if rc.top_driver:
                key_drivers.append({
                    "dimension": rc.dimension,
                    "measure": rc.measure,
                    "driver": rc.top_driver,
                    "concentration_risk": rc.concentration_risk,
                    "driver_count": len(rc.drivers),
                })
        return key_drivers

    # =========================================================================
    # Findings & Summary
    # =========================================================================
    @staticmethod
    def _compute_findings(
        anomalies: List[BusinessAnomaly], recommendations: List[Recommendation], trends: Dict[str, List[TrendPoint]], growth: List[GrowthDecline], decline: List[GrowthDecline], drivers: List[Dict[str, Any]], domain: str, total_rows: int
    ) -> tuple[List[str], List[str], List[str], str]:
        critical: List[str] = []
        positive: List[str] = []
        negative: List[str] = []
        for a in anomalies:
            if a.severity == "CRITICAL":
                critical.append(f"CRITICAL: {a.explanation}")
            elif a.severity == "HIGH":
                negative.append(f"HIGH: {a.explanation}")
        for r in recommendations:
            if r.priority == "CRITICAL" and r.id != "REC-999":
                critical.append(f"CRITICAL RECOMMENDATION: {r.reason}")
        if growth:
            positive.append(f"Strong growth detected: {len(growth)} periods with significant positive change.")

        findings_count = len(critical) + len(negative) + len(positive)
        summary_parts = [
            f"{domain} intelligence analysis of {total_rows:,} records."
        ]
        if anomalies:
            summary_parts.append(f"Identified {len(anomalies)} anomalies.")
        if recommendations:
            summary_parts.append(f"{len(recommendations)} recommendations generated.")
        if drivers:
            summary_parts.append(f"{len(drivers)} key business drivers identified.")
        if not summary_parts:
            summary_parts.append("Analysis complete. No significant findings.")

        summary = " ".join(summary_parts)
        return critical, positive, negative, summary

    # =========================================================================
    # Forecast Summary
    # =========================================================================
    @staticmethod
    def _compute_forecast_summary(
        predictions: List[Any],
        temporal: List[str],
        measures: List[str],
        domain: str,
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "outlook": "Stable",
            "expected_change_pct": 0.0,
            "main_driver": "",
            "risk": "Low",
            "management_action": "",
            "primary_metric": measures[0] if measures else "",
            "has_temporal_data": bool(temporal),
            "forecast_models_count": len(predictions),
            "feasible_forecasts_count": sum(1 for p in predictions if getattr(p, "feasible", False)),
        }

        if not predictions:
            summary["management_action"] = "Upload a dataset with temporal and numeric columns to enable forecasting."
            return summary

        feasible_preds = [p for p in predictions if getattr(p, "feasible", False)]
        if not feasible_preds:
            summary["outlook"] = "Unknown"
            summary["risk"] = "Medium"
            summary["management_action"] = predictions[0].limitation or "Insufficient data for reliable forecasting."
            return summary

        primary = feasible_preds[0]
        pct_change = getattr(primary, "expected_change_pct", 0.0) or 0.0
        metric = getattr(primary, "metric", "") or measures[0] if measures else ""
        metric_label = metric.replace("_", " ").title() if metric else "Primary Metric"
        drivers = getattr(primary, "drivers", []) or []
        main_driver = drivers[0].get("name", "") if drivers else ""

        if pct_change > 5:
            summary["outlook"] = "Growing"
        elif pct_change < -5:
            summary["outlook"] = "Declining"
        else:
            summary["outlook"] = "Stable"

        summary["expected_change_pct"] = round(pct_change, 2)
        summary["main_driver"] = main_driver
        summary["risk"] = getattr(primary, "risk_level", "Low") or "Low"
        summary["primary_metric"] = metric_label
        summary["management_action"] = getattr(primary, "recommended_action", "") or "Continue monitoring key metrics."
        summary["model_used"] = getattr(primary, "model_used", "") or getattr(primary, "model_name", "")
        summary["confidence"] = round(getattr(primary, "confidence", 0.0), 2)

        if len(feasible_preds) > 1:
            pct_changes = [getattr(p, "expected_change_pct", 0.0) or 0.0 for p in feasible_preds]
            avg_pct = sum(pct_changes) / len(pct_changes)
            if avg_pct > 5:
                summary["outlook"] = "Growing"
            elif avg_pct < -5:
                summary["outlook"] = "Declining"
            else:
                summary["outlook"] = "Stable"
            summary["expected_change_pct"] = round(avg_pct, 2)

        return summary

    # =========================================================================
    # Health & Confidence
    # =========================================================================
    @staticmethod
    def _compute_confidence_score(kpis: List[KPIMetric], profile: Dict[str, Any], measure_count: int, dimension_count: int, total_rows: int, errors: List[str], temporal_count: int = 0) -> float:
        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=profile,
            kpis=kpis,
            errors=errors,
        )
        return round(confidence_result.overall_score * 100.0, 1)

    @staticmethod
    def _compute_evidence(path: Path, profile: Dict[str, Any], measures: List[str], dimensions: List[str], errors: List[str]) -> Dict[str, Any]:
        tables_used = [path.name] if path else []
        columns_used = list(measures[:10]) + list(dimensions[:10])
        return {
            "dataset_path": str(path),
            "total_rows": profile.get("total_rows", 0),
            "measures_analyzed": measures[:10],
            "dimensions_analyzed": dimensions[:10],
            "errors": errors,
            "traceability": "Verified data analysis executed directly against dataset records.",
            "tables_used": tables_used,
            "columns_used": columns_used,
            "sql": "",
            "models_used": [
                "SemanticAnalyticsEngine",
                "StatisticalAnomalyEngine",
                "VarianceDecompositionEngine",
                "AutoInsights",
                "RecommendationEngine",
                "BusinessHealthEngine",
                "UniversalPredictionEngine",
                "ChartEngine",
            ],
        }

    # =========================================================================
    # Canonical Object Helpers
    # =========================================================================
    @staticmethod
    def _normalize_charts(raw_charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for c in raw_charts:
            chart_type = c.get("type", "bar")
            title = c.get("title", "")
            source_column = c.get("source_column", "")
            dimension_column = c.get("dimension_column", "")
            data = c.get("data", [])
            labels = [d.get("category") or d.get("period", "") for d in data]

            x_axis = c.get("x_axis", dimension_column or source_column)
            y_axis = c.get("y_axis", source_column)

            canonical_data = []
            for d in data:
                label = d.get("category") or d.get("period") or d.get("label") or ""
                value = d.get("value")
                if label and value is not None:
                    try:
                        clean_value = float(value)
                        if math.isnan(clean_value) or math.isinf(clean_value):
                            continue
                        canonical_data.append({
                            "x_field": str(label),
                            "y_field": clean_value,
                            "label": str(label),
                            "value": clean_value,
                        })
                    except (TypeError, ValueError):
                        continue

            if not canonical_data:
                continue

            normalized.append({
                "chart_type": chart_type,
                "type": chart_type,
                "title": title,
                "x_axis": x_axis,
                "y_axis": y_axis,
                "x_field": x_axis,
                "y_field": y_axis,
                "series": canonical_data,
                "data": canonical_data,
                "labels": [d["label"] for d in canonical_data],
                "values": [d["value"] for d in canonical_data],
                "confidence": c.get("confidence", 0.0),
                "source_column": source_column,
                "dimension_column": dimension_column,
                "business_interpretation": c.get("business_interpretation", ""),
                "evidence": c.get("evidence", ""),
                "available": True,
                "id": c.get("id", ""),
            })
        return normalized

    @staticmethod
    def _compute_copilot_context(
        domain: str,
        dataset_name: str,
        total_rows: int,
        measures: List[str],
        dimensions: List[str],
        temporal: List[str],
        kpis: List[KPIMetric],
        trends: Dict[str, List[TrendPoint]],
        anomalies: List[BusinessAnomaly],
        root_causes: List[RootCause],
        drivers: List[Dict[str, Any]],
        recommendations: List[Recommendation],
        risks: List[RiskItem],
        opportunities: List[OpportunityItem],
        growth: List[GrowthDecline],
        decline: List[GrowthDecline],
        predictions: List[Prediction],
        correlations: List[Correlation],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_kpis = [{"name": k.name, "value": k.formatted_value, "column": k.source_column} for k in kpis[:5] if k.available]
        top_relationships = []
        for corr in correlations[:5]:
            top_relationships.append({
                "columns": f"{corr.column_a} vs {corr.column_b}",
                "coefficient": corr.coefficient,
                "strength": corr.strength,
            })
        top_opportunities = [{"title": o.title, "priority": o.priority} for o in opportunities[:5]]
        top_risks = [{"title": r.title, "severity": r.severity} for r in risks[:5]]
        key_cols = measures[:5] + dimensions[:5]

        context = {
            "dataset_summary": f"{domain} dataset '{dataset_name}' with {total_rows:,} records.",
            "business_summary": f"Analysis of {total_rows:,} records across {len(measures)} metrics and {len(dimensions)} dimensions in the {domain} domain.",
            "detected_kpis": top_kpis,
            "important_metrics": measures[:10],
            "key_relationships": top_relationships,
            "business_risks": top_risks,
            "top_opportunities": top_opportunities,
            "most_important_columns": key_cols,
            "most_important_categories": dimensions[:5],
            "temporal_columns": temporal[:3],
            "anomaly_count": len(anomalies),
            "recommendation_count": len(recommendations),
            "prediction_count": len(predictions),
            "growth_periods": len(growth),
            "decline_periods": len(decline),
            "driver_count": len(drivers),
            "root_cause_count": len(root_causes),
        }
        return context

    @staticmethod
    def _compute_dataset_summary(
        domain: str,
        dataset_name: str,
        total_rows: int,
        measures: List[str],
        dimensions: List[str],
        temporal: List[str],
        volume: int,
        kpi_count: int,
        anomaly_count: int,
        recommendation_count: int,
        prediction_count: int,
        health_score: HealthScore,
        confidence_score: float,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        columns = profile.get("columns", {})
        null_stats = {}
        completeness_scores = {}
        for col_name, col_info in columns.items():
            null_pct = col_info.get("null_percentage", 0.0)
            null_stats[col_name] = {
                "null_percentage": null_pct,
                "distinct_count": col_info.get("distinct_count", 0),
                "data_type": col_info.get("data_type", "Unknown"),
            }
            completeness_scores[col_name] = round(100.0 - null_pct, 2)

        return {
            "domain": domain,
            "dataset_name": dataset_name,
            "total_rows": total_rows,
            "total_columns": profile.get("total_columns", 0),
            "measures": measures,
            "dimensions": dimensions,
            "temporal_columns": temporal,
            "volume": volume,
            "kpi_count": kpi_count,
            "anomaly_count": anomaly_count,
            "recommendation_count": recommendation_count,
            "prediction_count": prediction_count,
            "health_score": health_score.overall_score if health_score else 0.0,
            "health_status": health_score.status if health_score else "No Data",
            "confidence_score": confidence_score,
            "completeness_scores": completeness_scores,
            "null_statistics": null_stats,
            "data_quality": profile.get("data_quality", {}),
        }

    @staticmethod
    def _extract_entities(profile: Dict[str, Any]) -> List[str]:
        entities: List[str] = []
        columns = profile.get("columns", {})
        for col_name, col_info in columns.items():
            category = col_info.get("category", "")
            if category == "identifier":
                entities.append(col_name)
        return entities

    # =========================================================================
    # Resolution & Empty Result
    # =========================================================================
    @staticmethod
    def _resolve_parquet_path(semantic_model: SemanticModel, dataset_id: Optional[str] = None) -> Optional[Path]:
        try:
            tables = semantic_model.tables
            if tables:
                for t in tables:
                    fp = t.file_path
                    if fp and Path(fp).exists():
                        return Path(fp)
        except Exception:
            pass
        try:
            from app.services.dynamic_dashboard_service import _find_best_parquet
            from app.database.connection import SessionLocal
            db = SessionLocal()
            path = _find_best_parquet(db)
            db.close()
            return path
        except Exception:
            pass
        return None

    @staticmethod
    def _empty_result(semantic_model: SemanticModel, workspace_id: str, reason: str) -> AnalyticsResult:
        return AnalyticsResult(
            workspace_id=workspace_id,
            executive_summary=f"No analysis generated. {reason}",
            domain=semantic_model.domain or "Generic Business",
            dataset_type=semantic_model.dataset_type or "Unknown",
            semantic_model=semantic_model,
            generated_at=datetime.now(UTC).isoformat(),
            errors=[reason],
            health_score=HealthScore(overall_score=0.0, grade="N/A", status="No Data"),
        )
