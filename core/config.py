# core/config.py
from pydantic_settings import BaseSettings
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI SaaS Backend"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Token Expiry
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OTP_TOKEN_EXPIRE_MINUTES: int = 5

    # OTP
    OTP_LENGTH: int = 6
    OTP_MAX_RETRY: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    # Cookie
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_HTTPONLY: bool = True
    COOKIE_PATH: str = "/"

    # Cookie Names
    ACCESS_TOKEN_COOKIE: str = "access_token"
    REFRESH_TOKEN_COOKIE: str = "refresh_token"
    OTP_TOKEN_COOKIE: str = "otp_token"

    # API
    API_PREFIX: str = "/api/v1"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str = "AI SaaS"

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # ── Derived cookie paths — always in sync with API_PREFIX ──────────────
    @property
    def AUTH_COOKIE_PATH(self) -> str:
        """OTP token scope — only sent to auth routes."""
        return f"{self.API_PREFIX}/auth"

    @property
    def REFRESH_COOKIE_PATH(self) -> str:
        """Refresh token scope — only sent to refresh endpoint."""
        return f"{self.API_PREFIX}/auth/refresh-token"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()