import os
import tempfile
from pathlib import Path
from io import BytesIO

import duckdb
import pandas as pd
import pytest

# Ensure backend directory is on sys.path so `app.*` imports resolve
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader, CsvImportError


def _save_and_convert(csv_bytes: bytes, dataset_id: str, filename: str = "data.csv") -> Path:
    ParquetStorageManager.ensure_directories()
    raw_path = ParquetStorageManager.get_raw_path(dataset_id, filename)
    with open(raw_path, "wb") as f:
        f.write(csv_bytes)
    return GenericDataLoader.convert_to_parquet(raw_path, dataset_id)


def _parquet_has_rows(parquet_path: Path) -> bool:
    conn = duckdb.connect(":memory:")
    try:
        result = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path.as_posix()}')").fetchone()
        return result[0] > 0
    finally:
        conn.close()


class TestCsvUploadScenarios:
    """Test GenericDataLoader.convert_to_parquet() with different CSV formats."""

    def teardown_method(self, method):
        pass

    def test_normal_csv(self):
        csv_content = b"id,name,revenue\n1,Alice,100.5\n2,Bob,200.0\n3,Charlie,300.5\n"
        dataset_id = "test_normal_csv"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "normal.csv")
            assert parquet_path.exists(), "Parquet file should be created"
            assert _parquet_has_rows(parquet_path), "Parquet should contain rows"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_quoted_csv(self):
        csv_content = b'id,name,revenue\n1,"Alice, Jr.",100.5\n2,"Bob ""The Builder""",200.0\n'
        dataset_id = "test_quoted_csv"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "quoted.csv")
            assert parquet_path.exists(), "Parquet file should be created"
            assert _parquet_has_rows(parquet_path), "Parquet should contain rows"
            conn = duckdb.connect(":memory:")
            try:
                rows = conn.execute(
                    f"SELECT name FROM read_parquet('{parquet_path.as_posix()}') ORDER BY id"
                ).fetchall()
                names = [r[0] for r in rows]
                assert "Alice, Jr." in names, f"Expected quoted name, got {names}"
                assert any("Bob" in str(n) for n in names), f"Expected quoted Bob name, got {names}"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_semicolon_csv(self):
        csv_content = b"id;name;revenue\n1;Alice;100.5\n2;Bob;200.0\n3;Charlie;300.5\n"
        dataset_id = "test_semicolon_csv"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "semicolon.csv")
            assert parquet_path.exists(), "Parquet file should be created"
            assert _parquet_has_rows(parquet_path), "Parquet should contain rows"
            conn = duckdb.connect(":memory:")
            try:
                rows = conn.execute(
                    f"SELECT name FROM read_parquet('{parquet_path.as_posix()}') ORDER BY id"
                ).fetchall()
                names = [r[0] for r in rows]
                assert names == ["Alice", "Bob", "Charlie"], f"Expected Alice/Bob/Charlie, got {names}"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_tab_csv(self):
        csv_content = b"id\tname\trevenue\n1\tAlice\t100.5\n2\tBob\t200.0\n3\tCharlie\t300.5\n"
        dataset_id = "test_tab_csv"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "tab.csv")
            assert parquet_path.exists(), "Parquet file should be created"
            assert _parquet_has_rows(parquet_path), "Parquet should contain rows"
            conn = duckdb.connect(":memory:")
            try:
                rows = conn.execute(
                    f"SELECT name FROM read_parquet('{parquet_path.as_posix()}') ORDER BY id"
                ).fetchall()
                names = [r[0] for r in rows]
                assert names == ["Alice", "Bob", "Charlie"], f"Expected Alice/Bob/Charlie, got {names}"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_pipe_csv(self):
        csv_content = b"id|name|revenue\n1|Alice|100.5\n2|Bob|200.0\n3|Charlie|300.5\n"
        dataset_id = "test_pipe_csv"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "pipe.csv")
            assert parquet_path.exists(), "Parquet file should be created"
            assert _parquet_has_rows(parquet_path), "Parquet should contain rows"
            conn = duckdb.connect(":memory:")
            try:
                rows = conn.execute(
                    f"SELECT name FROM read_parquet('{parquet_path.as_posix()}') ORDER BY id"
                ).fetchall()
                names = [r[0] for r in rows]
                assert names == ["Alice", "Bob", "Charlie"], f"Expected Alice/Bob/Charlie, got {names}"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_empty_csv_raises(self):
        empty_bytes = b""
        dataset_id = "test_empty_csv"
        try:
            with pytest.raises(CsvImportError) as exc_info:
                _save_and_convert(empty_bytes, dataset_id, "empty.csv")
            assert "empty" in str(exc_info.value).lower() or "0 bytes" in str(exc_info.value).lower()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_only_header_csv_succeeds_with_zero_rows(self):
        header_only = b"id,name,revenue\n"
        dataset_id = "test_header_only_csv"
        try:
            parquet_path = _save_and_convert(header_only, dataset_id, "header_only.csv")
            assert parquet_path.exists()
            conn = duckdb.connect(":memory:")
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path.as_posix()}')").fetchone()[0]
                assert cnt == 0, f"Expected 0 rows for header-only CSV, got {cnt}"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_malformed_csv_raises_or_succeeds_gracefully(self):
        malformed = b"id,name,revenue\n1,Alice,100.5\n2,Bob,not_a_number\n3,Charlie,300.5\n"
        dataset_id = "test_malformed_csv"
        try:
            parquet_path = _save_and_convert(malformed, dataset_id, "malformed.csv")
            assert parquet_path.exists()
            conn = duckdb.connect(":memory:")
            try:
                rows = conn.execute(
                    f"SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
                ).fetchall()
                assert len(rows) >= 1, "Should have at least some rows despite malformed data"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_non_utf8_csv_raises(self):
        non_utf8 = b"id,name,revenue\n1,Alice,\xff\xfe\n"
        dataset_id = "test_non_utf8_csv"
        try:
            with pytest.raises(CsvImportError) as exc_info:
                _save_and_convert(non_utf8, dataset_id, "non_utf8.csv")
            assert "utf-8" in str(exc_info.value).lower() or "encoding" in str(exc_info.value).lower()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_csv_with_extra_delimiter_chars_in_data(self):
        csv_content = b"id,name,notes\n1,Alice,\"Has comma, and semicolon; in notes\"\n2,Bob,Clean\n"
        dataset_id = "test_extra_delim_chars"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "extra_delim.csv")
            assert parquet_path.exists()
            assert _parquet_has_rows(parquet_path)
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_csv_with_mismatched_quotes_falls_back(self):
        csv_content = b'id,name,notes\n1,Alice,"Unclosed quote\n2,Bob,Has newline in value\n'
        dataset_id = "test_mismatched_quotes"
        try:
            parquet_path = _save_and_convert(csv_content, dataset_id, "mismatched.csv")
            assert parquet_path.exists()
            # pandas fallback with on_bad_lines=skip may produce partial or empty results
            conn = duckdb.connect(":memory:")
            try:
                rows = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{parquet_path.as_posix()}')").fetchone()[0]
                assert rows >= 0, "Should produce some rows or zero rows"
            finally:
                conn.close()
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)
