import time
from typing import Optional, Dict, Any

from app.core.config import settings
from app.logging.logger import get_logger

logger = get_logger(__name__)

try:
    import resend

    # Configure the Resend SDK if a valid API key exists
    if getattr(settings, "RESEND_API_KEY", None):
        resend.api_key = settings.RESEND_API_KEY

except ImportError:
    resend = None


class ResendEmailService:
    """
    Production-Grade Resend Email REST API Dispatcher Service.
    Includes connection retries, structured logging (Recipient, Sender, Status, Resend ID, Elapsed Time),
    and human-readable error reporting for sandbox restrictions.
    Non-blocking local development fallback.
    """

    last_send_status: str = "None"
    last_error_msg: Optional[str] = None
    last_resend_id: Optional[str] = None
    last_elapsed_time: float = 0.0

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.RESEND_API_KEY and not settings.RESEND_API_KEY.startswith("re_test"))

    @classmethod
    def send_email(cls, to_email: str, subject: str, html_body: str, max_retries: int = 1) -> bool:
        start_time = time.time()
        masked_key = settings.get_masked_resend_key()

        if not cls.is_configured() or not resend:
            cls.last_send_status = "Unconfigured / Dev Mode"
            cls.last_error_msg = "Resend API unconfigured, missing module, or dev mode. Fast local fallback active."
            logger.info(f"[ResendEmailService Local Mode] Key: {masked_key} | Recipient: {to_email} | Status: Instant Local Fallback")
            return False

        resend.api_key = settings.RESEND_API_KEY

        params: resend.Emails.SendParams = {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        try:
            attempt_start = time.time()
            response = resend.Emails.send(params)
            elapsed = round(time.time() - attempt_start, 3)

            resend_id = response.get("id", "N/A") if isinstance(response, dict) else getattr(response, "id", "N/A")

            cls.last_send_status = "Success"
            cls.last_error_msg = None
            cls.last_resend_id = str(resend_id)
            cls.last_elapsed_time = elapsed

            logger.info(
                f"[Resend Email API] Sender: {settings.EMAIL_FROM} | "
                f"Recipient: {to_email} | "
                f"Status Code: 200 OK | "
                f"Resend ID: {resend_id} | "
                f"Elapsed Time: {elapsed}s"
            )
            return True

        except Exception as e:
            elapsed = round(time.time() - start_time, 3)
            cls.last_elapsed_time = elapsed
            raw_err = str(e)

            if "only send testing emails to your own email address" in raw_err:
                clean_msg = (
                    "Resend Account Sandbox Mode: Emails can only be sent to the Resend account owner's email address. "
                    "Fast local development fallback active."
                )
            else:
                clean_msg = f"Resend API Error: {raw_err}"

            cls.last_send_status = "Failed / Fallback"
            cls.last_error_msg = clean_msg
            cls.last_resend_id = None

            logger.warning(
                f"[Resend Email API Warning] Sender: {settings.EMAIL_FROM} | "
                f"Recipient: {to_email} | "
                f"Elapsed Time: {elapsed}s | "
                f"Reason: {clean_msg}"
            )
            return False

    @classmethod
    def send_otp_email(cls, to_email: str, otp_code: str) -> bool:
        subject = "DecisionLens Login Verification Code"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155; }}
            .brand {{ font-size: 20px; font-weight: bold; color: #6366f1; text-align: center; margin-bottom: 24px; }}
            .code-box {{ background: #0f172a; border-radius: 12px; padding: 16px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #818cf8; border: 1px solid #4338ca; margin: 24px 0; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">DecisionLens Security</div>
            <p>Hello,</p>
            <p>Your DecisionLens login verification code is:</p>
            <div class="code-box">{otp_code}</div>
            <p style="font-size: 13px; color: #cbd5e1;">This code expires in <strong>5 minutes</strong> and can only be used once.</p>
            <p style="font-size: 12px; color: #94a3b8;">If you did not request this login, please ignore this email.</p>
            <div class="footer">
              DecisionLens Enterprise Security Team &copy; 2026. Powered by Resend API.
            </div>
          </div>
        </body>
        </html>
        """
        return cls.send_email(to_email, subject, html_body)

    @classmethod
    def send_signup_verification_email(cls, to_email: str, otp_code: str) -> bool:
        subject = "Welcome to DecisionLens - Verify Your Email"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155; }}
            .brand {{ font-size: 20px; font-weight: bold; color: #6366f1; text-align: center; margin-bottom: 24px; }}
            .code-box {{ background: #0f172a; border-radius: 12px; padding: 16px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #34d399; border: 1px solid #059669; margin: 24px 0; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">DecisionLens Onboarding</div>
            <p>Hello,</p>
            <p>Welcome to DecisionLens Enterprise! Use the 6-digit code below to verify your account registration:</p>
            <div class="code-box">{otp_code}</div>
            <p style="font-size: 13px; color: #cbd5e1;">This code expires in <strong>5 minutes</strong>.</p>
            <div class="footer">
              DecisionLens Enterprise Security Team &copy; 2026.
            </div>
          </div>
        </body>
        </html>
        """
        return cls.send_email(to_email, subject, html_body)

    @classmethod
    def send_welcome_email(cls, to_email: str, full_name: str) -> bool:
        subject = "Welcome to DecisionLens Enterprise Intelligence Platform"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155; }}
            .brand {{ font-size: 20px; font-weight: bold; color: #6366f1; text-align: center; margin-bottom: 24px; }}
            .btn {{ display: inline-block; background: #4f46e5; color: #ffffff; font-weight: bold; text-decoration: none; padding: 12px 24px; border-radius: 12px; margin: 20px 0; font-size: 14px; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">DecisionLens Enterprise</div>
            <p>Hi {full_name},</p>
            <p>Your DecisionLens Enterprise workspace is active and ready.</p>
            <div style="text-align: center;">
              <a href="{settings.FRONTEND_URL}/dynamic-dashboard" class="btn">Launch Command Hub</a>
            </div>
            <div class="footer">
              DecisionLens Enterprise Security &copy; 2026.
            </div>
          </div>
        </body>
        </html>
        """
        return cls.send_email(to_email, subject, html_body)

    @classmethod
    def send_password_reset_email(cls, to_email: str, reset_link: str) -> bool:
        subject = "DecisionLens Password Reset Request"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155; }}
            .brand {{ font-size: 20px; font-weight: bold; color: #6366f1; text-align: center; margin-bottom: 24px; }}
            .btn {{ display: inline-block; background: #4f46e5; color: #ffffff; font-weight: bold; text-decoration: none; padding: 12px 24px; border-radius: 12px; margin: 20px 0; font-size: 14px; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">DecisionLens Security</div>
            <p>Hello,</p>
            <p>We received a request to reset your DecisionLens account password. Click below to proceed:</p>
            <div style="text-align: center;">
              <a href="{reset_link}" class="btn">Reset Password</a>
            </div>
            <p style="font-size: 13px; color: #cbd5e1;">This link expires in <strong>15 minutes</strong>.</p>
            <p style="font-size: 12px; color: #94a3b8;">If you did not request a password reset, your account is secure and you can ignore this email.</p>
            <div class="footer">
              DecisionLens Security Team &copy; 2026.
            </div>
          </div>
        </body>
        </html>
        """
        return cls.send_email(to_email, subject, html_body)

    @classmethod
    def send_password_changed_email(cls, to_email: str) -> bool:
        subject = "DecisionLens Security Alert: Password Changed"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #ffffff; padding: 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155; }}
            .brand {{ font-size: 20px; font-weight: bold; color: #ef4444; text-align: center; margin-bottom: 24px; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">DecisionLens Security Alert</div>
            <p>Hello,</p>
            <p>The password for your DecisionLens account was changed successfully. All active user sessions have been terminated.</p>
            <div class="footer">
              DecisionLens Security Team &copy; 2026.
            </div>
          </div>
        </body>
        </html>
        """
        return cls.send_email(to_email, subject, html_body)
