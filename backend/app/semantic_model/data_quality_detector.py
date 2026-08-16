from typing import Any, Dict, List, Optional
from pathlib import Path

from app.semantic_model.core import DataQualityReport, MissingValueReport
from app.ingestion.semantic_profiler import SemanticDataProfiler


class DataQualityDetector:
    """
    Comprehensive data quality assessment that produces
    a structured DataQualityReport and MissingValueReport
    for every column in a dataset.
    """

    HIGH_NULL_THRESHOLD = 0.5
    MODERATE_NULL_THRESHOLD = 0.2
    HIGH_CARDINALITY_THRESHOLD = 0.9
    REDUNDANT_UNIQUENESS_THRESHOLD = 0.01

    @classmethod
    def assess(
        cls,
        parquet_path: Path,
        profile: Optional[Dict[str, Any]] = None,
        semantic_model: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if profile is None:
            profile = SemanticDataProfiler.profile(parquet_path)

        table_name = semantic_model.get("table_name", parquet_path.stem) if semantic_model else parquet_path.stem
        total_rows = profile.get("total_rows", 0)
        total_columns = profile.get("total_columns", 0)
        columns_profile = profile.get("columns", {})

        missing_reports = cls._detect_missing_values(
            columns_profile, total_rows, table_name
        )

        high_null_cols = [
            r.column for r in missing_reports
            if r.null_percentage > cls.HIGH_NULL_THRESHOLD * 100
        ]
        moderate_null_cols = [
            r.column for r in missing_reports
            if cls.MODERATE_NULL_THRESHOLD * 100 < r.null_percentage <= cls.HIGH_NULL_THRESHOLD * 100
        ]

        negative_values = cls._detect_negative_values(
            columns_profile, parquet_path, table_name, columns_profile
        )

        empty_string_cols = cls._detect_empty_strings(
            columns_profile, parquet_path, table_name
        )

        high_cardinality_cols = cls._detect_high_cardinality(
            columns_profile, total_rows
        )

        redundant_cols = cls._detect_redundant_columns(
            columns_profile, total_rows
        )

        duplicate_rows = cls._estimate_duplicate_rows(
            columns_profile, total_rows
        )

        outlier_count = cls._estimate_outliers(
            columns_profile, total_rows
        )

        overall_score = cls._compute_overall_score(
            total_rows=total_rows,
            total_columns=total_columns,
            high_null_cols=high_null_cols,
            moderate_null_cols=moderate_null_cols,
            negative_values=negative_values,
            empty_string_cols=empty_string_cols,
            high_cardinality_cols=high_cardinality_cols,
            redundant_cols=redundant_cols,
            duplicate_rows=duplicate_rows,
            outlier_count=outlier_count,
        )

        issues = cls._generate_issues(
            high_null_cols=high_null_cols,
            moderate_null_cols=moderate_null_cols,
            negative_values=negative_values,
            empty_string_cols=empty_string_cols,
            high_cardinality_cols=high_cardinality_cols,
            redundant_cols=redundant_cols,
            duplicate_rows=duplicate_rows,
            outlier_count=outlier_count,
        )

        quality_report = DataQualityReport(
            overall_score=round(overall_score, 2),
            total_rows=total_rows,
            total_columns=total_columns,
            columns_with_high_null_rate=high_null_cols,
            columns_with_moderate_null_rate=moderate_null_cols,
            high_cardinality_columns=high_cardinality_cols,
            potentially_redundant_columns=redundant_cols,
            negative_numeric_values=negative_values,
            empty_string_columns=empty_string_cols,
            duplicate_rows=duplicate_rows,
            outliers_detected=outlier_count,
            issues=issues,
        )

        return {
            "data_quality_report": quality_report,
            "missing_value_reports": [r.__dict__ for r in missing_reports],
            "table_name": table_name,
        }

    @classmethod
    def _detect_missing_values(
        cls,
        columns_profile: Dict[str, Any],
        total_rows: int,
        table_name: str,
    ) -> List[MissingValueReport]:
        reports = []
        for col_name, col_profile in columns_profile.items():
            null_count = col_profile.get("null_count", 0)
            null_pct = col_profile.get("null_percentage", 0.0)

            if null_count > 0:
                missing_type = "null"
                if null_pct > cls.HIGH_NULL_THRESHOLD * 100:
                    missing_type = "critical_null"
                elif null_pct > cls.MODERATE_NULL_THRESHOLD * 100:
                    missing_type = "moderate_null"

                impact = "Critical" if missing_type == "critical_null" else (
                    "Moderate" if missing_type == "moderate_null" else "Low"
                )

                reports.append(MissingValueReport(
                    column=col_name,
                    table=table_name,
                    null_count=null_count,
                    null_percentage=null_pct,
                    missing_value_type=missing_type,
                    impact=impact,
                ))
        return reports

    @classmethod
    def _detect_negative_values(
        cls,
        columns_profile: Dict[str, Any],
        parquet_path: Path,
        table_name: str,
        all_columns_profile: Dict[str, Any],
    ) -> Dict[str, int]:
        negative_summary = {}
        path_str = str(parquet_path).replace("\\", "/")

        for col_name, col_profile in columns_profile.items():
            category = col_profile.get("category", "")
            if category != "measure":
                continue
            stats = col_profile.get("stats", {})
            min_val = stats.get("min")
            if min_val is not None and isinstance(min_val, (int, float)) and min_val < 0:
                try:
                    import duckdb
                    con = duckdb.connect(":memory:")
                    col_esc = f'"{col_name}"'
                    sql = f"SELECT COUNT(*) as neg_cnt FROM read_parquet('{path_str}') WHERE {col_esc} < 0"
                    result = con.execute(sql).fetchone()
                    neg_cnt = result[0] if result else 0
                    con.close()
                    if neg_cnt > 0:
                        negative_summary[col_name] = neg_cnt
                except Exception:
                    pass
        return negative_summary

    @classmethod
    def _detect_empty_strings(
        cls,
        columns_profile: Dict[str, Any],
        parquet_path: Path,
        table_name: str,
    ) -> List[str]:
        empty_cols = []
        path_str = str(parquet_path).replace("\\", "/")

        for col_name, col_profile in columns_profile.items():
            col_type = col_profile.get("data_type", "").upper()
            category = col_profile.get("category", "")
            if "VARCHAR" not in col_type and "TEXT" not in col_type:
                continue
            if category not in ("dimension", "identifier"):
                continue

            try:
                import duckdb
                con = duckdb.connect(":memory:")
                col_esc = f'"{col_name}"'
                sql = f"SELECT COUNT(*) as empty_cnt FROM read_parquet('{path_str}') WHERE TRIM({col_esc}) = ''"
                result = con.execute(sql).fetchone()
                empty_cnt = result[0] if result else 0
                con.close()
                if empty_cnt > 0:
                    empty_cols.append(col_name)
            except Exception:
                pass
        return empty_cols

    @classmethod
    def _detect_high_cardinality(
        cls,
        columns_profile: Dict[str, Any],
        total_rows: int,
    ) -> List[str]:
        high_card_cols = []
        for col_name, col_profile in columns_profile.items():
            distinct_count = col_profile.get("distinct_count", 0)
            ratio = distinct_count / max(total_rows, 1)
            if ratio > cls.HIGH_CARDINALITY_THRESHOLD:
                high_card_cols.append(col_name)
        return high_card_cols

    @classmethod
    def _detect_redundant_columns(
        cls,
        columns_profile: Dict[str, Any],
        total_rows: int,
    ) -> List[str]:
        redundant_cols = []
        for col_name, col_profile in columns_profile.items():
            distinct_count = col_profile.get("distinct_count", 0)
            ratio = distinct_count / max(total_rows, 1)
            if ratio < cls.REDUNDANT_UNIQUENESS_THRESHOLD:
                category = col_profile.get("category", "")
                if category in ("measure",):
                    redundant_cols.append(col_name)
        return redundant_cols

    @classmethod
    def _estimate_duplicate_rows(
        cls,
        columns_profile: Dict[str, Any],
        total_rows: int,
    ) -> int:
        if total_rows < 10:
            return 0
        identifier_cols = [
            c for c, p in columns_profile.items()
            if p.get("category") == "identifier"
        ]
        if not identifier_cols:
            return max(0, int(total_rows * 0.02))
        return 0

    @classmethod
    def _estimate_outliers(
        cls,
        columns_profile: Dict[str, Any],
        total_rows: int,
    ) -> int:
        outlier_count = 0
        for col_name, col_profile in columns_profile.items():
            category = col_profile.get("category", "")
            if category != "measure":
                continue
            stats = col_profile.get("stats", {})
            q25 = stats.get("q25")
            q75 = stats.get("q75")
            mean = stats.get("mean")
            stddev = stats.get("stddev")
            if q25 is not None and q75 is not None and stddev is not None and stddev > 0:
                iqr = q75 - q25
                lower = q25 - 1.5 * iqr
                upper = q75 + 1.5 * iqr
                if mean is not None:
                    if mean < lower or mean > upper:
                        outlier_count += 1
        return outlier_count

    @classmethod
    def _compute_overall_score(
        cls,
        total_rows: int,
        total_columns: int,
        high_null_cols: List[str],
        moderate_null_cols: List[str],
        negative_values: Dict[str, int],
        empty_string_cols: List[str],
        high_cardinality_cols: List[str],
        redundant_cols: List[str],
        duplicate_rows: int,
        outlier_count: int,
    ) -> float:
        score = 100.0

        score -= len(high_null_cols) * 5
        score -= len(moderate_null_cols) * 2
        score -= len(negative_values) * 2
        score -= len(empty_string_cols) * 1
        score -= len(high_cardinality_cols) * 1
        score -= len(redundant_cols) * 1
        score -= min(duplicate_rows, 10) * 2
        score -= min(outlier_count, 10) * 1

        return max(0.0, min(100.0, score))

    @classmethod
    def _generate_issues(
        cls,
        high_null_cols: List[str],
        moderate_null_cols: List[str],
        negative_values: Dict[str, int],
        empty_string_cols: List[str],
        high_cardinality_cols: List[str],
        redundant_cols: List[str],
        duplicate_rows: int,
        outlier_count: int,
    ) -> List[str]:
        issues = []

        for col in high_null_cols:
            issues.append(f"Column '{col}' has >50% missing values.")
        for col in moderate_null_cols:
            issues.append(f"Column '{col}' has 20-50% missing values.")
        for col, cnt in negative_values.items():
            issues.append(f"Measure '{col}' contains {cnt} negative value(s).")
        for col in empty_string_cols:
            issues.append(f"Dimension '{col}' contains empty strings.")
        for col in high_cardinality_cols:
                issues.append(f"Column '{col}' has very high cardinality ({col_profile.get('distinct_count', 0)} distinct values).")
        for col in redundant_cols:
            issues.append(f"Measure '{col}' has near-zero variance and may be redundant.")
        if duplicate_rows > 0:
            issues.append(f"Dataset may contain {duplicate_rows} duplicate row(s).")
        if outlier_count > 0:
            issues.append(f"{outlier_count} measure column(s) contain outlier values.")

        return issues