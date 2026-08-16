import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "DecisionLens Enterprise Decision Intelligence"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./decisionlens.db")

    JWT_SECRET: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", ""))
    OTP_SECRET: str = os.getenv("OTP_SECRET", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "").strip()
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev").strip()

    SUPER_ADMIN_EMAIL: str = os.getenv("SUPER_ADMIN_EMAIL", "").strip().lower()
    SUPER_ADMIN_ROLE: str = os.getenv("SUPER_ADMIN_ROLE", "SUPER_ADMIN").strip().upper()
    SUPER_ADMIN_PASSWORD: str = os.getenv("SUPER_ADMIN_PASSWORD", "").strip()

    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()

    @classmethod
    def get_masked_resend_key(cls) -> str:
        key = cls.RESEND_API_KEY
        if not key or len(key) < 10:
            return "UNCONFIGURED"
        return f"{key[:6]}...{key[-5:]}"

    @classmethod
    def validate(cls) -> List[str]:
        missing = []
        if not cls.JWT_SECRET:
            missing.append("JWT_SECRET")
        if not cls.OTP_SECRET:
            missing.append("OTP_SECRET")
        if not cls.SUPER_ADMIN_EMAIL:
            missing.append("SUPER_ADMIN_EMAIL")
        if not cls.SUPER_ADMIN_PASSWORD:
            missing.append("SUPER_ADMIN_PASSWORD")
        return missing


settings = Settings()
