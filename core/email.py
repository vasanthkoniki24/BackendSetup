# core/email.py
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.config import settings

logger = logging.getLogger(__name__)


# ─── Email Templates ─────────────────────────────────────────────────────────

def _otp_registration_html(otp: str, full_name: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <h2 style="color: #4F46E5;">Verify Your Email</h2>
        <p>Hi <strong>{full_name}</strong>,</p>
        <p>Thanks for registering. Use the OTP below to verify your email address:</p>
        <div style="
            background: #F3F4F6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 24px 0;
        ">
            <span style="
                font-size: 36px;
                font-weight: bold;
                letter-spacing: 8px;
                color: #4F46E5;
            ">{otp}</span>
        </div>
        <p style="color: #6B7280; font-size: 14px;">
            This OTP is valid for <strong>5 minutes</strong>. Do not share it with anyone.
        </p>
        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;" />
        <p style="color: #9CA3AF; font-size: 12px;">
            If you did not create an account, please ignore this email.
        </p>
    </body>
    </html>
    """


def _otp_forgot_password_html(otp: str, full_name: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <h2 style="color: #DC2626;">Password Reset Request</h2>
        <p>Hi <strong>{full_name}</strong>,</p>
        <p>We received a request to reset your password. Use the OTP below:</p>
        <div style="
            background: #FEF2F2;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 24px 0;
        ">
            <span style="
                font-size: 36px;
                font-weight: bold;
                letter-spacing: 8px;
                color: #DC2626;
            ">{otp}</span>
        </div>
        <p style="color: #6B7280; font-size: 14px;">
            This OTP is valid for <strong>5 minutes</strong>.
            If you did not request this, please secure your account immediately.
        </p>
        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;" />
        <p style="color: #9CA3AF; font-size: 12px;">
            Never share your OTP with anyone, including our support team.
        </p>
    </body>
    </html>
    """


def _otp_resend_html(otp: str, full_name: str, purpose: str) -> str:
    action = "verify your email" if purpose == "registration" else "reset your password"
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
        <h2 style="color: #059669;">New OTP Requested</h2>
        <p>Hi <strong>{full_name}</strong>,</p>
        <p>Here is your new OTP to {action}:</p>
        <div style="
            background: #ECFDF5;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 24px 0;
        ">
            <span style="
                font-size: 36px;
                font-weight: bold;
                letter-spacing: 8px;
                color: #059669;
            ">{otp}</span>
        </div>
        <p style="color: #6B7280; font-size: 14px;">
            This OTP is valid for <strong>5 minutes</strong>.
            Your previous OTP has been invalidated.
        </p>
    </body>
    </html>
    """


# ─── SMTP Sender ─────────────────────────────────────────────────────────────

class EmailService:
    """
    Handles all outgoing email via SMTP.
    Uses TLS (STARTTLS) on port 587.
    """

    @staticmethod
    def _send(
        to_email: str,
        subject: str,
        html_body: str,
    ) -> None:
        """
        Core send method.
        Raises RuntimeError on SMTP failure — caller decides how to handle.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg["To"] = to_email

        part = MIMEText(html_body, "html")
        msg.attach(part)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
                logger.info(f"Email sent to {to_email} | subject: {subject}")
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check SMTP_USER / SMTP_PASSWORD.")
            raise RuntimeError("Email service authentication failed.")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending to {to_email}: {e}")
            raise RuntimeError(f"Failed to send email: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected email error: {e}")
            raise RuntimeError(f"Unexpected email error: {str(e)}")

    @classmethod
    def send_registration_otp(
        cls,
        to_email: str,
        full_name: str,
        otp: str,
    ) -> None:
        cls._send(
            to_email=to_email,
            subject=f"Your Verification OTP — {settings.APP_NAME}",
            html_body=_otp_registration_html(otp, full_name),
        )

    @classmethod
    def send_forgot_password_otp(
        cls,
        to_email: str,
        full_name: str,
        otp: str,
    ) -> None:
        cls._send(
            to_email=to_email,
            subject=f"Password Reset OTP — {settings.APP_NAME}",
            html_body=_otp_forgot_password_html(otp, full_name),
        )

    @classmethod
    def send_resend_otp(
        cls,
        to_email: str,
        full_name: str,
        otp: str,
        purpose: str,
    ) -> None:
        cls._send(
            to_email=to_email,
            subject=f"New OTP — {settings.APP_NAME}",
            html_body=_otp_resend_html(otp, full_name, purpose),
        )


# ─── Module-level convenience functions ──────────────────────────────────────

email_service = EmailService()