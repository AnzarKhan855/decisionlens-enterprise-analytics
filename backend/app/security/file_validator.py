import re
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from app.logging.logger import get_logger

logger = get_logger(__name__)


class FileValidationError(Exception):
    def __init__(self, message: str, reason: str = "", recovery_suggestion: str = ""):
        self.message = message
        self.reason = reason
        self.recovery_suggestion = recovery_suggestion
        super().__init__(self.message)


_CSV_INJECTION_PATTERN = re.compile(r"^\s*[=+\-@|]\s*[A-Za-z]", re.IGNORECASE)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "|", "\t")


def validate_csv_content(content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            return False, "File encoding is not supported. Use UTF-8 or Latin-1 encoded CSV."

    lines = text.splitlines()
    if not lines:
        return False, "File is empty."

    header = lines[0]
    if len(header.strip()) == 0:
        return False, "CSV file has no header row."

    for i, line in enumerate(lines[1: min(len(lines), 100)], start=2):
        if _CSV_INJECTION_PATTERN.match(line):
            return False, f"CSV injection detected at line {i}. Remove formula-like values starting with =, +, -, @, |."

    data_lines = [l for l in lines[1:] if l.strip()]
    if len(data_lines) == 0:
        return False, "CSV file contains headers but no data rows."

    return True, None


def validate_file_size(content: bytes, max_size_mb: int = 500) -> Tuple[bool, Optional[str]]:
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File size {size_mb:.1f}MB exceeds maximum {max_size_mb}MB."
    return True, None


def validate_parquet_content(path: Path, min_rows: int = 1) -> Tuple[bool, Optional[str]]:
    try:
        import duckdb
        conn = duckdb.connect(database=":memory:")
        conn.execute("SET threads TO 1")
        row_count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]
        conn.close()
        if row_count < min_rows:
            return False, f"Parquet file contains {row_count} rows. Minimum {min_rows} row required."
        return True, None
    except Exception as exc:
        return False, f"Parquet validation failed: {str(exc)}"


def detect_duplicate_content(content: bytes, existing_hashes: List[str]) -> Tuple[bool, Optional[str]]:
    sha256 = hashlib.sha256(content).hexdigest()
    if sha256 in existing_hashes:
        return False, "This file is identical to a previously uploaded dataset."
    return True, sha256


def sanitize_filename(filename: str) -> str:
    import re
    from pathlib import Path
    name = Path(filename).name
    name = re.sub(r'[^\w\.\-]', '_', name)
    while ".." in name:
        name = name.replace("..", "_")
    if not name or name.startswith("."):
        name = "uploaded_file_" + name
    return name


def validate_upload(
    content: bytes,
    filename: str,
    existing_hashes: Optional[List[str]] = None,
    max_size_mb: int = 500,
    min_rows: int = 1,
) -> Dict[str, Any]:
    errors = []
    warnings = []

    ok, reason = validate_file_size(content, max_size_mb)
    if not ok:
        errors.append(reason)

    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        ok, reason = validate_csv_content(content, filename)
        if not ok:
            errors.append(reason)
    elif ext == ".parquet":
        if len(content) < 4 or not content.startswith(b"PAR1"):
            errors.append("Invalid Parquet file: Missing 'PAR1' magic header.")
        else:
            import tempfile
            tmp_path = Path(tempfile.gettempdir()) / f"validate_{int(time.time())}_{sanitize_filename(filename)}"
            try:
                tmp_path.write_bytes(content)
                ok, reason = validate_parquet_content(tmp_path, min_rows=min_rows)
                if not ok:
                    errors.append(reason)
            finally:
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass

    if existing_hashes:
        ok, hash_result = detect_duplicate_content(content, existing_hashes)
        if not ok:
            warnings.append(hash_result)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "filename": sanitize_filename(filename),
    }
