import os
import shutil
from pathlib import Path
from typing import Tuple, Optional, List

# Standard directory for storing uploaded dataset parquet files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "parquet"
UPLOAD_RAW_DIR = BASE_DIR / "storage" / "raw"
UPLOAD_EXTRACTED_DIR = BASE_DIR / "storage" / "uploads"
UPLOAD_ZIP_DIR = BASE_DIR / "storage" / "zips"


class ParquetStorageManager:
    """
    Manages physical storage of raw uploads, compressed Parquet files, extracted folders, and ZIP archives.
    """

    _SYSTEM_FILE_PREFIXES = ("sample-", "unified_", "tmp_")

    @staticmethod
    def ensure_directories():
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_RAW_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_ZIP_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_parquet_path(dataset_id: str) -> Path:
        ParquetStorageManager.ensure_directories()
        return STORAGE_DIR / f"{dataset_id}.parquet"

    @staticmethod
    def get_parquet_path_for_workspace(dataset_id: str) -> Optional[Path]:
        """
        Resolve a parquet path for a dataset/workspace ID.
        Handles both single-file datasets ({id}.parquet) and workspace uploads ({id}__*.parquet).
        Returns the best table (preferring measures + temporal columns) for workspace uploads.
        """
        direct = ParquetStorageManager.get_parquet_path(dataset_id)
        if direct.exists():
            return direct

        prefix = f"{dataset_id}__"
        candidates: List[Tuple[int, int, Path]] = []

        def _score_file(pfile: Path) -> Tuple[int, int]:
            try:
                import duckdb
                conn = duckdb.connect(":memory:")
                schema = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{pfile.as_posix()}')").fetchall()
                numeric_cols = sum(1 for c in schema if any(nt in c[1].upper() for nt in ["BIGINT", "INTEGER", "INT", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"]))
                row_count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pfile.as_posix()}')").fetchone()[0]
                has_temporal = any(any(dt in c[1].upper() for dt in ["DATE", "TIME", "TIMESTAMP"]) for c in schema)
                conn.close()
                temporal_bonus = 5000000 if has_temporal else 0
                score = temporal_bonus + numeric_cols * 10000 + row_count
                return score, row_count
            except Exception:
                return 0, 0

        for pfile in STORAGE_DIR.glob(f"{prefix}*.parquet"):
            if pfile.name.startswith(ParquetStorageManager._SYSTEM_FILE_PREFIXES):
                continue
            if not pfile.exists():
                continue
            score, row_count = _score_file(pfile)
            candidates.append((score, row_count, pfile))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][2]

    @staticmethod
    def get_raw_path(dataset_id: str, original_filename: str) -> Path:
        ParquetStorageManager.ensure_directories()
        ext = Path(original_filename).suffix
        return UPLOAD_RAW_DIR / f"{dataset_id}{ext}"

    @staticmethod
    def save_raw_file(file_bytes: bytes, dataset_id: str, original_filename: str) -> Path:
        raw_path = ParquetStorageManager.get_raw_path(dataset_id, original_filename)
        with open(raw_path, "wb") as f:
            f.write(file_bytes)
        return raw_path

    @staticmethod
    def delete_dataset_files(dataset_id: str) -> int:
        """
        Permanently deletes all physical files associated with a dataset or workspace across all storage directories.
        Returns the count of deleted file-system entries.
        """
        ParquetStorageManager.ensure_directories()
        deleted_count = 0

        for base in [STORAGE_DIR, Path("storage/parquet"), Path("backend/storage/parquet")]:
            if base.exists():
                for pfile in list(base.glob(f"*{dataset_id}*")):
                    try:
                        if pfile.is_file():
                            pfile.unlink()
                            deleted_count += 1
                        elif pfile.is_dir():
                            shutil.rmtree(pfile, ignore_errors=True)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"[Purge Warning] Failed to delete {pfile}: {e}")

        for base in [UPLOAD_RAW_DIR, Path("storage/raw"), Path("backend/storage/raw")]:
            if base.exists():
                for rfile in list(base.glob(f"*{dataset_id}*")):
                    try:
                        if rfile.is_file():
                            rfile.unlink()
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"[Purge Warning] Failed to delete raw file {rfile}: {e}")

        for base in [UPLOAD_EXTRACTED_DIR, Path("storage/uploads"), Path("backend/storage/uploads")]:
            if base.exists():
                target_dir = base / dataset_id
                if target_dir.exists() and target_dir.is_dir():
                    try:
                        shutil.rmtree(target_dir, ignore_errors=True)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"[Purge Warning] Failed to delete extracted dir {target_dir}: {e}")

        for base in [UPLOAD_ZIP_DIR, Path("storage/zips"), Path("backend/storage/zips")]:
            if base.exists():
                for zfile in list(base.glob(f"*{dataset_id}*")):
                    try:
                        if zfile.is_file():
                            zfile.unlink()
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"[Purge Warning] Failed to delete zip {zfile}: {e}")

        return deleted_count
