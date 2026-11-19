import logging
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_score_cache = {}
_resolved_path_cache = {}

# Standard directory for storing uploaded dataset parquet files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "parquet"
UPLOAD_RAW_DIR = BASE_DIR / "storage" / "raw"
UPLOAD_EXTRACTED_DIR = BASE_DIR / "storage" / "uploads"
UPLOAD_ZIP_DIR = BASE_DIR / "storage" / "zips"


class ParquetStorageManager:
    """
    Manages physical storage of raw uploads, compressed Parquet files, extracted folders, and ZIP archives.
    Integrates with MongoDB GridFS for persistent multi-container cross-restart data continuity.
    """

    _SYSTEM_FILE_PREFIXES = ("sample-", "unified_", "tmp_", "ds-bench-", "test_")

    @staticmethod
    def ensure_directories():
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_RAW_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_ZIP_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_gridfs():
        try:
            import gridfs
            from app.database.mongodb import get_database
            db = get_database()
            return gridfs.GridFS(db)
        except Exception as e:
            logger.debug(f"[GridFS] Connection unavailable: {e}")
            return None

    @staticmethod
    def persist_to_gridfs(file_path: Path, filename: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
        """Saves a parquet or data file to MongoDB GridFS for persistent cross-container storage."""
        if not file_path.exists():
            return False
        fs = ParquetStorageManager._get_gridfs()
        if fs is None:
            return False
        try:
            fn = filename or file_path.name
            for existing in fs.find({"filename": fn}):
                fs.delete(existing._id)
            with open(file_path, "rb") as f:
                fs.put(f, filename=fn, metadata=metadata or {})
            logger.info(f"[GridFS Persisted] {fn} ({file_path.stat().st_size} bytes)")
            return True
        except Exception as e:
            logger.warning(f"[GridFS Save Warning] {file_path.name}: {e}")
            return False

    @staticmethod
    def restore_from_gridfs(filename: str, target_path: Optional[Path] = None) -> Optional[Path]:
        """Restores a file from MongoDB GridFS if missing from local storage."""
        ParquetStorageManager.ensure_directories()
        out_path = target_path or (STORAGE_DIR / filename)
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path
        fs = ParquetStorageManager._get_gridfs()
        if fs is None:
            return None
        try:
            grid_out = fs.find_one({"filename": filename})
            if not grid_out:
                grid_out = fs.find_one({"filename": {"$regex": f"{filename}$"}})
            if grid_out:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(grid_out.read())
                logger.info(f"[GridFS Restored] {filename} -> {out_path} ({out_path.stat().st_size} bytes)")
                return out_path
        except Exception as e:
            logger.debug(f"[GridFS Restore Warning] {filename}: {e}")
        return None

    @staticmethod
    def restore_workspace_from_gridfs(workspace_id: str) -> List[Path]:
        """Restores all table parquet files for a given workspace from MongoDB GridFS."""
        ParquetStorageManager.ensure_directories()
        fs = ParquetStorageManager._get_gridfs()
        if fs is None:
            return []
        restored: List[Path] = []
        try:
            pattern = f"^{workspace_id}__"
            for grid_out in fs.find({"filename": {"$regex": pattern}}):
                dest = STORAGE_DIR / grid_out.filename
                if not dest.exists() or dest.stat().st_size == 0:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(grid_out.read())
                    logger.info(f"[GridFS Restored WS File] {grid_out.filename} ({dest.stat().st_size} bytes)")
                restored.append(dest)
        except Exception as e:
            logger.debug(f"[GridFS Restore WS Warning] {workspace_id}: {e}")
        return restored

    @staticmethod
    def get_parquet_path(dataset_id: str) -> Path:
        ParquetStorageManager.ensure_directories()
        target = STORAGE_DIR / f"{dataset_id}.parquet"
        if not target.exists():
            restored = ParquetStorageManager.restore_from_gridfs(f"{dataset_id}.parquet", target)
            if restored and restored.exists():
                return restored
        return target

    @staticmethod
    def get_parquet_path_for_workspace(dataset_id: str) -> Optional[Path]:
        """
        Resolve a parquet path for a dataset/workspace ID.
        Handles both single-file datasets ({id}.parquet) and workspace uploads ({id}__*.parquet).
        Returns the best table (preferring measures + temporal columns) for workspace uploads.
        """
        cached_p = _resolved_path_cache.get(dataset_id)
        if cached_p and cached_p.exists():
            return cached_p

        direct = ParquetStorageManager.get_parquet_path(dataset_id)
        if direct.exists():
            _resolved_path_cache[dataset_id] = direct
            return direct

        unified = STORAGE_DIR / f"unified_{dataset_id}.parquet"
        if unified.exists():
            _resolved_path_cache[dataset_id] = unified
            return unified

        seen_files = set()
        matched_files: List[Path] = []
        for pat in [f"{dataset_id}__*.parquet", f"{dataset_id}_*.parquet"]:
            for pfile in STORAGE_DIR.glob(pat):
                if pfile.name not in seen_files:
                    seen_files.add(pfile.name)
                    matched_files.append(pfile)

        # If no local files matched, attempt to restore from GridFS
        if not matched_files:
            restored = ParquetStorageManager.restore_workspace_from_gridfs(dataset_id)
            if restored:
                for r in restored:
                    if r.name not in seen_files:
                        seen_files.add(r.name)
                        matched_files.append(r)

        # Also check EnterpriseWorkspaceManager tables and restore them if needed
        if not matched_files:
            try:
                from app.services.workspace_service import EnterpriseWorkspaceManager
                ws_info = EnterpriseWorkspaceManager.get_workspace(dataset_id)
                if ws_info and ws_info.get("tables"):
                    for tbl in ws_info["tables"]:
                        fn = Path(tbl.get("file_path", "")).name
                        if fn:
                            res = ParquetStorageManager.restore_from_gridfs(fn)
                            if res and res.exists() and res.name not in seen_files:
                                seen_files.add(res.name)
                                matched_files.append(res)
            except Exception:
                pass

        candidates: List[Tuple[int, int, Path]] = []

        def _score_file(pfile: Path) -> Tuple[int, int]:
            try:
                st = pfile.stat()
                ck = (str(pfile), st.st_mtime)
                if ck in _score_cache:
                    return _score_cache[ck]

                import duckdb
                conn = duckdb.connect(":memory:")
                schema = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{pfile.as_posix()}')").fetchall()
                numeric_cols = sum(1 for c in schema if any(nt in c[1].upper() for nt in ["BIGINT", "INTEGER", "INT", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"]))
                row_count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pfile.as_posix()}')").fetchone()[0]
                has_temporal = any(any(dt in c[1].upper() for dt in ["DATE", "TIME", "TIMESTAMP"]) for c in schema)
                conn.close()
                temporal_bonus = 5000000 if has_temporal else 0
                score = temporal_bonus + numeric_cols * 10000 + row_count
                _score_cache[ck] = (score, row_count)
                return score, row_count
            except Exception:
                return 0, 0

        for pfile in matched_files:
            if pfile.name.startswith(ParquetStorageManager._SYSTEM_FILE_PREFIXES):
                continue
            if not pfile.exists():
                continue
            score, row_count = _score_file(pfile)
            candidates.append((score, row_count, pfile))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        resolved = candidates[0][2]
        _resolved_path_cache[dataset_id] = resolved
        return resolved

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

        # Delete from MongoDB GridFS
        fs = ParquetStorageManager._get_gridfs()
        if fs:
            try:
                for grid_f in fs.find({"filename": {"$regex": f"^{dataset_id}"}}):
                    fs.delete(grid_f._id)
                    deleted_count += 1
            except Exception as e:
                logger.debug(f"[GridFS Purge Warning] {dataset_id}: {e}")

        return deleted_count
