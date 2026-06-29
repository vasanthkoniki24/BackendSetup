# core/dependencies.py
"""
FastAPI dependency injection for authentication and authorization.

Auth flow supported:
  - Cookie-based  : reads access_token from HTTP-only cookie (primary — browser clients)
  - Bearer-based  : reads from Authorization: Bearer <token> header (API / Swagger)

Both paths decode the same JWT and load the same User model.
"""
import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.cookies import get_access_token_from_cookie
from core.security import decode_access_token
from core.exceptions import (
    TokenMissingError,
    TokenInvalidError,
    AccountNotActiveError,
    AccountNotFoundError,
    PermissionDeniedError,
)
from models.user import User, AccountType

logger = logging.getLogger(__name__)

# ─── Bearer scheme (auto_error=False so we can fall back to cookie) ──────────
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Token Extractor ─────────────────────────────────────────────────────────

def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    """
    Extract JWT from request in priority order:
      1. HTTP-only cookie  (browser / frontend clients)
      2. Authorization header (Swagger UI / API clients / mobile)

    Raises TokenMissingError if neither is present.
    """
    # Priority 1: cookie
    cookie_token = get_access_token_from_cookie(request)
    if cookie_token:
        logger.debug("Access token resolved from cookie.")
        return cookie_token

    # Priority 2: Bearer header
    if credentials and credentials.credentials:
        logger.debug("Access token resolved from Authorization header.")
        return credentials.credentials

    raise TokenMissingError("access_token")


# ─── Core Auth Dependency ────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve and return the authenticated User from the request.

    Steps:
      1. Extract token (cookie → header fallback)
      2. Decode + validate JWT (type must be 'access')
      3. Load User from DB by UUID sub claim
      4. Assert account is active

    Raises:
      TokenMissingError      → no token in cookie or header
      TokenExpiredError      → token past exp claim
      TokenInvalidError      → bad signature / wrong type
      AccountNotFoundError   → user deleted after token issued
      AccountNotActiveError  → user exists but is_active = False
    """
    token = _extract_token(request, credentials)

    # Decode — raises TokenExpiredError or TokenInvalidError on failure
    payload = decode_access_token(token)

    user_id: str = payload.get("sub")
    if not user_id:
        raise TokenInvalidError()

    # Load user from DB
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user: Optional[User] = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Token valid but user not found: user_id={user_id}")
        raise AccountNotFoundError()

    if not user.is_active:
        logger.warning(f"Inactive account attempted access: user_id={user_id}")
        raise AccountNotActiveError()

    return user


# ─── Role-based Authorization Dependencies ───────────────────────────────────

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Alias for get_current_user.
    Use this name in routes where you want to be explicit
    that the user must be active (documents intent clearly).
    """
    return current_user


async def get_current_org_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the current user to be an Organization account.
    Use on routes that are org-only (e.g. tenant management).
    """
    if current_user.account_type != AccountType.ORGANIZATION:
        raise PermissionDeniedError()
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the current user to have admin role.
    Use on internal / admin-panel routes.
    """
    if not getattr(current_user, "is_admin", False):
        raise PermissionDeniedError()
    return current_user


# ─── Optional Auth (public routes that behave differently when authed) ────────

async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Returns the authenticated User if a valid token is present,
    or None if no token provided.

    Does NOT raise on missing token — useful for public routes
    that optionally personalize when a user is logged in.
    """
    try:
        token = _extract_token(request, credentials)
    except TokenMissingError:
        return None

    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    return user if (user and user.is_active) else None