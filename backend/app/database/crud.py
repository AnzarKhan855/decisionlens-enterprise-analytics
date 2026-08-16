from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models import Dataset, User, OTPToken, PasswordResetToken
from datetime import datetime, timedelta


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower()).first()


def create_user(
    db: Session,
    email: str,
    hashed_password: str,
    full_name: str,
    role: str = "EMPLOYEE",
    organization: str = "Enterprise Corp"
) -> User:
    user = User(
        email=email.lower(),
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        organization=organization
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_dataset(
    db: Session,
    filename: str,
    file_path: str,
    dataset_type: str,
    rows: int,
    columns: int,
    file_type: str,
    user_id: Optional[int] = None,
    file_size_bytes: int = 0
):
    if user_id is None:
        from app.database.models import User
        first_user = db.query(User).first()
        if first_user:
            user_id = first_user.id

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


def create_otp_token(db: Session, email: str, hashed_otp: str, expiry_seconds: int = 300) -> OTPToken:
    expiry = datetime.utcnow() + timedelta(seconds=expiry_seconds)
    token = OTPToken(email=email.lower(), hashed_otp=hashed_otp, expiry=expiry, attempts=0)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_otp_token(db: Session, email: str, hashed_otp: str) -> Optional[OTPToken]:
    now = datetime.utcnow()
    return db.query(OTPToken).filter(
        OTPToken.email == email.lower(),
        OTPToken.hashed_otp == hashed_otp,
        OTPToken.expiry > now,
    ).first()


def invalidate_otp_tokens(db: Session, email: str):
    db.query(OTPToken).filter(OTPToken.email == email.lower()).delete(synchronize_session=False)
    db.commit()


def create_password_reset_token(db: Session, email: str, token: str, expiry_seconds: int = 3600) -> PasswordResetToken:
    expiry = datetime.utcnow() + timedelta(seconds=expiry_seconds)
    reset_token = PasswordResetToken(email=email.lower(), token=token, expiry=expiry)
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def get_valid_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    now = datetime.utcnow()
    return db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.expiry > now,
    ).first()


def invalidate_reset_token(db: Session, token: str):
    db.query(PasswordResetToken).filter(PasswordResetToken.token == token).delete(synchronize_session=False)
    db.commit()
