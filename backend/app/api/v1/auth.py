import secrets
import time
import hashlib
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header, Depends

from app.core.rbac import get_current_user_from_token
from app.core.config import settings
from app.core.security import SecurityManager
from app.core.rbac import SUPER_ADMIN, ORGANIZATION_ADMIN, EMPLOYEE, normalize_role, ROLES, PERMISSIONS, ROLE_PERMISSIONS
from app.services.email_service import ResendEmailService
from app.database.connection import SessionLocal
from app.database.crud import get_user_by_email, create_user, update_user_password, create_otp_token, get_valid_otp_token, invalidate_otp_tokens, create_password_reset_token, get_valid_reset_token, invalidate_reset_token
from app.database.models import OTPToken, PasswordResetToken
from app.logging.logger import get_logger

logger = get_logger(__name__)


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    organization: Optional[str] = None
    role: Optional[str] = EMPLOYEE


class UserLoginRequest(BaseModel):
    email: str
    password: str


class OTPVerifyRequest(BaseModel):
    email: str
    otp_code: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


router = APIRouter(
    tags=["Authentication & Users"]
)


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    email_clean = body.email.strip().lower()
    user = _get_or_create_user(email_clean)
    if not user:
        return {
            "message": "If an account exists with this email, a password reset link has been sent.",
            "email_sent": False
        }

    reset_token = secrets.token_urlsafe(32)

    db = SessionLocal()
    try:
        invalidate_reset_token(db, email_clean)
        create_password_reset_token(db, email_clean, reset_token, expiry_seconds=3600)
    except Exception as e:
        logger.warning("[Reset Token DB Warning] %s", e)
    finally:
        db.close()

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    is_sent = False
    logger.info(f"[RESET] user_found={bool(user)}")
    logger.info("[RESET] token_persisted=true")
    logger.info("[RESET] email_send_attempted=true")
    try:
        is_sent = ResendEmailService.send_password_reset_email(email_clean, reset_link)
    except Exception as err:
        logger.warning("[Forgot Password Resend API Warning] %s", err)

    logger.info(f"[RESET] provider_accepted={is_sent}")
    logger.info(f"[RESET] provider_message_id_present={bool(ResendEmailService.last_resend_id)}")

    return {
        "message": "If an account exists with this email, a password reset link has been sent.",
        "email_sent": is_sent
    }


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    if not body.reset_token:
        raise HTTPException(status_code=400, detail="Reset token is required.")

    if not body.new_password or len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    db = SessionLocal()
    try:
        record = get_valid_reset_token(db, body.reset_token)
        if not record:
            raise HTTPException(status_code=400, detail="Invalid or expired password reset link. Please request a new link.")

        email = record.email
        hashed = SecurityManager.hash_password(body.new_password)

        updated = update_user_password(db, email, hashed)
        if not updated:
            raise HTTPException(status_code=404, detail="User account not found.")

        invalidate_reset_token(db, body.reset_token)
    finally:
        db.close()

    try:
        ResendEmailService.send_password_changed_email(email)
    except Exception as err:
        logger.warning("[Password Changed Resend API Warning] %s", err)

    return {"message": "Password updated successfully. Please sign in with your new password."}

router = APIRouter(
    tags=["Authentication & Users"]
)

RATE_LIMIT_STORE: Dict[str, float] = {}


def _cleanup_expired_entries() -> None:
    now = time.time()
    expired_rate = [e for e, t in RATE_LIMIT_STORE.items() if now - t > 300]
    for e in expired_rate:
        RATE_LIMIT_STORE.pop(e, None)

    db = SessionLocal()
    try:
        now_utc = datetime.now(UTC)
        db.query(OTPToken).filter(OTPToken.expiry < now_utc).delete(synchronize_session=False)
        db.query(PasswordResetToken).filter(PasswordResetToken.expiry < now_utc).delete(synchronize_session=False)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _get_or_create_user(email: str, password_fallback: Optional[str] = None, role_fallback: str = EMPLOYEE) -> Optional[Dict[str, Any]]:
    email_clean = email.strip().lower()

    if not email_clean or "@" not in email_clean:
        return None

    db = SessionLocal()
    try:
        db_user = get_user_by_email(db, email_clean)
        if not db_user and settings.SUPER_ADMIN_EMAIL and email_clean == settings.SUPER_ADMIN_EMAIL.lower():
            admin_pwd = settings.SUPER_ADMIN_PASSWORD or "admin123"
            hashed = SecurityManager.hash_password(admin_pwd)
            try:
                db_user = create_user(
                    db,
                    email=email_clean,
                    hashed_password=hashed,
                    full_name="Super Administrator",
                    role=SUPER_ADMIN,
                    organization="DecisionLens Enterprise"
                )
                logger.info("[Auto-Seed SUPER_ADMIN] Successfully created SuperAdmin account for %s", email_clean)
            except Exception as seed_err:
                db.rollback()
                logger.warning("[Auto-Seed SUPER_ADMIN Warning] %s", seed_err)
                db_user = get_user_by_email(db, email_clean)

        if db_user:
            user_record = {
                "email": db_user.email,
                "full_name": db_user.full_name,
                "password_hash": db_user.hashed_password,
                "role": normalize_role(db_user.role),
                "organization": db_user.organization or "Enterprise Corp",
                "tenant_id": f"tenant-{email_clean.split('@')[0]}"
            }
            return user_record
    except Exception as e:
        logger.warning("[Auth DB Lookup Warning] %s", e)
    finally:
        db.close()

    return None




@router.get("/email-status")
def get_email_diagnostic_status(user: dict = Depends(get_current_user_from_token)):
    configured = ResendEmailService.is_configured()
    return {
        "resend_api_configured": configured,
        "resend_api_key_masked": settings.get_masked_resend_key(),
        "email_from": settings.EMAIL_FROM,
        "last_send_status": ResendEmailService.last_send_status,
        "last_error_message": ResendEmailService.last_error_msg,
        "last_resend_id": ResendEmailService.last_resend_id,
        "last_elapsed_seconds": ResendEmailService.last_elapsed_time
    }


@router.post("/register")
def register_user(body: UserRegisterRequest):
    email_clean = body.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email format.")

    if not body.password or len(body.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    db = SessionLocal()
    try:
        existing = get_user_by_email(db, email_clean)
        if existing:
            raise HTTPException(status_code=400, detail="User with this email already exists.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Register DB Lookup Warning] %s", e)
    finally:
        db.close()

    org_name = (body.organization or "").strip() or "Default Organization"
    assigned_role = SUPER_ADMIN if email_clean == settings.SUPER_ADMIN_EMAIL.lower() else normalize_role(body.role)
    hashed = SecurityManager.hash_password(body.password)

    user_record = {
        "email": email_clean,
        "full_name": body.full_name,
        "password_hash": hashed,
        "role": assigned_role,
        "organization": org_name,
        "tenant_id": f"tenant-{email_clean.split('@')[0]}"
    }

    db = SessionLocal()
    try:
        new_user = create_user(db, email_clean, hashed, body.full_name, role=assigned_role, organization=org_name)
        if not new_user or not new_user.id:
            raise HTTPException(status_code=500, detail="Database verification failed: User object missing ID.")
        logger.info(f"[REGISTER VERIFIED] User persisted in DB: id={new_user.id}, email={new_user.email}, role={new_user.role}")
    except HTTPException:
        raise
    except Exception as db_err:
        db.rollback()
        logger.error("[Register DB Error] Failed to insert user '%s': %s", email_clean, db_err)
        err_msg = str(db_err)
        if "UNIQUE constraint failed" in err_msg or "already exists" in err_msg.lower():
            raise HTTPException(status_code=409, detail="User with this email address already exists.")
        raise HTTPException(status_code=500, detail=f"Database user creation failed: {err_msg}")
    finally:
        db.close()

    # OTP is ONLY generated for SUPER_ADMIN
    if assigned_role == SUPER_ADMIN:
        raw_otp = f"{secrets.randbelow(900000) + 100000}"
        hashed_otp = hashlib.sha256(raw_otp.encode()).hexdigest()

        db = SessionLocal()
        try:
            create_otp_token(db, email_clean, hashed_otp, expiry_seconds=300)
        except Exception as e:
            logger.warning("[OTP DB Warning] %s", e)
        finally:
            db.close()

        is_sent = False
        try:
            is_sent = ResendEmailService.send_signup_verification_email(email_clean, raw_otp)
        except Exception as err:
            logger.warning("[Register Resend API Warning] %s", err)

        return {
            "message": "Registration initiated. Verification code generated.",
            "otp_required": True,
            "email": email_clean,
            "role": SUPER_ADMIN,
            "email_sent": is_sent
        }

    # For ORGANIZATION_ADMIN and EMPLOYEE -> Immediate JWT registration/login (No OTP)
    access_token = SecurityManager.create_access_token({
        "sub": user_record["email"],
        "role": assigned_role,
        "full_name": user_record["full_name"],
        "tenant_id": user_record["tenant_id"]
    })
    refresh_token = SecurityManager.create_access_token({"sub": user_record["email"], "type": "refresh"})

    return {
        "message": "User registered successfully.",
        "otp_required": False,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": user_record["email"],
            "full_name": user_record["full_name"],
            "role": assigned_role,
            "tenant_id": user_record["tenant_id"]
        }
    }


@router.post("/login")
def login_user(body: UserLoginRequest):
    email_clean = body.email.strip().lower()
    user = _get_or_create_user(email_clean)
    if not user or not SecurityManager.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password credentials.")

    user_role = SUPER_ADMIN if email_clean == settings.SUPER_ADMIN_EMAIL.lower() else normalize_role(user.get("role"))

    # OTP is ONLY generated for SUPER_ADMIN
    if user_role == SUPER_ADMIN:
        now = time.time()
        last_requested = RATE_LIMIT_STORE.get(email_clean, 0)
        if now - last_requested < 5:
            remaining = int(5 - (now - last_requested))
            raise HTTPException(status_code=429, detail=f"Please wait {remaining} seconds before requesting another verification code.")

        RATE_LIMIT_STORE[email_clean] = now

        raw_otp = f"{secrets.randbelow(900000) + 100000}"
        hashed_otp = hashlib.sha256(raw_otp.encode()).hexdigest()

        db = SessionLocal()
        try:
            invalidate_otp_tokens(db, email_clean)
            create_otp_token(db, email_clean, hashed_otp, expiry_seconds=300)
        except Exception as e:
            logger.warning("[OTP DB Warning] %s", e)
        finally:
            db.close()

        is_sent = False
        try:
            is_sent = ResendEmailService.send_otp_email(email_clean, raw_otp)
        except Exception as err:
            logger.warning("[Login Resend API Warning] %s", err)

        logger.info(
            "[DEVELOPMENT OTP GENERATED FOR SUPER_ADMIN] Target Email: %s | Verification Code (OTP): %s",
            email_clean,
            raw_otp,
        )

        return {
            "message": f"Verification code generated for {email_clean}. Code expires in 5 minutes.",
            "otp_required": True,
            "email": email_clean,
            "role": SUPER_ADMIN,
            "expiry_seconds": 300,
            "email_sent": is_sent
        }

    # For ORGANIZATION_ADMIN and EMPLOYEE -> Immediate JWT login (No OTP)
    access_token = SecurityManager.create_access_token({
        "sub": user["email"],
        "role": user_role,
        "full_name": user.get("full_name", email_clean.split("@")[0].title()),
        "tenant_id": user.get("tenant_id", "tenant-001")
    })
    refresh_token = SecurityManager.create_access_token({"sub": user["email"], "type": "refresh"})

    return {
        "message": "Authentication Successful.",
        "otp_required": False,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user_role,
            "organization": user.get("organization"),
            "tenant_id": user.get("tenant_id")
        }
    }


@router.post("/verify-otp")
def verify_otp_code(body: OTPVerifyRequest):
    email_clean = body.email.strip().lower()
    entered_hash = hashlib.sha256(body.otp_code.strip().encode()).hexdigest()

    db = SessionLocal()
    try:
        record = get_valid_otp_token(db, email_clean, entered_hash)
        if not record:
            _cleanup_expired_entries()
            raise HTTPException(status_code=400, detail="No active verification code found. Please request login again.")

        if record.attempts >= 5:
            invalidate_otp_tokens(db, email_clean)
            db.commit()
            raise HTTPException(status_code=429, detail="Maximum verification attempts exceeded. Please request a new code.")

        record.attempts += 1
        db.commit()

        invalidate_otp_tokens(db, email_clean)
        db.commit()
    finally:
        db.close()

    user = _get_or_create_user(email_clean)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    user_role = SUPER_ADMIN if email_clean == settings.SUPER_ADMIN_EMAIL.lower() else normalize_role(user.get("role"))

    access_token = SecurityManager.create_access_token({
        "sub": user["email"],
        "role": user_role,
        "full_name": user.get("full_name"),
        "tenant_id": user.get("tenant_id", "tenant-superadmin")
    })
    refresh_token = SecurityManager.create_access_token({"sub": user["email"], "type": "refresh"})

    try:
        ResendEmailService.send_welcome_email(user["email"], user["full_name"])
    except Exception as err:
        logger.warning("[Welcome Resend API Warning] %s", err)

    return {
        "message": "Enterprise Authentication Successful.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user_role,
            "tenant_id": user.get("tenant_id", "tenant-superadmin")
        }
    }




class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh-token")
def refresh_access_token(body: RefreshTokenRequest):
    payload = SecurityManager.decode_access_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload.")

    user = _get_or_create_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user_role = SUPER_ADMIN if email.lower() == settings.SUPER_ADMIN_EMAIL.lower() else normalize_role(user.get("role"))

    access_token = SecurityManager.create_access_token({
        "sub": user["email"],
        "role": user_role,
        "full_name": user.get("full_name"),
        "tenant_id": user.get("tenant_id", "tenant-001")
    })
    refresh_token = SecurityManager.create_access_token({"sub": user["email"], "type": "refresh"})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user_role,
            "tenant_id": user.get("tenant_id", "tenant-001")
        }
    }


@router.get("/me")
def get_current_user_profile(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Bearer token.")

    token = authorization.split(" ")[1]
    payload = SecurityManager.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token has expired or is invalid.")

    email = payload.get("sub", "").lower()
    user = _get_or_create_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Token may be invalid.")

    user_role = SUPER_ADMIN if email == settings.SUPER_ADMIN_EMAIL.lower() else normalize_role(user.get("role"))

    return {
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user_role,
        "organization": user.get("organization"),
        "tenant_id": user.get("tenant_id")
    }


@router.get("/rbac/matrix")
def get_rbac_permission_matrix():
    return {
        "roles": ROLES,
        "permissions": PERMISSIONS,
        "role_permissions": ROLE_PERMISSIONS
    }


@router.post("/rbac/assign-role")
def assign_user_role(email: str, role: str, user: dict = Depends(get_current_user_from_token)):
    email_clean = email.strip().lower()
    normalized = normalize_role(role)
    target = _get_or_create_user(email_clean)
    if not target:
        raise HTTPException(status_code=404, detail=f"User '{email_clean}' not found.")
    target["role"] = normalized
    return {"status": "success", "email": email_clean, "new_role": normalized}
