# services/token_service.py
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from core.cookies import (
    get_refresh_token_from_cookie,
    get_otp_token_from_cookie,
)
from core.security import (
    decode_otp_token,
    decode_refresh_token,
)
from core.exceptions import (
    TokenMissingError,
    TokenInvalidError,
    TokenExpiredError,
    RefreshTokenInvalidError,
)
from models.refresh_token import RefreshToken
from models.user import User

logger = logging.getLogger(__name__)


class TokenService:
    """
    Handles token extraction, validation, and lifecycle management.

    Responsibilities:
    - Extract tokens from HTTP-only cookies
    - Validate OTP JWT for reset password gate
    - Validate refresh token from cookie
    - Clean up expired tokens from DB (maintenance)

    Separation of concerns:
    - AuthService  → issues and uses tokens for auth flows
    - OTPService   → uses OTP tokens for OTP verification flows
    - TokenService → utility layer for token reads and DB maintenance
    """

    # ─── OTP Token Extraction ─────────────────────────────────────────────────

    @staticmethod
    def extract_otp_token_payload(request: Request) -> dict:
        """
        Extract and decode OTP JWT from HTTP-only cookie.

        Used by:
        - reset_password route: validates OTP was verified
          before allowing password change

        Returns full payload dict including 'sub' (email) and 'purpose'.

        Raises:
            TokenMissingError   → cookie not present
            TokenExpiredError   → JWT past exp claim
            TokenInvalidError   → bad signature / wrong type
        """
        raw_token = get_otp_token_from_cookie(request)
        if not raw_token:
            logger.warning("OTP token cookie missing from request")
            raise TokenMissingError("otp_token")

        try:
            payload = decode_otp_token(raw_token)
        except TokenExpiredError:
            logger.warning("OTP token expired")
            raise
        except Exception:
            logger.warning("OTP token invalid")
            raise TokenInvalidError()

        email = payload.get("sub")
        purpose = payload.get("purpose")

        if not email or not purpose:
            raise TokenInvalidError()

        logger.debug(
            f"OTP token extracted: email={email} purpose={purpose}"
        )

        return payload

    @staticmethod
    def extract_email_from_otp_cookie(
        request: Request,
        expected_purpose: str,
    ) -> str:
        """
        Extract and validate email from OTP cookie for a specific purpose.

        Convenience wrapper around extract_otp_token_payload.
        Validates purpose matches before returning email.

        Args:
            request: FastAPI request object
            expected_purpose: 'registration' | 'forgot_password'

        Returns:
            email string from JWT sub claim

        Raises:
            TokenMissingError   → no OTP cookie
            TokenExpiredError   → cookie expired
            TokenInvalidError   → wrong purpose or invalid token
        """
        payload = TokenService.extract_otp_token_payload(request)

        purpose = payload.get("purpose")
        if purpose != expected_purpose:
            logger.warning(
                f"OTP purpose mismatch in cookie: "
                f"expected={expected_purpose} got={purpose}"
            )
            raise TokenInvalidError()

        email: str = payload.get("sub")
        return email.lower().strip()

    # ─── Refresh Token Extraction ─────────────────────────────────────────────

    @staticmethod
    def extract_refresh_token_from_cookie(request: Request) -> str:
        """
        Extract raw refresh token JWT string from HTTP-only cookie.

        Returns raw token string — does NOT decode or validate.
        Validation is done by AuthService.refresh_access_token.

        Raises:
            TokenMissingError → refresh_token cookie not present
        """
        raw_token = get_refresh_token_from_cookie(request)
        if not raw_token:
            logger.warning("Refresh token cookie missing from request")
            raise TokenMissingError("refresh_token")

        return raw_token

    @staticmethod
    def extract_refresh_token_optional(request: Request) -> Optional[str]:
        """
        Extract refresh token from cookie — returns None if absent.
        Used by logout (which should succeed even if token missing).
        """
        return get_refresh_token_from_cookie(request)

    # ─── Refresh Token DB Validation ─────────────────────────────────────────

    @staticmethod
    async def validate_refresh_token_in_db(
        db: AsyncSession,
        token: str,
    ) -> Optional[RefreshToken]:
        """
        Check refresh token exists in DB and is valid:
        - Not revoked
        - Not expired

        Returns RefreshToken record or None.
        Does NOT raise — caller decides action on None.
        """
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_token(
        db: AsyncSession,
        token: str,
    ) -> bool:
        """
        Revoke a specific refresh token by token string.

        Returns True if token was found and revoked.
        Returns False if token not found or already revoked.
        """
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.is_revoked == False,
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            return False

        db_token.is_revoked = True
        await db.flush()

        logger.info(f"Refresh token revoked: token_id={db_token.id}")
        return True

    @staticmethod
    async def revoke_all_user_tokens(
        db: AsyncSession,
        user_id: str,
    ) -> int:
        """
        Revoke ALL active refresh tokens for a user.

        Used by:
        - Password reset (force re-login on all devices)
        - Admin: force logout all sessions

        Returns count of revoked tokens.
        """
        result = await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            )
            .values(is_revoked=True)
            .returning(RefreshToken.id)
        )
        revoked_ids = result.fetchall()
        count = len(revoked_ids)

        if count:
            logger.info(
                f"Revoked {count} refresh token(s) "
                f"for user_id={user_id}"
            )

        return count

    # ─── Token Cleanup (Maintenance) ──────────────────────────────────────────

    @staticmethod
    async def purge_expired_refresh_tokens(
        db: AsyncSession,
    ) -> int:
        """
        Delete expired refresh tokens from DB.

        Should be called periodically via:
        - Background task (APScheduler / Celery beat)
        - Startup event (for small apps)
        - Dedicated maintenance endpoint (admin only)

        Returns count of deleted records.
        """
        result = await db.execute(
            delete(RefreshToken)
            .where(
                RefreshToken.expires_at < datetime.now(timezone.utc),
            )
            .returning(RefreshToken.id)
        )
        deleted_ids = result.fetchall()
        count = len(deleted_ids)

        if count:
            logger.info(
                f"Purged {count} expired refresh token(s) from DB"
            )

        return count

    @staticmethod
    async def purge_expired_otp_records(
        db: AsyncSession,
    ) -> int:
        """
        Delete expired OTP records from DB.

        Keeps the otp_verifications table lean.
        Safe to run periodically — expired OTPs are already unusable.

        Returns count of deleted records.
        """
        from models.otp_verification import OTPVerification

        result = await db.execute(
            delete(OTPVerification)
            .where(
                OTPVerification.expires_at < datetime.now(timezone.utc),
            )
            .returning(OTPVerification.id)
        )
        deleted_ids = result.fetchall()
        count = len(deleted_ids)

        if count:
            logger.info(
                f"Purged {count} expired OTP record(s) from DB"
            )

        return count

    @staticmethod
    async def get_active_session_count(
        db: AsyncSession,
        user_id: str,
    ) -> int:
        """
        Count active (non-revoked, non-expired) refresh tokens for a user.
        Represents number of active sessions across devices.

        Useful for:
        - Profile page: "You have X active sessions"
        - Admin: session monitoring
        """
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        tokens = result.scalars().all()
        return len(tokens)