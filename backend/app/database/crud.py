from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models import Dataset, User, OTPToken, PasswordResetToken
from datetime import UTC, datetime, timedelta, timezone
from app.logging.logger import get_logger

logger = get_logger(__name__)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    email_clean = email.lower().strip()
    # 1. Check local SQLite / PostgreSQL first
    user = db.query(User).filter(User.email == email_clean).first()
    if user:
        return user

    # 2. Check durable MongoDB store (survives container cold-starts and redeploys)
    try:
        from app.database.mongodb import users as mongo_users
        doc = mongo_users.find_one({"email": email_clean})
        if doc:
            stored_id = doc.get("user_id") or doc.get("id")
            user = User(
                email=doc["email"],
                hashed_password=doc["hashed_password"],
                full_name=doc.get("full_name", "Enterprise User"),
                role=doc.get("role", "EMPLOYEE"),
                organization=doc.get("organization", "Enterprise Corp"),
            )
            if stored_id and isinstance(stored_id, int):
                user.id = stored_id
            db.add(user)
            db.commit()
            db.refresh(user)
            if doc.get("user_id") != user.id or doc.get("id") != user.id:
                mongo_users.update_one({"email": email_clean}, {"$set": {"user_id": user.id, "id": user.id}})
            logger.info("[AUTH DB] Re-hydrated user %s from MongoDB into local database (id=%s)", email_clean, user.id)
            return user
    except Exception as mongo_err:
        logger.debug("[MongoDB User Lookup Warning] %s", mongo_err)

    return None


def _get_next_user_id(db: Session) -> int:
    from sqlalchemy import func
    max_sqlite = db.query(func.max(User.id)).scalar() or 0
    max_mongo = 0
    try:
        from app.database.mongodb import users as mongo_users
        highest = mongo_users.find_one(sort=[("user_id", -1)])
        if highest:
            max_mongo = highest.get("user_id") or highest.get("id") or 0
    except Exception:
        pass
    return max(max_sqlite, max_mongo) + 1


def create_user(
    db: Session,
    email: str,
    hashed_password: str,
    full_name: str,
    role: str = "EMPLOYEE",
    organization: str = "Enterprise Corp"
) -> User:
    email_clean = email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        existing_doc = None
        try:
            from app.database.mongodb import users as mongo_users
            existing_doc = mongo_users.find_one({"email": email_clean})
        except Exception:
            pass

        allocated_id = None
        if existing_doc and (existing_doc.get("user_id") or existing_doc.get("id")):
            allocated_id = existing_doc.get("user_id") or existing_doc.get("id")
        else:
            allocated_id = _get_next_user_id(db)

        user = User(
            id=allocated_id,
            email=email_clean,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            organization=organization
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.hashed_password = hashed_password
        user.full_name = full_name
        user.role = role
        user.organization = organization
        db.commit()
        db.refresh(user)

    # Persist durably in MongoDB Atlas
    try:
        from app.database.mongodb import users as mongo_users
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            mongo_users.update_one(
                {"email": email_clean},
                {
                    "$set": {
                        "id": user.id,
                        "user_id": user.id,
                        "email": email_clean,
                        "hashed_password": hashed_password,
                        "full_name": full_name,
                        "role": role,
                        "organization": organization,
                        "updated_at": now_iso,
                    },
                    "$setOnInsert": {
                        "created_at": now_iso,
                    }
                },
                upsert=True
            )
        except Exception as dup_err:
            if "duplicate key" in str(dup_err).lower() and "user_id" in str(dup_err).lower():
                new_id = _get_next_user_id(db)
                user.id = new_id
                db.commit()
                db.refresh(user)
                mongo_users.update_one(
                    {"email": email_clean},
                    {
                        "$set": {
                            "id": new_id,
                            "user_id": new_id,
                            "email": email_clean,
                            "hashed_password": hashed_password,
                            "full_name": full_name,
                            "role": role,
                            "organization": organization,
                            "updated_at": now_iso,
                        },
                        "$setOnInsert": {
                            "created_at": now_iso,
                        }
                    },
                    upsert=True
                )
            else:
                raise
        logger.info("[AUTH DB] Persisted user %s to durable MongoDB store (id=%s)", email_clean, user.id)
    except Exception as mongo_err:
        logger.warning("[MongoDB Auth Persistence Warning] Failed to persist user to MongoDB: %s", mongo_err)

    return user


def update_user_password(db: Session, email: str, new_hashed_password: str) -> bool:
    email_clean = email.lower().strip()
    user = get_user_by_email(db, email_clean)
    success = False
    if user:
        user.hashed_password = new_hashed_password
        db.commit()
        db.refresh(user)
        success = True

    try:
        from app.database.mongodb import users as mongo_users
        mongo_users.update_one(
            {"email": email_clean},
            {"$set": {"hashed_password": new_hashed_password, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        success = True
    except Exception as mongo_err:
        logger.warning("[MongoDB Password Update Warning] %s", mongo_err)

    return success


def save_dataset(
    db: Session,
    filename: str,
    file_path: str,
    dataset_type: str,
    rows: int,
    columns: int,
    file_type: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    file_size_bytes: int = 0
):
    # 1. If user_id is missing but email is provided, resolve directly
    if user_id is None and user_email:
        resolved_user = get_user_by_email(db, user_email)
        if resolved_user:
            user_id = resolved_user.id

    # 2. If user_id is still missing, fallback to existing local user
    if user_id is None:
        first_user = db.query(User).first()
        if first_user:
            user_id = first_user.id
        else:
            # Check MongoDB for any durable user to re-hydrate
            try:
                from app.database.mongodb import users as mongo_users
                m_doc = mongo_users.find_one({})
                if m_doc:
                    rehydrated = get_user_by_email(db, m_doc["email"])
                    if rehydrated:
                        user_id = rehydrated.id
            except Exception:
                pass

    # 3. If database has zero users (e.g. fresh ephemeral start), auto-seed system user so user_id is NEVER null
    if user_id is None:
        from app.core.config import settings
        from app.core.security import SecurityManager
        admin_email = settings.SUPER_ADMIN_EMAIL.lower() if settings.SUPER_ADMIN_EMAIL else "admin@decisionlens.io"
        admin_pwd = settings.SUPER_ADMIN_PASSWORD or "admin123"
        seeded = create_user(
            db,
            email=admin_email,
            hashed_password=SecurityManager.hash_password(admin_pwd),
            full_name="Super Administrator",
            role="SUPER_ADMIN",
            organization="DecisionLens Enterprise"
        )
        user_id = seeded.id
        logger.info("[save_dataset] Auto-seeded admin user (id=%s) to satisfy NOT NULL constraint", user_id)

    dataset = Dataset(
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        dataset_type=dataset_type,
        rows=rows,
        columns=columns,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


def get_latest_dataset(db: Session):
    return (
        db.query(Dataset)
        .order_by(Dataset.uploaded_at.desc())
        .first()
    )


def get_all_datasets(db: Session):
    return (
        db.query(Dataset)
        .order_by(Dataset.uploaded_at.desc())
        .all()
    )


def get_dataset_by_id(db: Session, dataset_id: int):
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def delete_dataset_by_id(db: Session, dataset_id: int):
    ds = get_dataset_by_id(db, dataset_id)
    if ds:
        db.delete(ds)
        db.commit()
        return True
    return False


def delete_dataset_permanently(db: Session, identifier: str, file_paths: Optional[List[str]] = None) -> int:
    """
    Permanently deletes dataset records from SQLite matching ID, filename, file path,
    or an explicit list of file_paths (used for workspace-scoped cleanup where the
    identifier is a workspace slug rather than a dataset filename).
    Returns the count of deleted DB records.
    """
    deleted_count = 0
    if identifier.isdigit():
        ds = get_dataset_by_id(db, int(identifier))
        if ds:
            db.delete(ds)
            deleted_count += 1

    matching = db.query(Dataset).filter(
        (Dataset.filename == identifier) |
        (Dataset.filename.like(f"%{identifier}%")) |
        (Dataset.file_path.like(f"%{identifier}%"))
    ).all()

    for ds in matching:
        db.delete(ds)
        deleted_count += 1

    if file_paths:
        for fp in file_paths:
            path_matches = db.query(Dataset).filter(Dataset.file_path == fp).all()
            for ds in path_matches:
                if ds not in db.deleted:
                    db.delete(ds)
                    deleted_count += 1

    db.commit()
    return deleted_count


def delete_all_datasets(db: Session) -> int:
    """
    Permanently deletes all dataset records from SQLite database.
    Returns the count of deleted DB records.
    """
    deleted_count = db.query(Dataset).delete(synchronize_session=False)
    db.commit()
    return deleted_count


def create_otp_token(db: Session, email: str, hashed_otp: str, expiry_seconds: int = 300) -> OTPToken:
    expiry = datetime.now(UTC) + timedelta(seconds=expiry_seconds)
    token = OTPToken(email=email.lower(), hashed_otp=hashed_otp, expiry=expiry, attempts=0)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_otp_token(db: Session, email: str, hashed_otp: str) -> Optional[OTPToken]:
    now = datetime.now(UTC)
    return db.query(OTPToken).filter(
        OTPToken.email == email.lower(),
        OTPToken.hashed_otp == hashed_otp,
        OTPToken.expiry > now,
    ).first()


def invalidate_otp_tokens(db: Session, email: str):
    db.query(OTPToken).filter(OTPToken.email == email.lower()).delete(synchronize_session=False)
    db.commit()


def create_password_reset_token(db: Session, email: str, token: str, expiry_seconds: int = 3600) -> PasswordResetToken:
    expiry = datetime.now(UTC) + timedelta(seconds=expiry_seconds)
    reset_token = PasswordResetToken(email=email.lower(), token=token, expiry=expiry)
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def get_valid_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    now = datetime.now(UTC)
    return db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expiry > now,
    ).first()


def invalidate_reset_token(db: Session, token: str):
    db.query(PasswordResetToken).filter(PasswordResetToken.token == token).delete(synchronize_session=False)
    db.commit()
