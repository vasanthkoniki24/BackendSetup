# services/auth_service.py
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from core.config import settings
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_otp_token,
    generate_otp,
)
from core.cookies import (
    set_access_token_cookie,
    set_refresh_token_cookie,
    set_otp_token_cookie,
    clear_all_auth_cookies,
    clear_otp_token_cookie,
)
from core.email import email_service
from core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    AccountNotActiveError,
    AccountNotFoundError,
    RefreshTokenInvalidError,
)
from models.user import User, AccountType
from models.tenant import Tenant, TenantStatus
from models.refresh_token import RefreshToken
from models.otp_verification import OTPVerification, OTPPurpose
from schemas.auth import RegisterRequest, LoginRequest
from schemas.response import (
    RegisterResponse,
    TokenResponse,
    MessageResponse,
    mask_email,
)
from schemas.user import UserResponse

logger = logging.getLogger(__name__)


class AuthService:
    """
    Core authentication service.

    Handles:
    - Registration (Individual + Organization)
    - Account activation after OTP verification
    - Tenant auto-creation for Organization accounts
    - Login with credential validation
    - Token issuance and cookie management
    - Refresh token rotation
    - Password reset
    - Logout

    Never raises raw HTTPException — always uses core.exceptions.
    All methods receive db session from route layer.
    db.flush() used instead of commit() — get_db dependency owns commit.
    """

    # ─── DB Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    async def _get_user_by_email(
        db: AsyncSession,
        email: str,
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(
                User.email == email.lower().strip()
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_user_by_id(
        db: AsyncSession,
        user_id: str,
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_active_refresh_token(
        db: AsyncSession,
        token: str,
    ) -> Optional[RefreshToken]:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    # ─── Token + Cookie Issuance ──────────────────────────────────────────────

    @staticmethod
    async def _issue_auth_tokens(
        db: AsyncSession,
        response: Response,
        user: User,
    ) -> None:
        """
        Generate access + refresh tokens and set in HTTP-only cookies.

        Steps:
        1. Create access JWT (15-30 min)
        2. Create refresh JWT (7-30 days)
        3. Persist refresh token to DB
        4. Set both tokens in HTTP-only cookies

        Called by: login, activate_account, refresh_access_token
        """
        # 1. Create tokens
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            account_type=user.account_type.value,
        )
        refresh_token = create_refresh_token(user_id=user.id)

        # 2. Persist refresh token
        db_refresh = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            ),
        )
        db.add(db_refresh)
        await db.flush()

        # 3. Set cookies
        set_access_token_cookie(response, access_token)
        set_refresh_token_cookie(response, refresh_token)

        logger.info(
            f"Auth tokens issued: user_id={user.id} "
            f"account_type={user.account_type.value}"
        )

    # ─── Registration ─────────────────────────────────────────────────────────

    @staticmethod
    async def register(
        db: AsyncSession,
        response: Response,
        payload: RegisterRequest,
    ) -> RegisterResponse:
        """
        Register new user (Individual or Organization).

        Flow:
        1. Check email uniqueness
        2. Hash password
        3. Create User (is_active=False — awaiting OTP)
        4. Generate 6-digit OTP
        5. Store OTPVerification record
           - Includes organization_name for org accounts
             so tenant can be created correctly on activation
        6. Generate OTP JWT (contains email + purpose)
        7. Set OTP JWT in HTTP-only cookie
        8. Send OTP email
        9. Return masked email

        User is NOT active until verify-otp is called.
        Tenant is NOT created until account is activated.
        """
        email = payload.email.lower().strip()

        # 1. Email uniqueness
        existing = await AuthService._get_user_by_email(db, email)
        if existing:
            logger.warning(
                f"Registration with existing email: {email}"
            )
            raise EmailAlreadyExistsError()

        # 2. Hash password
        password_hash = hash_password(payload.password)

        # 3. Create user (inactive)
        user = User(
            full_name=payload.full_name,
            email=email,
            password_hash=password_hash,
            account_type=payload.account_type,
            is_active=False,
        )
        db.add(user)
        await db.flush()

        logger.info(
            f"User created (pending activation): "
            f"user_id={user.id} "
            f"account_type={payload.account_type.value}"
        )

        # 4. Generate OTP
        otp = generate_otp()

        # 5. Store OTP record
        # organization_name stored here so _create_tenant
        # can use the real name on activation
        otp_record = OTPVerification(
            email=email,
            otp=otp,
            purpose=OTPPurpose.REGISTRATION,
            expires_at=datetime.now(timezone.utc) + timedelta(
                minutes=settings.OTP_TOKEN_EXPIRE_MINUTES
            ),
            organization_name=(
                payload.organization_name
                if payload.account_type == AccountType.ORGANIZATION
                else None
            ),
        )
        db.add(otp_record)
        await db.flush()

        # 6. Generate OTP JWT
        otp_token = create_otp_token(
            email=email,
            purpose=OTPPurpose.REGISTRATION.value,
        )

        # 7. Set OTP cookie
        set_otp_token_cookie(response, otp_token)

        # 8. Send OTP email
        try:
            email_service.send_registration_otp(
                to_email=email,
                full_name=payload.full_name,
                otp=otp,
            )
            logger.info(f"Registration OTP sent: email={email}")
        except RuntimeError as e:
            # Email failure does not block registration
            # OTP is in DB — user can use resend-otp
            logger.error(
                f"Failed to send registration OTP to {email}: {e}"
            )

        # 9. Return masked email
        return RegisterResponse(
            message=(
                "Registration successful. "
                "Please check your email for the 6-digit OTP."
            ),
            email_hint=mask_email(email),
        )

    # ─── Account Activation ───────────────────────────────────────────────────

    @staticmethod
    async def activate_account(
        db: AsyncSession,
        response: Response,
        email: str,
    ) -> TokenResponse:
        """
        Activate account after successful OTP verification.

        Called by OTPService after OTP is validated.

        Flow:
        1. Load user
        2. Set is_active = True
        3. If Organization: create Tenant with real organization_name
           fetched from the OTPVerification record
        4. Clear OTP cookie
        5. Issue access + refresh tokens
        6. Return user info

        This is the ONLY place Tenant is created.
        organization_name sourced from OTPVerification.organization_name
        — stored during registration, never from request body.
        """
        email = email.lower().strip()

        # 1. Load user
        user = await AuthService._get_user_by_email(db, email)
        if not user:
            logger.error(
                f"Activation for non-existent user: {email}"
            )
            raise AccountNotFoundError()

        # 2. Activate
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info(
            f"Account activated: user_id={user.id} "
            f"account_type={user.account_type.value}"
        )

        # 3. Create tenant for Organization accounts
        if user.account_type == AccountType.ORGANIZATION:
            await AuthService._create_tenant(db, user, email)

        # 4. Clear OTP cookie
        clear_otp_token_cookie(response)

        # 5. Issue auth tokens
        await AuthService._issue_auth_tokens(db, response, user)

        # 6. Return response
        return TokenResponse(
            message="Account verified and activated successfully.",
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def _create_tenant(
        db: AsyncSession,
        user: User,
        email: str,
    ) -> Optional[Tenant]:
        """
        Auto-create Tenant for Organization account on activation.

        organization_name is fetched from the most recent
        OTPVerification record for this email — stored during registration.

        This avoids adding organization_name to the users table
        and keeps the registration data flow clean.
        """
        # Guard: prevent duplicate tenant
        existing = await db.execute(
            select(Tenant).where(
                Tenant.owner_user_id == user.id
            )
        )
        if existing.scalar_one_or_none():
            logger.warning(
                f"Tenant already exists for user_id={user.id} — skip"
            )
            return None

        # Fetch organization_name from OTP record
        otp_result = await db.execute(
            select(OTPVerification)
            .where(
                OTPVerification.email == email,
                OTPVerification.purpose == OTPPurpose.REGISTRATION,
                OTPVerification.verified == True,
            )
            .order_by(OTPVerification.created_at.desc())
            .limit(1)
        )
        otp_record = otp_result.scalar_one_or_none()

        # Use real org name from OTP record or fall back to user's name
        organization_name = (
            otp_record.organization_name
            if otp_record and otp_record.organization_name
            else f"{user.full_name}'s Organization"
        )

        tenant = Tenant(
            organization_name=organization_name,
            owner_user_id=user.id,
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        logger.info(
            f"Tenant created: tenant_id={tenant.id} "
            f"org={organization_name} "
            f"owner_user_id={user.id}"
        )
        return tenant

    # ─── Login ────────────────────────────────────────────────────────────────

    @staticmethod
    async def login(
        db: AsyncSession,
        response: Response,
        payload: LoginRequest,
    ) -> TokenResponse:
        """
        Authenticate with email + password.

        Flow:
        1. Find user by email
        2. Verify password (bcrypt)
        3. Check is_active
        4. Issue access + refresh tokens in cookies
        5. Return user info

        Security:
        - Same error for wrong email OR wrong password
          (prevents user enumeration attacks)
        - Timing-safe comparison via bcrypt verify
        """
        email = payload.email.lower().strip()

        # 1. Find user
        user = await AuthService._get_user_by_email(db, email)
        if not user:
            logger.warning(
                f"Login attempt: email not found: {email}"
            )
            raise InvalidCredentialsError()

        # 2. Verify password
        if not verify_password(payload.password, user.password_hash):
            logger.warning(
                f"Login attempt: wrong password: user_id={user.id}"
            )
            raise InvalidCredentialsError()

        # 3. Check active
        if not user.is_active:
            logger.warning(
                f"Login attempt: inactive account: user_id={user.id}"
            )
            raise AccountNotActiveError()

        # 4. Issue tokens
        await AuthService._issue_auth_tokens(db, response, user)

        logger.info(f"Login successful: user_id={user.id}")

        # 5. Return response
        return TokenResponse(
            message="Login successful.",
            user=UserResponse.model_validate(user),
        )

    # ─── Forgot Password ──────────────────────────────────────────────────────

    @staticmethod
    async def forgot_password(
        db: AsyncSession,
        response: Response,
        email: str,
    ) -> MessageResponse:
        """
        Initiate forgot password flow.

        Flow:
        1. Look up user (generic response if not found — no enumeration)
        2. Generate OTP
        3. Store OTPVerification (purpose=forgot_password)
        4. Generate OTP JWT
        5. Set OTP cookie
        6. Send email
        7. Return generic message

        Security:
        - Returns same message whether email exists or not
        - Only active accounts can reset password
        """
        email = email.lower().strip()

        # Generic message — do not reveal if email exists
        generic_message = (
            "If an account with this email exists, "
            "you will receive a password reset OTP shortly."
        )

        user = await AuthService._get_user_by_email(db, email)
        if not user or not user.is_active:
            logger.warning(
                f"Forgot password: user not found or inactive: {email}"
            )
            return MessageResponse(message=generic_message)

        # Generate OTP
        otp = generate_otp()

        # Store OTP record
        otp_record = OTPVerification(
            email=email,
            otp=otp,
            purpose=OTPPurpose.FORGOT_PASSWORD,
            expires_at=datetime.now(timezone.utc) + timedelta(
                minutes=settings.OTP_TOKEN_EXPIRE_MINUTES
            ),
        )
        db.add(otp_record)
        await db.flush()

        # Generate + set OTP JWT cookie
        otp_token = create_otp_token(
            email=email,
            purpose=OTPPurpose.FORGOT_PASSWORD.value,
        )
        set_otp_token_cookie(response, otp_token)

        # Send email
        try:
            email_service.send_forgot_password_otp(
                to_email=email,
                full_name=user.full_name,
                otp=otp,
            )
            logger.info(f"Forgot password OTP sent: email={email}")
        except RuntimeError as e:
            logger.error(
                f"Failed to send forgot password OTP to {email}: {e}"
            )

        return MessageResponse(message=generic_message)

    # ─── Reset Password ───────────────────────────────────────────────────────

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        response: Response,
        email: str,
        new_password: str,
    ) -> MessageResponse:
        """
        Reset password after OTP verification.

        Email sourced from verified OTP JWT cookie — never request body.

        Flow:
        1. Load user
        2. Hash new password
        3. Update password_hash
        4. Revoke ALL refresh tokens (force re-login on all devices)
        5. Clear all cookies
        6. Return success
        """
        email = email.lower().strip()

        user = await AuthService._get_user_by_email(db, email)
        if not user:
            raise AccountNotFoundError()

        # Hash + update
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Revoke ALL refresh tokens — force re-login everywhere
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.is_revoked == False,
            )
            .values(is_revoked=True)
        )

        # Clear all cookies
        clear_all_auth_cookies(response)

        logger.info(
            f"Password reset complete: user_id={user.id}. "
            f"All refresh tokens revoked."
        )

        return MessageResponse(
            message=(
                "Password reset successful. "
                "Please login with your new password."
            )
        )

    # ─── Refresh Token ────────────────────────────────────────────────────────

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession,
        response: Response,
        refresh_token: str,
    ) -> TokenResponse:
        """
        Issue new access token using refresh token.
        Implements token rotation — old token revoked, new one issued.

        Flow:
        1. Decode refresh JWT
        2. Validate in DB (not revoked, not expired)
        3. Load user
        4. Revoke old refresh token
        5. Issue new access + refresh tokens
        6. Return user info
        """
        from core.security import decode_refresh_token

        # 1. Decode JWT
        try:
            payload = decode_refresh_token(refresh_token)
        except Exception:
            raise RefreshTokenInvalidError()

        user_id: str = payload.get("sub")
        if not user_id:
            raise RefreshTokenInvalidError()

        # 2. Validate in DB
        db_token = await AuthService._get_active_refresh_token(
            db, refresh_token
        )
        if not db_token:
            logger.warning(
                f"Invalid/revoked refresh token: user_id={user_id}"
            )
            raise RefreshTokenInvalidError()

        # 3. Load user
        user = await AuthService._get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise RefreshTokenInvalidError()

        # 4. Revoke old token (rotation)
        db_token.is_revoked = True
        await db.flush()

        logger.info(f"Refresh token rotated: user_id={user.id}")

        # 5. Issue new tokens
        await AuthService._issue_auth_tokens(db, response, user)

        # 6. Return response
        return TokenResponse(
            message="Token refreshed successfully.",
            user=UserResponse.model_validate(user),
        )

    # ─── Logout ───────────────────────────────────────────────────────────────

    @staticmethod
    async def logout(
        db: AsyncSession,
        response: Response,
        refresh_token: Optional[str],
        user_id: str,
    ) -> MessageResponse:
        """
        Logout user.

        Flow:
        1. Revoke refresh token in DB (if present)
        2. Clear all HTTP-only cookies
        3. Return success

        Always clears cookies even if token not found.
        """
        if refresh_token:
            db_token = await AuthService._get_active_refresh_token(
                db, refresh_token
            )
            if db_token:
                db_token.is_revoked = True
                await db.flush()
                logger.info(
                    f"Refresh token revoked on logout: user_id={user_id}"
                )

        clear_all_auth_cookies(response)
        logger.info(f"User logged out: user_id={user_id}")

        return MessageResponse(message="Logged out successfully.")