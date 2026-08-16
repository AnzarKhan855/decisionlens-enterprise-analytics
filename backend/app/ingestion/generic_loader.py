import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd

from app.database.storage import ParquetStorageManager, STORAGE_DIR, UPLOAD_RAW_DIR
from app.database.duckdb_engine import _validate_parquet_path
from app.logging.logger import get_logger

logger = get_logger(__name__)


class CsvImportError(Exception):
    def __init__(self, message: str, stage: str, filename: str, absolute_path: str,
                 sql_query: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.stage = stage
        self.filename = filename
        self.absolute_path = absolute_path
        self.sql_query = sql_query
        self.original_exception = original_exception


def _log_csv_import_error(stage: str, filename: str, absolute_path: str,
                          sql_query: str, exc: Exception) -> None:
    tb_str = traceback.format_exc()
    logger.error(
        "[CSV Import Error] stage=%s | filename=%s | path=%s | sql=%s | exception=%s: %s\n%s",
        stage, filename, absolute_path, sql_query,
        exc.__class__.__name__, str(exc), tb_str
    )


def _preflight_checks(file_path: Path, filename: str) -> None:
    absolute_path = str(file_path.resolve())

    if not file_path.exists():
        raise CsvImportError(
            message=f"File does not exist: {absolute_path}",
            stage="preflight_existence",
            filename=filename,
            absolute_path=absolute_path,
            sql_query="",
        )

    if file_path.stat().st_size == 0:
        raise CsvImportError(
            message=f"File is empty (0 bytes): {absolute_path}",
            stage="preflight_empty",
            filename=filename,
            absolute_path=absolute_path,
            sql_query="",
        )

    try:
        with open(file_path, "rb") as f:
            raw = f.read(4096)
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CsvImportError(
            message=f"File is not valid UTF-8: {absolute_path}",
            stage="preflight_encoding",
            filename=filename,
            absolute_path=absolute_path,
            sql_query="",
            original_exception=exc,
        ) from exc

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            sample = f.read(8192)
        if not sample.strip():
            raise CsvImportError(
                message=f"File contains no data after stripping whitespace: {absolute_path}",
                stage="preflight_empty_content",
                filename=filename,
                absolute_path=absolute_path,
                sql_query="",
            )
    except CsvImportError:
        raise
    except Exception as exc:
        raise CsvImportError(
            message=f"Failed to read file content: {absolute_path}",
            stage="preflight_read",
            filename=filename,
            absolute_path=absolute_path,
            sql_query="",
            original_exception=exc,
        ) from exc


def _detect_delimiter(file_path: Path, filename: str) -> Optional[str]:
    absolute_path = str(file_path.resolve())
    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            first_lines = ""
            for _ in range(5):
                line = f.readline()
                if not line:
                    break
                first_lines += line

        counts = {
            ",": first_lines.count(","),
            ";": first_lines.count(";"),
            "\t": first_lines.count("\t"),
            "|": first_lines.count("|"),
        }

        best_delim = max(counts, key=counts.get)
        if counts[best_delim] > 0:
            logger.info(
                "[CSV Delimiter Detection] filename=%s | path=%s | detected=%r | counts=%s",
                filename, absolute_path, repr(best_delim), counts
            )
            return best_delim
        return None
    except Exception as exc:
        logger.warning(
            "[CSV Delimiter Detection Failed] filename=%s | path=%s | error=%s: %s",
            filename, absolute_path, exc.__class__.__name__, str(exc)
        )
        return None


def _read_csv_with_conn(conn: duckdb.DuckDBPyConnection, src_str: str, dest_str: str, filename: str, absolute_path: str,
                         stage: str, ignore_errors: bool = False, sample_size: int = 1024,
                         header: bool = True, delimiter: Optional[str] = None) -> None:
    if delimiter:
        sql = (
            f"COPY (SELECT * FROM read_csv_auto(?, "
            f"ignore_errors={str(ignore_errors).lower()}, "
            f"sample_size={sample_size}, "
            f"header={str(header).lower()}, "
            f"delim='{delimiter}')) TO '{dest_str}' (FORMAT PARQUET)"
        )
        params = [src_str]
    else:
        sql = (
            f"COPY (SELECT * FROM read_csv_auto(?, "
            f"all_varchar=False, "
            f"ignore_errors={str(ignore_errors).lower()}, "
            f"sample_size={sample_size}, "
            f"header={str(header).lower()})) TO '{dest_str}' (FORMAT PARQUET)"
        )
        params = [src_str]

    logger.info(
        "[CSV DuckDB Execute] stage=%s | filename=%s | path=%s | sql=%s",
        stage, filename, absolute_path, sql
    )

    try:
        conn.execute(sql, params)
    except Exception as exc:
        _log_csv_import_error(stage, filename, absolute_path, sql, exc)
        raise CsvImportError(
            message=f"DuckDB read_csv_auto failed at stage '{stage}': {str(exc)}",
            stage=stage,
            filename=filename,
            absolute_path=absolute_path,
            sql_query=sql,
            original_exception=exc,
        ) from exc


def _import_csv_to_parquet(conn: duckdb.DuckDBPyConnection, src_str: str, dest_str: str,
                            file_path: Path, filename: str, absolute_path: str) -> None:
    _preflight_checks(file_path, filename)

    detected_delim = _detect_delimiter(file_path, filename)

    if detected_delim and detected_delim != ",":
        logger.info(
            "[CSV Import] Non-comma delimiter detected (%r), trying explicit delimiter first.",
            repr(detected_delim)
        )
        try:
            _read_csv_with_conn(conn, src_str, dest_str, filename, absolute_path,
                                stage="csv_explicit_delimiter", delimiter=detected_delim)
            return
        except CsvImportError:
            pass

    try:
        _read_csv_with_conn(conn, src_str, dest_str, filename, absolute_path,
                            stage="csv_read_csv_auto", ignore_errors=False, sample_size=1024, header=True)
        return
    except CsvImportError:
        pass

    try:
        logger.info(
            "[CSV Import Retry 1] filename=%s | path=%s | ignore_errors=true, sample_size=-1, header=true",
            filename, absolute_path
        )
        _read_csv_with_conn(conn, src_str, dest_str, filename, absolute_path,
                            stage="csv_retry_ignore_errors", ignore_errors=True, sample_size=-1, header=True)
        return
    except CsvImportError:
        pass

    try:
        logger.info(
            "[CSV Import Fallback Pandas] filename=%s | path=%s | engine=pandas",
            filename, absolute_path
        )
        df = pd.read_csv(
            file_path,
            sep=detected_delim or ",",
            quotechar='"',
            encoding="utf-8",
            on_bad_lines="skip",
            engine="python",
        )
        conn.register("csv_df", df)
        sql = f"COPY (SELECT * FROM csv_df) TO '{dest_str}' (FORMAT PARQUET)"
        logger.info("[CSV Pandas DuckDB Execute] filename=%s | sql=%s", filename, sql)
        conn.execute(sql)
        logger.info("[CSV Import Fallback Pandas] SUCCESS for filename=%s", filename)
        return
    except Exception as exc:
        _log_csv_import_error("csv_fallback_pandas", filename, absolute_path, f"pd.read_csv -> {dest_str}", exc)
        raise CsvImportError(
            message=f"CSV import fallback (pandas) failed: {str(exc)}",
            stage="csv_fallback_pandas",
            filename=filename,
            absolute_path=absolute_path,
            sql_query=f"pd.read_csv({absolute_path})",
            original_exception=exc,
        ) from exc

    if detected_delim and detected_delim == ",":
        try:
            logger.info(
                "[CSV Import Retry 2] filename=%s | path=%s | explicit comma delimiter",
                filename, absolute_path
            )
            _read_csv_with_conn(conn, src_str, dest_str, filename, absolute_path,
                                stage="csv_retry_explicit_comma", delimiter=",")
            return
        except CsvImportError:
            pass

    for delim_char in [",", ";", "\t", "|"]:
        if detected_delim and delim_char == detected_delim:
            continue
        try:
            logger.info(
                "[CSV Import Retry Delimiter] filename=%s | path=%s | delimiter=%r",
                filename, absolute_path, repr(delim_char)
            )
            _read_csv_with_conn(conn, src_str, dest_str, filename, absolute_path,
                                stage=f"csv_retry_delim_{repr(delim_char)}", delimiter=delim_char)
            return
        except CsvImportError:
            continue

    raise CsvImportError(
        message=(
            "All CSV import strategies failed for "
            f"'{filename}'. Check encoding, delimiter, headers, quoting, and malformed rows."
        ),
        stage="csv_all_strategies_failed",
        filename=filename,
        absolute_path=absolute_path,
        sql_query=src_str,
    )


def _is_cloud_synced_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
        onedrive = Path.home() / "OneDrive"
        onedrive_documents = onedrive / "Documents"
        return resolved.is_relative_to(onedrive.resolve()) or resolved.is_relative_to(onedrive_documents.resolve())
    except Exception:
        return False


class GenericDataLoader:
    """
    Streams and converts raw files (CSV, Excel, Parquet) into normalized Parquet format.
    Uses DuckDB for streaming CSV/Parquet conversions to minimize RAM overhead.
    Optionally enriches with retail semantic mapping after loading.
    """

    @staticmethod
    def convert_to_parquet(file_path: Path, dataset_id: str) -> Path:
        target_parquet_path = ParquetStorageManager.get_parquet_path(dataset_id)
        dest_str = _validate_parquet_path(target_parquet_path)
        suffix = file_path.suffix.lower()

        resolved_src = file_path.resolve()
        allowed_roots = [
            STORAGE_DIR.resolve(),
            UPLOAD_RAW_DIR.resolve(),
            Path(tempfile.gettempdir()).resolve(),
        ]
        if not any(resolved_src.is_relative_to(root) for root in allowed_roots):
            raise ValueError(f"Source file path is outside allowed directories: {file_path}")
        filename = file_path.name
        absolute_path = str(resolved_src)

        if target_parquet_path.exists():
            try:
                target_parquet_path.unlink(missing_ok=True)
            except Exception:
                import uuid
                target_parquet_path = ParquetStorageManager.get_parquet_path(f"{dataset_id}_{uuid.uuid4().hex[:4]}")
                dest_str = _validate_parquet_path(target_parquet_path)

        local_tmp_dir = None
        working_path = resolved_src
        working_src_str = str(resolved_src.as_posix())

        if _is_cloud_synced_path(resolved_src):
            local_tmp_dir = tempfile.mkdtemp(prefix="decisionlens_csv_")
            working_path = Path(local_tmp_dir) / filename
            shutil.copy2(resolved_src, working_path)
            working_src_str = str(working_path.resolve().as_posix())
            logger.info(
                "[CSV Local Copy] filename=%s | original_path=%s | local_path=%s",
                filename, absolute_path, working_src_str
            )

        conn = duckdb.connect(database=":memory:")
        try:
            if suffix == ".csv":
                _import_csv_to_parquet(conn, working_src_str, dest_str, working_path, filename, working_src_str)
            elif suffix == ".parquet":
                sql = f"COPY (SELECT * FROM read_parquet('{working_src_str}')) TO '{dest_str}' (FORMAT PARQUET)"
                logger.info(
                    "[Parquet DuckDB Execute] filename=%s | path=%s | sql=%s",
                    filename, working_src_str, sql
                )
                try:
                    conn.execute(sql)
                except Exception as exc:
                    _log_csv_import_error("parquet_import", filename, working_src_str, sql, exc)
                    raise CsvImportError(
                        message=f"DuckDB read_parquet failed: {str(exc)}",
                        stage="parquet_import",
                        filename=filename,
                        absolute_path=working_src_str,
                        sql_query=sql,
                        original_exception=exc,
                    ) from exc
            elif suffix in [".xlsx", ".xls"]:
                logger.info(
                    "[Excel Import] filename=%s | path=%s | engine=pandas",
                    filename, working_src_str
                )
                df = pd.read_excel(working_path)
                conn.register("excel_df", df)
                sql = f"COPY (SELECT * FROM excel_df) TO '{dest_str}' (FORMAT PARQUET)"
                logger.info("[Excel DuckDB Execute] filename=%s | sql=%s", filename, sql)
                conn.execute(sql)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
        finally:
            conn.close()
            if local_tmp_dir is not None:
                try:
                    shutil.rmtree(local_tmp_dir, ignore_errors=True)
                    logger.info("[CSV Local Cleanup] Removed temp dir: %s", local_tmp_dir)
                except Exception as cleanup_err:
                    logger.warning("[CSV Local Cleanup Failed] %s: %s", local_tmp_dir, cleanup_err)

        return target_parquet_path

    @staticmethod
    def enrich_with_retail_semantics(parquet_path: Path) -> Dict[str, Any]:
        try:
            from app.retail.engine import RetailSemanticEngine
            return RetailSemanticEngine.enrich_profile(parquet_path)
        except Exception as e:
            logger.warning(f"Retail semantic enrichment failed for {parquet_path}: {str(e)}")
            return {}
