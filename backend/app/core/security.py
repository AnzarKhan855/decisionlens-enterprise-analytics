import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional
from dotenv import load_dotenv

SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("JWT_SECRET") or "dev_default_secret_key_decisionlens_2026_secure"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 86400

PASSWORD_SALT = os.environ.get("PASSWORD_SALT") or os.environ.get("JWT_SALT") or "dev_default_password_salt_decisionlens_2026_secure"

if os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod"):
    if "dev_default" in SECRET_KEY or "dev_default" in PASSWORD_SALT:
        import logging
        logging.getLogger(__name__).warning("SECURITY WARNING: Running in production using development fallback keys. Please configure SECRET_KEY and PASSWORD_SALT environment variables!")


class SecurityManager:
    """
    Enterprise Authentication & Security Manager.
    Handles secure password hashing (PBKDF2-HMAC-SHA256) and JWT token generation/verification.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            PASSWORD_SALT.encode("utf-8"),
            100000
        )
        return key.hex()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return SecurityManager.hash_password(plain_password) == hashed_password

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _base64url_decode(data_str: str) -> bytes:
        padding = 4 - (len(data_str) % 4)
        if padding != 4:
            data_str += "=" * padding
        return base64.urlsafe_b64decode(data_str.encode("utf-8"))

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
        header = {"alg": ALGORITHM, "typ": "JWT"}
        payload = data.copy()
        payload["exp"] = int(time.time()) + expires_in

        header_b64 = SecurityManager._base64url_encode(json.dumps(header).encode("utf-8"))
        payload_b64 = SecurityManager._base64url_encode(json.dumps(payload).encode("utf-8"))

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        signature_b64 = SecurityManager._base64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts
            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()

            if SecurityManager._base64url_encode(expected_sig) != signature_b64:
                return None

            payload_bytes = SecurityManager._base64url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))

            if payload.get("exp", 0) < time.time():
                return None  # Token Expired

            return payload
        except Exception:
            return None
