import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def detect_and_normalize_csv_encoding(file_path: Path, filename: str) -> Tuple[Path, str, bool]:
    """
    Robust CSV encoding detection & normalization.
    Detects UTF-8, UTF-8-BOM, Windows-1252 (e.g. byte 0xA0 in Excel/Superstore), and Latin-1.
    If non-UTF-8 is detected, streams and normalizes the file to clean UTF-8 before ingestion.
    Returns (working_path, detected_encoding_label, was_normalized).
    """
    try:
        with open(file_path, "rb") as f:
            sample = f.read(65536)
    except Exception as e:
        logger.warning("[Encoding Detection Error] Could not read sample: %s", e)
        return file_path, "UTF-8", False

    detected_encoding = "utf-8"
    if sample.startswith(b'\xef\xbb\xbf'):
        detected_encoding = "utf-8-sig"
    else:
        try:
            sample.decode("utf-8")
            detected_encoding = "utf-8"
        except UnicodeDecodeError:
            try:
                sample.decode("windows-1252")
                detected_encoding = "windows-1252"
            except UnicodeDecodeError:
                detected_encoding = "latin-1"

    if detected_encoding in ("windows-1252", "latin-1", "utf-8-sig"):
        normalized_tmp = file_path.with_name(f"{file_path.stem}__normalized_utf8.csv")
        try:
            with open(file_path, "r", encoding=detected_encoding, errors="replace") as src, \
                 open(normalized_tmp, "w", encoding="utf-8", newline="") as dst:
                while True:
                    chunk = src.read(65536)
                    if not chunk:
                        break
                    dst.write(chunk)
            encoding_label = (
                "Windows-1252" if detected_encoding == "windows-1252"
                else ("Latin-1" if detected_encoding == "latin-1" else "UTF-8 with BOM")
            )
            logger.info(
                "[CSV Ingestion] CSV encoding detected as %s and normalized successfully to UTF-8 for filename=%s",
                encoding_label, filename
            )
            return normalized_tmp, encoding_label, True
        except Exception as norm_err:
            logger.warning("[CSV Normalization Warning] Failed to normalize encoding: %s", norm_err)
            if normalized_tmp.exists():
                normalized_tmp.unlink(missing_ok=True)
            return file_path, detected_encoding, False

    return file_path, "UTF-8", False


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
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw.decode("windows-1252")
            except UnicodeDecodeError:
                raw.decode("latin-1")
    except Exception as exc:
        raise CsvImportError(
            message=f"File encoding is invalid or unreadable: {absolute_path}",
            stage="preflight_encoding",
            filename=filename,
            absolute_path=absolute_path,
            sql_query="",
            original_exception=exc,
        ) from exc

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
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
        with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
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
    # 1. Normalize encoding (Windows-1252 byte 0xA0, Latin-1, UTF-8 BOM, etc.)
    effective_path, encoding_label, is_temp = detect_and_normalize_csv_encoding(file_path, filename)
    effective_src_str = effective_path.as_posix()

    try:
        _preflight_checks(effective_path, filename)
        detected_delim = _detect_delimiter(effective_path, filename)

        # Strategy 1: Explicit delimiter if non-comma detected
        if detected_delim and detected_delim != ",":
            logger.info(
                "[CSV Import] Non-comma delimiter detected (%r), trying explicit delimiter first.",
                repr(detected_delim)
            )
            try:
                _read_csv_with_conn(conn, effective_src_str, dest_str, filename, absolute_path,
                                    stage="csv_explicit_delimiter", delimiter=detected_delim)
                return
            except CsvImportError:
                pass

        # Strategy 2: Standard DuckDB read_csv_auto
        try:
            _read_csv_with_conn(conn, effective_src_str, dest_str, filename, absolute_path,
                                stage="csv_read_csv_auto", ignore_errors=False, sample_size=2048, header=True)
            return
        except CsvImportError:
            pass

        # Strategy 3: Standard DuckDB with ignore_errors=True
        try:
            logger.info(
                "[CSV Import Retry 1] filename=%s | path=%s | ignore_errors=true, sample_size=-1",
                filename, absolute_path
            )
            _read_csv_with_conn(conn, effective_src_str, dest_str, filename, absolute_path,
                                stage="csv_retry_ignore_errors", ignore_errors=True, sample_size=-1, header=True)
            return
        except CsvImportError:
            pass

        # Strategy 4: Try explicit delimiters with ignore_errors=True
        delims_to_try = [detected_delim] if detected_delim else [",", ";", "\t", "|"]
        for d in delims_to_try:
            if not d:
                continue
            try:
                _read_csv_with_conn(conn, effective_src_str, dest_str, filename, absolute_path,
                                    stage=f"csv_retry_delim_{repr(d)}", delimiter=d, ignore_errors=True)
                return
            except CsvImportError:
                continue

        # Strategy 5: Fast streaming fallback with all_varchar=True in DuckDB
        # Extremely fast for large datasets with mixed types or weird rows without Python RAM bloat
        try:
            logger.info(
                "[CSV Import Retry 3] filename=%s | path=%s | all_varchar=true streaming fallback",
                filename, absolute_path
            )
            delim_clause = f", delim='{detected_delim}'" if detected_delim else ""
            sql = (
                f"COPY (SELECT * FROM read_csv_auto(?, "
                f"all_varchar=True, "
                f"ignore_errors=True, "
                f"sample_size=-1, "
                f"header=True{delim_clause})) TO '{dest_str}' (FORMAT PARQUET)"
            )
            conn.execute(sql, [effective_src_str])
            logger.info("[CSV Import] SUCCESS with all_varchar=True for %s", filename)
            return
        except Exception as exc:
            logger.warning("[CSV Import] all_varchar=True fallback failed for %s: %s", filename, exc)

        # Strategy 6: Pandas fallback with chunking to avoid memory exhaustion
        try:
            logger.info(
                "[CSV Import Fallback Pandas] filename=%s | path=%s | engine=pandas",
                filename, absolute_path
            )
            chunks = []
            total_rows = 0
            for chunk in pd.read_csv(
                effective_path,
                sep=detected_delim or ",",
                quotechar='"',
                encoding="utf-8",
                on_bad_lines="skip",
                engine="python",
                chunksize=100_000,
            ):
                chunks.append(chunk)
                total_rows += len(chunk)
                if total_rows >= 500_000:
                    break
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
                conn.register("csv_df", df)
                conn.execute(f"COPY (SELECT * FROM csv_df) TO '{dest_str}' (FORMAT PARQUET)")
                conn.unregister("csv_df")
                logger.info("[CSV Import Fallback Pandas] SUCCESS for filename=%s", filename)
                return
        except Exception as exc:
            _log_csv_import_error("csv_fallback_pandas", filename, absolute_path, f"pd.read_csv -> {dest_str}", exc)

        raise CsvImportError(
            message=(
                "All CSV import strategies failed for "
                f"'{filename}'. Check encoding, delimiter, headers, quoting, and malformed rows."
            ),
            stage="csv_all_strategies_failed",
            filename=filename,
            absolute_path=absolute_path,
            sql_query=effective_src_str,
        )
    finally:
        if is_temp and effective_path.exists():
            try:
                effective_path.unlink(missing_ok=True)
            except Exception:
                pass


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
            Path.cwd().resolve(),
            Path(__file__).resolve().parents[2],
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
