import re
import html
from typing import Any, Dict, Optional
from pathlib import Path


class InputSanitizer:
    SQL_INJECTION_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|TRUNCATE)\b)", re.IGNORECASE),
        re.compile(r"(--|;|\/\*|\*\/|xp_|sp_)"),
        re.compile(r"(\bOR\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
        re.compile(r"(\bAND\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
    ]

    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"(ignore\s+(previous|above|all)\s+instructions)", re.IGNORECASE),
        re.compile(r"(disregard\s+(previous|above|all))", re.IGNORECASE),
        re.compile(r"(forget\s+(everything|all|previous))", re.IGNORECASE),
        re.compile(r"(you\s+are\s+now\s+(a|an|acting))", re.IGNORECASE),
        re.compile(r"(system\s+prompt\s*[:=])", re.IGNORECASE),
        re.compile(r"(roleplay|pretend\s+to\s+be)", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 10000) -> str:
        if not isinstance(value, str):
            return str(value)
        value = html.escape(value)
        value = value[:max_length]
        return value

    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @classmethod
    def check_prompt_injection(cls, value: str) -> bool:
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @classmethod
    def sanitize_identifier(cls, value: str) -> str:
        import re
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
            raise ValueError(f"Invalid identifier: {value}")
        return value

    @classmethod
    def validate_path(cls, path: Path, allowed_root: Path) -> Path:
        resolved = path.resolve()
        allowed = allowed_root.resolve()
        try:
            resolved.relative_to(allowed)
        except ValueError:
            raise ValueError(f"Path traversal detected: {path} is outside {allowed_root}")
        return resolved

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        if max_depth <= 0:
            return data
        result = {}
        for key, value in data.items():
            clean_key = cls.sanitize_string(str(key), max_length=200)
            if isinstance(value, str):
                result[clean_key] = cls.sanitize_string(value, max_length=10000)
            elif isinstance(value, dict):
                result[clean_key] = cls.sanitize_dict(value, max_depth=max_depth - 1)
            elif isinstance(value, list):
                result[clean_key] = [
                    cls.sanitize_string(str(v), max_length=10000) if isinstance(v, str)
                    else cls.sanitize_dict(v, max_depth=max_depth - 1) if isinstance(v, dict)
                    else v
                    for v in value[:1000]
                ]
            else:
                result[clean_key] = value
        return result
