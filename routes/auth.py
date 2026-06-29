# routes/auth.py
"""
Authentication routes — exactly as per project requirements.

Endpoints:
  POST /auth/register          — Register Individual or Org user
  POST /auth/verify-otp        — Verify email OTP after registration
  POST /auth/resend-otp        — Resend OTP with cooldown
  POST /auth/login             — Login with email + password
  POST /auth/forgot-password   — Initiate forgot password flow
  POST /auth/verify-forgot-otp — Verify OTP for password reset
  POST /auth/reset-password    — Reset password after OTP verified
  POST /auth/logout            — Logout + clear all cookies
  POST /auth/refresh-token     — Rotate refresh token
"""
import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from core.cookies import get_refresh_token_from_cookie
from core.exceptions import TokenMissingError
from models.user import User
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
)
from schemas.response import (
    RegisterResponse,
    TokenResponse,
    MessageResponse,
)
from services.auth_service import AuthService
from services.otp_service import OTPService
from services.token_service import TokenService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ─── POST /auth/register ──────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    summary="Register a new user",
    description=(
        "Register a new Individual or Organization account.\n\n"
        "**Individual:** full_name, email, password, confirm_password, "
        "account_type=individual\n\n"
        "**Organization:** all above + organization_name, "
        "account_type=organization, business email required\n\n"
        "On success: OTP sent to email, otp_token set in HTTP-only cookie."
    ),
    responses={
        201: {"description": "Registration successful, OTP sent"},
        409: {"description": "Email already exists"},
        422: {"description": "Validation error"},
    },
)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Register new user.
    On success sets otp_token HTTP-only cookie for OTP verification.
    Email is NOT returned — use email_hint for display only.
    """
    logger.info(
        f"Register request: email={payload.email} "
        f"account_type={payload.account_type.value}"
    )
    return await AuthService.register(
        db=db,
        response=response,
        payload=payload,
    )


# ─── POST /auth/verify-otp ───────────────────────────────────────────────────

@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify email OTP",
    description=(
        "Verify the 6-digit OTP sent to email during registration.\n\n"
        "**Email is NOT required in request body** — extracted from "
        "otp_token HTTP-only cookie automatically.\n\n"
        "On success: account activated, access_token and refresh_token "
        "set in HTTP-only cookies. If Organization account, tenant is "
        "auto-created and tenant admin assigned."
    ),
    responses={
        200: {"description": "OTP verified, account activated, tokens set"},
        400: {"description": "Invalid, expired, or already used OTP"},
        401: {"description": "OTP token cookie missing or invalid"},
        429: {"description": "Max OTP retry attempts exceeded"},
    },
)
async def verify_otp(
    payload: VerifyOTPRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Verify registration OTP.
    Email resolved from otp_token cookie — never from request body.
    On success: activates account + issues access/refresh tokens.
    """
    logger.info("OTP verification request received")

    # Step 1: Validate OTP — returns verified email
    email = await OTPService.verify_registration_otp(
        db=db,
        response=response,
        request=request,
        otp_input=payload.otp,
    )

    # Step 2: Activate account + issue tokens
    return await AuthService.activate_account(
        db=db,
        response=response,
        email=email,
    )


# ─── POST /auth/resend-otp ───────────────────────────────────────────────────

@router.post(
    "/resend-otp",
    response_model=MessageResponse,
    summary="Resend OTP",
    description=(
        "Resend OTP to the registered email.\n\n"
        "Email resolved from otp_token HTTP-only cookie — "
        "no request body needed.\n\n"
        f"Cooldown enforced between resend requests. "
        "Previous OTP is invalidated immediately."
    ),
    responses={
        200: {"description": "New OTP sent successfully"},
        401: {"description": "OTP token cookie missing or expired"},
        429: {"description": "Resend cooldown active"},
    },
)
async def resend_otp(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Resend OTP.
    Email + purpose resolved from otp_token cookie.
    Cooldown prevents spam. Old OTP invalidated on resend.
    """
    logger.info("Resend OTP request received")
    return await OTPService.resend_otp(
        db=db,
        response=response,
        request=request,
    )


# ─── POST /auth/login ────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description=(
        "Login with email and password.\n\n"
        "On success: access_token (15-30 min) and refresh_token (7-30 days) "
        "set in HTTP-only cookies.\n\n"
        "**Frontend:** include `credentials: 'include'` in all fetch calls "
        "so cookies are sent automatically."
    ),
    responses={
        200: {"description": "Login successful, tokens set in cookies"},
        401: {"description": "Invalid email or password"},
        403: {"description": "Account not verified — complete OTP first"},
    },
)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email + password.
    Issues access_token + refresh_token in HTTP-only cookies.
    """
    logger.info(f"Login request: email={payload.email}")
    return await AuthService.login(
        db=db,
        response=response,
        payload=payload,
    )


# ─── POST /auth/forgot-password ──────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Forgot password — request OTP",
    description=(
        "Initiate forgot password flow.\n\n"
        "Generates OTP and sends to registered email. "
        "Sets otp_token in HTTP-only cookie.\n\n"
        "Returns same message whether email exists or not "
        "(prevents user enumeration)."
    ),
    responses={
        200: {"description": "OTP sent if account exists"},
    },
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Initiate forgot password flow.
    Sets otp_token cookie for subsequent verify-forgot-otp call.
    """
    logger.info(f"Forgot password request: email={payload.email}")
    return await AuthService.forgot_password(
        db=db,
        response=response,
        email=payload.email,
    )


# ─── POST /auth/verify-forgot-otp ────────────────────────────────────────────

@router.post(
    "/verify-forgot-otp",
    response_model=MessageResponse,
    summary="Verify forgot password OTP",
    description=(
        "Verify OTP for password reset flow.\n\n"
        "Email resolved from otp_token cookie — not from request body.\n\n"
        "On success: refreshes otp_token cookie to confirm OTP was verified. "
        "Call /auth/reset-password next."
    ),
    responses={
        200: {"description": "OTP verified — proceed to reset-password"},
        400: {"description": "Invalid, expired, or already used OTP"},
        401: {"description": "OTP token cookie missing or invalid"},
        429: {"description": "Max retry exceeded"},
    },
)
async def verify_forgot_otp(
    payload: VerifyOTPRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Verify OTP for forgot password flow.
    On success refreshes otp_token cookie — gates /auth/reset-password.
    """
    logger.info("Verify forgot password OTP request received")

    await OTPService.verify_forgot_password_otp(
        db=db,
        response=response,
        request=request,
        otp_input=payload.otp,
    )

    return MessageResponse(
        message=(
            "OTP verified successfully. "
            "You may now reset your password."
        )
    )


# ─── POST /auth/reset-password ───────────────────────────────────────────────

@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description=(
        "Reset password after OTP verification.\n\n"
        "Requires valid otp_token cookie from /auth/verify-forgot-otp.\n\n"
        "Email is extracted from otp_token cookie — never from request body.\n\n"
        "On success: all refresh tokens revoked (force re-login on all devices), "
        "all cookies cleared."
    ),
    responses={
        200: {"description": "Password reset successful"},
        401: {"description": "OTP token cookie missing or not verified"},
        404: {"description": "User not found"},
        422: {"description": "Password policy violation"},
    },
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Reset password.
    Email gated by otp_token cookie — must have completed verify-forgot-otp.
    All existing sessions invalidated on success.
    """
    logger.info("Reset password request received")

    # Extract + validate email from OTP cookie
    # Purpose must be forgot_password — prevents using registration OTP
    email = TokenService.extract_email_from_otp_cookie(
        request=request,
        expected_purpose="forgot_password",
    )

    return await AuthService.reset_password(
        db=db,
        response=response,
        email=email,
        new_password=payload.new_password,
    )


# ─── POST /auth/logout ───────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout",
    description=(
        "Logout current session.\n\n"
        "Revokes refresh token in DB and clears all HTTP-only cookies "
        "(access_token, refresh_token, otp_token).\n\n"
        "Always succeeds — safe to call even if already logged out."
    ),
    responses={
        200: {"description": "Logged out successfully"},
    },
)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Logout authenticated user.
    Revokes refresh token + clears all cookies.
    Requires valid access_token.
    """
    logger.info(f"Logout request: user_id={current_user.id}")

    # Extract refresh token (optional — logout still succeeds if missing)
    refresh_token = get_refresh_token_from_cookie(request)

    return await AuthService.logout(
        db=db,
        response=response,
        refresh_token=refresh_token,
        user_id=current_user.id,
    )


# ─── POST /auth/refresh-token ────────────────────────────────────────────────

@router.post(
    "/refresh-token",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Generate new access token using refresh token.\n\n"
        "Refresh token read from HTTP-only cookie automatically.\n\n"
        "Implements token rotation — old refresh token is revoked "
        "and new access + refresh tokens are issued.\n\n"
        "Call this when access_token expires (401 response)."
    ),
    responses={
        200: {"description": "New tokens issued"},
        401: {"description": "Refresh token missing, invalid or expired"},
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Rotate refresh token and issue new access token.
    Refresh token read from HTTP-only cookie.
    """
    logger.info("Refresh token request received")

    # Extract refresh token from cookie
    raw_token = TokenService.extract_refresh_token_from_cookie(request)

    return await AuthService.refresh_access_token(
        db=db,
        response=response,
        refresh_token=raw_token,
    )