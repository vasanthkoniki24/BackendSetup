# core/security.py
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Suppress bcrypt __about__ warning from passlib on newer bcrypt versions
warnings.filterwarnings(
    "ignore",
    message=".*error reading bcrypt version.*",
    category=UserWarning,
)

from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from core.config import settings
from core.exceptions import TokenExpiredError, TokenInvalidError

# ─── Password Hashing ────────────────────────────────────────────────────────

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(plain_password: str) -> str:
    """Hash plain-text password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain-text password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── OTP Generation ──────────────────────────────────────────────────────────

def generate_otp(length: int = None) -> str:
    """
    Generate cryptographically secure numeric OTP.
    Uses secrets module — never random — no predictability.
    """
    length = length or settings.OTP_LENGTH
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


# ─── JWT Token Creation ──────────────────────────────────────────────────────

def _build_token(
    subject: str,
    token_type: str,
    expire_delta: timedelta,
    extra_claims: dict[str, Any] = None,
) -> str:
    """
    Internal — build and sign a JWT.

    Claims:
        sub  → subject (user_id or email)
        type → token purpose
        iat  → issued at
        exp  → expiry
        jti  → unique token ID (enables future blacklisting)
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expire_delta,
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    user_id: str,
    email: str,
    account_type: str,
) -> str:
    """
    Short-lived access token (15–30 min).
    Carries user identity for protected route authentication.
    """
    return _build_token(
        subject=user_id,
        token_type="access",
        expire_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        extra_claims={
            "email": email,
            "account_type": account_type,
        },
    )


def create_refresh_token(user_id: str) -> str:
    """
    Long-lived refresh token (7–30 days).
    Used ONLY to issue new access tokens.
    """
    return _build_token(
        subject=user_id,
        token_type="refresh",
        expire_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )


def create_otp_token(email: str, purpose: str) -> str:
    """
    Short-lived OTP session token (5 min).
    Binds OTP flow to email without exposing email in frontend.

    purpose: 'registration' | 'forgot_password'
    """
    return _build_token(
        subject=email,
        token_type="otp",
        expire_delta=timedelta(
            minutes=settings.OTP_TOKEN_EXPIRE_MINUTES
        ),
        extra_claims={"purpose": purpose},
    )


# ─── JWT Token Decoding ──────────────────────────────────────────────────────

def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises:
        TokenExpiredError  → past exp claim
        TokenInvalidError  → bad signature / wrong type / malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()

    if payload.get("type") != expected_type:
        raise TokenInvalidError()

    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> dict[str, Any]:
    return decode_token(token, expected_type="refresh")


def decode_otp_token(token: str) -> dict[str, Any]:
    return decode_token(token, expected_type="otp")


# ─── Secure Random Helpers ───────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    """Generate URL-safe random token."""
    return secrets.token_urlsafe(nbytes)