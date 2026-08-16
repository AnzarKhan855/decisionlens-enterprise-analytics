from pathlib import Path
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.models import Base

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def create_tables():
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        for col_def in [
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS user_id INTEGER",
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER DEFAULT 0",
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'Analyzed'",
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS tags VARCHAR DEFAULT ''",
            "ALTER TABLE datasets ALTER COLUMN user_id SET NOT NULL",
            "ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS ck_user_role CHECK (role IN ('ADMIN', 'ANALYST', 'USER'))",
            "ALTER TABLE datasets ADD CONSTRAINT IF NOT EXISTS ck_dataset_status CHECK (status IN ('Uploaded', 'Analyzing', 'Analyzed', 'Error'))",
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_datasets_uploaded_at ON datasets (uploaded_at)"
        ]:
            try:
                conn.execute(text(col_def))
                conn.commit()
            except Exception:
                pass
