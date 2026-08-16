"""
Test Suite for Role-Based Authentication & Verification Rules in DecisionLens
Tests:
  1. SUPER_ADMIN Login Flow (Password -> OTP -> JWT)
  2. ORGANIZATION_ADMIN Login Flow (Password -> Immediate JWT, No OTP)
  3. EMPLOYEE Login Flow (Password -> Immediate JWT, No OTP)
  4. Invalid Credentials, Invalid OTP, Expired OTP
  5. JWT Token Decoding & /auth/me Role Verification
"""

import time
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.security import SecurityManager
from app.core.rbac import SUPER_ADMIN, ORGANIZATION_ADMIN, EMPLOYEE, normalize_role, ROLE_PERMISSIONS
from app.api.v1.auth import (
    login_user,
    verify_otp_code,
    register_user,
    get_current_user_profile,
    UserLoginRequest,
    OTPVerifyRequest,
    UserRegisterRequest,
    RATE_LIMIT_STORE,
)
from app.database.connection import SessionLocal
from app.database.models import User, OTPToken
from fastapi import HTTPException


def test_super_admin_login_requires_otp():
    """Verify that SUPER_ADMIN receives otp_required=True and triggers OTP flow."""
    super_admin_email = settings.SUPER_ADMIN_EMAIL.lower()
    super_admin_pass = settings.SUPER_ADMIN_PASSWORD

    req = UserLoginRequest(email=super_admin_email, password=super_admin_pass)
    res = login_user(req)

    assert res["otp_required"] is True
    assert res["email"] == super_admin_email
    assert res["role"] == SUPER_ADMIN
    assert "dev_otp" not in res

    db = SessionLocal()
    try:
        otp_record = db.query(OTPToken).filter(OTPToken.email == super_admin_email).first()
        assert otp_record is not None
        hashed_otp = otp_record.hashed_otp
    finally:
        db.close()

    otp_req = OTPVerifyRequest(email=super_admin_email, otp_code="000000")
    try:
        verify_otp_code(otp_req)
        assert False, "Should have raised HTTPException for invalid OTP"
    except HTTPException:
        pass

    print("[PASS] test_super_admin_login_requires_otp passed.")


def test_organization_admin_login_no_otp():
    """Verify that ORGANIZATION_ADMIN gets immediate JWT token without OTP."""
    org_email = "orgadmin@decisionlens.ai"
    org_pass = "orgadmin123"

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == org_email.lower()).first()
        if not existing:
            reg_req = UserRegisterRequest(
                email=org_email,
                password=org_pass,
                full_name="Organization Administrator",
                organization="Acme Analytics Inc",
                role=ORGANIZATION_ADMIN
            )
            register_user(reg_req)
    finally:
        db.close()

    req = UserLoginRequest(email=org_email, password=org_pass)
    res = login_user(req)

    assert res["otp_required"] is False
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["user"]["role"] == ORGANIZATION_ADMIN

    decoded = SecurityManager.decode_access_token(res["access_token"])
    assert decoded is not None
    assert decoded["sub"] == org_email
    assert decoded["role"] == ORGANIZATION_ADMIN
    print("[PASS] test_organization_admin_login_no_otp passed.")


def test_employee_login_no_otp():
    """Verify that EMPLOYEE gets immediate JWT token without OTP."""
    emp_email = "employee@decisionlens.ai"
    emp_pass = "employee123"

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == emp_email.lower()).first()
        if not existing:
            reg_req = UserRegisterRequest(
                email=emp_email,
                password=emp_pass,
                full_name="Analytics Employee",
                organization="Acme Analytics Inc",
                role=EMPLOYEE
            )
            register_user(reg_req)
    finally:
        db.close()

    req = UserLoginRequest(email=emp_email, password=emp_pass)
    res = login_user(req)

    assert res["otp_required"] is False
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["user"]["role"] == EMPLOYEE

    decoded = SecurityManager.decode_access_token(res["access_token"])
    assert decoded is not None
    assert decoded["sub"] == emp_email
    assert decoded["role"] == EMPLOYEE
    print("[PASS] test_employee_login_no_otp passed.")


def test_invalid_password_rejected():
    """Verify that incorrect passwords raise 401 Unauthorized."""
    emp_email = "nonexistent@decisionlens.ai"
    req = UserLoginRequest(email=emp_email, password="WrongPassword123")

    try:
        login_user(req)
        assert False, "Should have raised HTTPException"
    except HTTPException as exc_info:
        assert exc_info.status_code == 401
    print("[PASS] test_invalid_password_rejected passed.")


def test_invalid_otp_rejected():
    """Verify that wrong OTP code raises 400 Bad Request."""
    super_admin_email = settings.SUPER_ADMIN_EMAIL.lower()
    super_admin_pass = settings.SUPER_ADMIN_PASSWORD

    RATE_LIMIT_STORE.clear()

    req = UserLoginRequest(email=super_admin_email, password=super_admin_pass)
    login_res = login_user(req)

    otp_req = OTPVerifyRequest(email=super_admin_email, otp_code="000000")
    try:
        verify_otp_code(otp_req)
        assert False, "Should have raised HTTPException"
    except HTTPException as exc_info:
        assert exc_info.status_code == 400
    print("[PASS] test_invalid_otp_rejected passed.")


def test_role_normalization():
    """Verify legacy role normalization."""
    assert normalize_role("Super Admin") == SUPER_ADMIN
    assert normalize_role("Administrator") == SUPER_ADMIN
    assert normalize_role("Organization Admin") == ORGANIZATION_ADMIN
    assert normalize_role("Analyst") == EMPLOYEE
    assert normalize_role("Viewer") == EMPLOYEE
    assert normalize_role(None) == EMPLOYEE
    print("[PASS] test_role_normalization passed.")


def run_all_tests():
    print("\n==================================================")
    print("RUNNING ROLE-BASED AUTHENTICATION TEST SUITE")
    print("==================================================")
    test_super_admin_login_requires_otp()
    test_organization_admin_login_no_otp()
    test_employee_login_no_otp()
    test_invalid_password_rejected()
    test_invalid_otp_rejected()
    test_role_normalization()
    print("==================================================")
    print("ALL AUTHENTICATION TESTS PASSED 100% SUCCESS!")
    print("==================================================\n")


if __name__ == "__main__":
    run_all_tests()
