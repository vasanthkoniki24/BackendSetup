# services/otp_service.py
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from core.config import settings
from core.security import (
    generate_otp,
    create_otp_token,
    decode_otp_token,
)
from core.cookies import (
    set_otp_token_cookie,
    get_otp_token_from_cookie,
    clear_otp_token_cookie,
)
from core.email import email_service
from core.exceptions import (
    TokenMissingError,
    TokenInvalidError,
    TokenExpiredError,
    OTPInvalidError,
    OTPExpiredError,
    OTPMaxRetryError,
    OTPCooldownError,
    OTPAlreadyVerifiedError,
    AccountNotFoundError,
)
from models.otp_verification import OTPVerification, OTPPurpose
from models.user import User
from schemas.response import MessageResponse

logger = logging.getLogger(__name__)


class OTPService:
    """
    Handles all OTP lifecycle operations.

    Responsibilities:
    - OTP generation and storage
    - OTP validation with retry tracking
    - OTP resend with cooldown enforcement
    - OTP JWT cookie extraction and validation
    - Coordinating with AuthService for post-verification actions

    Security model:
    - Email is NEVER taken from request body during verify/resend
    - Email is always extracted from OTP JWT in HTTP-only cookie
    - Retry counter blocks brute force after OTP_MAX_RETRY attempts
    - Cooldown prevents OTP spam on resend
    - Old OTPs are invalidated on resend (only latest is valid)
    """

    # ─── Cookie + JWT Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_otp_jwt_from_cookie(request) -> str:
        """
        Extract OTP JWT string from HTTP-only cookie.
        Raises TokenMissingError if cookie is absent.
        """
        token = get_otp_token_from_cookie(request)
        if not token:
            raise TokenMissingError("otp_token")
        return token

    @staticmethod
    def _decode_and_validate_otp_jwt(token: str) -> dict:
        """
        Decode OTP JWT and return payload.

        Validates:
        - Signature integrity
        - Token type = 'otp'
        - Not expired

        Returns payload dict with 'sub' (email) and 'purpose' claims.
        """
        try:
            payload = decode_otp_token(token)
        except TokenExpiredError:
            raise TokenExpiredError()
        except Exception:
            raise TokenInvalidError()

        email = payload.get("sub")
        purpose = payload.get("purpose")

        if not email or not purpose:
            raise TokenInvalidError()

        return payload

    # ─── OTP DB Helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def _get_latest_otp_record(
        db: AsyncSession,
        email: str,
        purpose: OTPPurpose,
    ) -> Optional[OTPVerification]:
        """
        Fetch the most recent OTP record for a given email + purpose.
        Returns None if no record found.
        """
        result = await db.execute(
            select(OTPVerification)
            .where(
                OTPVerification.email == email.lower().strip(),
                OTPVerification.purpose == purpose,
            )
            .order_by(OTPVerification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _invalidate_existing_otps(
        db: AsyncSession,
        email: str,
        purpose: OTPPurpose,
    ) -> None:
        """
        Mark all existing OTP records for this email + purpose as verified=True.
        Effectively invalidates them before issuing a new OTP.
        Called on resend to ensure only the latest OTP is valid.
        """
        await db.execute(
            update(OTPVerification)
            .where(
                OTPVerification.email == email.lower().strip(),
                OTPVerification.purpose == purpose,
                OTPVerification.verified == False,
            )
            .values(verified=True)
        )
        logger.debug(
            f"Invalidated existing OTPs for "
            f"email={email} purpose={purpose.value}"
        )

    @staticmethod
    async def _create_otp_record(
        db: AsyncSession,
        email: str,
        purpose: OTPPurpose,
    ) -> tuple[str, OTPVerification]:
        """
        Generate a new OTP and persist it to DB.

        Returns:
            (otp_plain_text, OTPVerification record)

        otp_plain_text is used for email sending only —
        never stored in plaintext anywhere else.
        """
        otp = generate_otp()

        otp_record = OTPVerification(
            email=email.lower().strip(),
            otp=otp,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(
                minutes=settings.OTP_TOKEN_EXPIRE_MINUTES
            ),
            verified=False,
            retry_count=0,
        )
        db.add(otp_record)
        await db.flush()

        logger.info(
            f"OTP record created: email={email} "
            f"purpose={purpose.value} "
            f"expires_at={otp_record.expires_at}"
        )

        return otp, otp_record

    # ─── OTP Verification ─────────────────────────────────────────────────────

    @staticmethod
    async def verify_registration_otp(
        db: AsyncSession,
        response: Response,
        request,
        otp_input: str,
    ) -> None:
        """
        Verify OTP for registration flow.

        Flow:
        1. Extract + decode OTP JWT from cookie
        2. Validate purpose = 'registration'
        3. Fetch latest OTP record from DB
        4. Run all OTP validations
        5. Mark OTP as verified
        6. Return email to caller (AuthService.activate_account)

        Returns email string — caller handles account activation.
        This keeps OTPService single-responsibility.
        """
        email = await OTPService._validate_otp_from_cookie(
            db=db,
            request=request,
            otp_input=otp_input,
            expected_purpose=OTPPurpose.REGISTRATION,
        )
        return email

    @staticmethod
    async def verify_forgot_password_otp(
        db: AsyncSession,
        response: Response,
        request,
        otp_input: str,
    ) -> str:
        """
        Verify OTP for forgot password flow.

        Same validation as registration but:
        - purpose must = 'forgot_password'
        - After verification: issue a short-lived reset OTP JWT
          so the reset-password endpoint can confirm OTP was verified

        Returns email string — caller handles password reset.
        """
        email = await OTPService._validate_otp_from_cookie(
            db=db,
            request=request,
            otp_input=otp_input,
            expected_purpose=OTPPurpose.FORGOT_PASSWORD,
        )

        # Issue a new OTP JWT with purpose='forgot_password'
        # so reset-password endpoint can confirm OTP was verified
        # We reuse otp_token cookie — it gets overwritten with same purpose
        reset_token = create_otp_token(
            email=email,
            purpose=OTPPurpose.FORGOT_PASSWORD.value,
        )
        set_otp_token_cookie(response, reset_token)

        logger.info(
            f"Forgot password OTP verified for email={email}. "
            f"Reset token cookie set."
        )

        return email

    @staticmethod
    async def _validate_otp_from_cookie(
        db: AsyncSession,
        request,
        otp_input: str,
        expected_purpose: OTPPurpose,
    ) -> str:
        """
        Core OTP validation logic — shared by registration and forgot password.

        Validation sequence (order matters):
        1. Extract OTP JWT from cookie
        2. Decode JWT — raises on expired/invalid
        3. Validate purpose matches expected
        4. Fetch latest OTP record from DB
        5. Check OTP record exists
        6. Check retry limit FIRST (before expiry — prevents timing attacks)
        7. Check already verified (replay guard)
        8. Check expiry
        9. Compare OTP value
        10. Mark as verified on success
        11. Increment retry_count on failure

        Returns email on success.
        Raises specific OTP exceptions on each failure mode.
        """
        # 1. Extract JWT from cookie
        token = OTPService._extract_otp_jwt_from_cookie(request)

        # 2. Decode JWT
        payload = OTPService._decode_and_validate_otp_jwt(token)

        email: str = payload.get("sub")
        purpose_str: str = payload.get("purpose")

        # 3. Validate purpose
        try:
            purpose = OTPPurpose(purpose_str)
        except ValueError:
            raise TokenInvalidError()

        if purpose != expected_purpose:
            logger.warning(
                f"OTP purpose mismatch: expected={expected_purpose.value} "
                f"got={purpose_str} email={email}"
            )
            raise TokenInvalidError()

        # 4. Fetch OTP record
        otp_record = await OTPService._get_latest_otp_record(
            db, email, purpose
        )

        # 5. Record must exist
        if not otp_record:
            logger.warning(
                f"No OTP record found for email={email} "
                f"purpose={purpose.value}"
            )
            raise OTPInvalidError()

        # 6. Retry limit check (BEFORE expiry — order is intentional)
        #    Checking expiry first would allow unlimited retries on expired OTPs
        if otp_record.retry_count >= settings.OTP_MAX_RETRY:
            logger.warning(
                f"OTP max retry exceeded: email={email} "
                f"retries={otp_record.retry_count}"
            )
            raise OTPMaxRetryError()

        # 7. Replay guard
        if otp_record.verified:
            logger.warning(
                f"Already-verified OTP reuse attempt: email={email}"
            )
            raise OTPAlreadyVerifiedError()

        # 8. Expiry check
        if otp_record.is_expired:
            logger.warning(
                f"Expired OTP attempt: email={email} "
                f"expired_at={otp_record.expires_at}"
            )
            raise OTPExpiredError()

        # 9. OTP value comparison
        if otp_record.otp != otp_input.strip():
            # Increment retry counter
            otp_record.retry_count += 1
            await db.flush()

            remaining = settings.OTP_MAX_RETRY - otp_record.retry_count
            logger.warning(
                f"Invalid OTP attempt: email={email} "
                f"retries={otp_record.retry_count} "
                f"remaining={remaining}"
            )
            raise OTPInvalidError()

        # 10. Mark as verified — prevents replay
        otp_record.verified = True
        await db.flush()

        logger.info(
            f"OTP verified successfully: email={email} "
            f"purpose={purpose.value}"
        )

        return email

    # ─── OTP Resend ───────────────────────────────────────────────────────────

    @staticmethod
    async def resend_otp(
        db: AsyncSession,
        response: Response,
        request,
    ) -> MessageResponse:
        """
        Resend OTP for registration or forgot password.

        Flow:
        1. Extract + decode OTP JWT from cookie
        2. Validate user/email exists and is appropriate
        3. Enforce cooldown (OTP_RESEND_COOLDOWN_SECONDS)
        4. Invalidate all existing OTPs for this email + purpose
        5. Generate and store new OTP
        6. Generate new OTP JWT and refresh cookie
        7. Send OTP email
        8. Return success message

        Security:
        - Email sourced from cookie — never from request body
        - Cooldown prevents OTP spam
        - Old OTPs invalidated immediately on resend
        """
        # 1. Extract + decode JWT from cookie
        token = OTPService._extract_otp_jwt_from_cookie(request)
        payload = OTPService._decode_and_validate_otp_jwt(token)

        email: str = payload.get("sub").lower().strip()
        purpose_str: str = payload.get("purpose")

        try:
            purpose = OTPPurpose(purpose_str)
        except ValueError:
            raise TokenInvalidError()

        # 2. Validate email has a user (for registration: user exists but inactive)
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user: Optional[User] = result.scalar_one_or_none()

        if not user:
            raise AccountNotFoundError()

        # 3. Cooldown check — look at most recent OTP record
        latest_otp = await OTPService._get_latest_otp_record(
            db, email, purpose
        )

        if latest_otp:
            elapsed = (
                datetime.now(timezone.utc) - latest_otp.created_at
            ).total_seconds()

            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                remaining_seconds = int(
                    settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed
                )
                logger.warning(
                    f"OTP resend cooldown active: email={email} "
                    f"remaining={remaining_seconds}s"
                )
                raise OTPCooldownError(seconds=remaining_seconds)

        # 4. Invalidate all existing OTPs
        await OTPService._invalidate_existing_otps(db, email, purpose)

        # 5. Generate new OTP and store
        otp, _ = await OTPService._create_otp_record(db, email, purpose)

        # 6. Generate new OTP JWT and refresh cookie
        new_otp_token = create_otp_token(
            email=email,
            purpose=purpose.value,
        )
        set_otp_token_cookie(response, new_otp_token)

        # 7. Send email
        try:
            email_service.send_resend_otp(
                to_email=email,
                full_name=user.full_name,
                otp=otp,
                purpose=purpose.value,
            )
            logger.info(
                f"OTP resent successfully: email={email} "
                f"purpose={purpose.value}"
            )
        except RuntimeError as e:
            logger.error(
                f"Failed to send resend OTP email to {email}: {e}"
            )

        return MessageResponse(
            message=(
                f"A new OTP has been sent to your email. "
                f"Valid for {settings.OTP_TOKEN_EXPIRE_MINUTES} minutes."
            )
        )