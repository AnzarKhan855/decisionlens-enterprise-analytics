from pathlib import Path
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.models import Base

from app.logging.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./decisionlens.db"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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

    db_type = engine.name
    masked_url = str(engine.url).split('@')[-1] if '@' in str(engine.url) else str(engine.url)
    logger.info(f"[AUTH DB] database_type={db_type}")
    logger.info(f"[AUTH DB] database_identifier={masked_url}")

    with engine.connect() as conn:
        # SQLite schema migration for users table role constraint update
        if engine.name == "sqlite":
            try:
                res = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
                sql_str = res[0] if res and res[0] else ""
                table_exists = bool(res and res[0])
                logger.info(f"[AUTH DB] users_table_exists={table_exists}")
                
                migration_needed = bool(sql_str and ("EMPLOYEE" not in sql_str or "SUPER_ADMIN" not in sql_str))
                logger.info(f"[AUTH DB] role_migration_required={migration_needed}")

                if migration_needed:
                    logger.info("[AUTH DB] role_migration_started=true")
                    count_before = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
                    logger.info(f"[AUTH DB] existing_user_count={count_before}")

                    conn.execute(text("PRAGMA foreign_keys=OFF;"))
                    conn.execute(text("DROP TABLE IF EXISTS users_new;"))
                    conn.execute(text("""
                        CREATE TABLE users_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email VARCHAR UNIQUE NOT NULL,
                            hashed_password VARCHAR NOT NULL,
                            full_name VARCHAR NOT NULL,
                            organization VARCHAR DEFAULT 'Enterprise Corp',
                            role VARCHAR DEFAULT 'USER' NOT NULL CHECK (role IN ('SUPER_ADMIN', 'ORGANIZATION_ADMIN', 'EMPLOYEE', 'ADMIN', 'ANALYST', 'USER')),
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    conn.execute(text("""
                        INSERT INTO users_new (id, email, hashed_password, full_name, organization, role, created_at)
                        SELECT id, email, hashed_password, full_name, organization, role, created_at FROM users;
                    """))
                    conn.execute(text("DROP TABLE users;"))
                    conn.execute(text("ALTER TABLE users_new RENAME TO users;"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);"))
                    conn.execute(text("PRAGMA foreign_keys=ON;"))
                    conn.commit()

                    count_after = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
                    logger.info("[AUTH DB] role_migration_completed=true")
                    logger.info(f"[AUTH DB] final_user_count={count_after}")
                    logger.info("[AUTH DB] employee_role_supported=true")
                else:
                    count_current = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
                    logger.info(f"[AUTH DB] existing_user_count={count_current}")
                    logger.info("[AUTH DB] role_migration_completed=true")
                    logger.info(f"[AUTH DB] final_user_count={count_current}")
                    logger.info("[AUTH DB] employee_role_supported=true")
            except Exception as mig_err:
                logger.error(f"[AUTH DB] role_migration_completed=false ERROR={mig_err}", exc_info=True)

        elif engine.name == "postgresql":
            try:
                conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_user_role;"))
                conn.execute(text("ALTER TABLE users ADD CONSTRAINT ck_user_role CHECK (role IN ('SUPER_ADMIN', 'ORGANIZATION_ADMIN', 'EMPLOYEE', 'ADMIN', 'ANALYST', 'USER'));"))
                conn.commit()
                logger.info("[AUTH DB] PostgreSQL users table role constraint updated successfully.")
                logger.info("[AUTH DB] employee_role_supported=true")
            except Exception as pg_err:
                logger.warning(f"[AUTH DB WARNING] PostgreSQL constraint update warning: {pg_err}")

        for col_def in [
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS user_id INTEGER",
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER DEFAULT 0",
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'Analyzed'",
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS tags VARCHAR DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS ix_datasets_uploaded_at ON datasets (uploaded_at)"
        ]:
            try:
                conn.execute(text(col_def))
                conn.commit()
            except Exception:
                pass
