# core/cookies.py
from fastapi import Response, Request
from core.config import settings


# ─── Cookie Setters ──────────────────────────────────────────────────────────

def _set_cookie(
    response: Response,
    key: str,
    value: str,
    max_age: int,
    path: str = None,
) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=path or settings.COOKIE_PATH,
    )


def set_access_token_cookie(response: Response, token: str) -> None:
    """Access token — path=/ so it's sent to all routes including /users/me."""
    _set_cookie(
        response=response,
        key=settings.ACCESS_TOKEN_COOKIE,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.COOKIE_PATH,           # "/"
    )


def set_refresh_token_cookie(response: Response, token: str) -> None:
    """Refresh token — scoped to refresh endpoint only."""
    _set_cookie(
        response=response,
        key=settings.REFRESH_TOKEN_COOKIE,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=settings.REFRESH_COOKIE_PATH,   # "/api/v1/auth/refresh-token"
    )


def set_otp_token_cookie(response: Response, token: str) -> None:
    """OTP token — scoped to auth routes only."""
    _set_cookie(
        response=response,
        key=settings.OTP_TOKEN_COOKIE,
        value=token,
        max_age=settings.OTP_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.AUTH_COOKIE_PATH,      # "/api/v1/auth"
    )


# ─── Cookie Clearers ─────────────────────────────────────────────────────────

def _clear_cookie(response: Response, key: str, path: str = None) -> None:
    response.delete_cookie(
        key=key,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=path or settings.COOKIE_PATH,
    )


def clear_access_token_cookie(response: Response) -> None:
    _clear_cookie(response, settings.ACCESS_TOKEN_COOKIE, path=settings.COOKIE_PATH)


def clear_refresh_token_cookie(response: Response) -> None:
    _clear_cookie(response, settings.REFRESH_TOKEN_COOKIE, path=settings.REFRESH_COOKIE_PATH)


def clear_otp_token_cookie(response: Response) -> None:
    _clear_cookie(response, settings.OTP_TOKEN_COOKIE, path=settings.AUTH_COOKIE_PATH)


def clear_all_auth_cookies(response: Response) -> None:
    """Clear all auth cookies — used on logout and password reset."""
    clear_access_token_cookie(response)
    clear_refresh_token_cookie(response)
    clear_otp_token_cookie(response)


# ─── Cookie Readers ──────────────────────────────────────────────────────────

def get_access_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.ACCESS_TOKEN_COOKIE)


def get_refresh_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.REFRESH_TOKEN_COOKIE)


def get_otp_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.OTP_TOKEN_COOKIE)