# main.py
"""
AI SaaS Platform — FastAPI Application Entry Point

Active routes (auth module scope):
  /api/v1/auth/*   — Authentication & OTP
  /api/v1/users/*  — User profile (GET /me only)
  /health          — System health check

All other modules (tenants, marketplace, subscriptions,
notifications, admin, AI) are out of scope for this phase.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import engine, Base
from core.exceptions import AppException
from core.logging_config import setup_logging

# ─── Model imports ────────────────────────────────────────────────────────────
# Must be imported before create_all so metadata includes all tables
from models.user import User                          # noqa: F401
from models.tenant import Tenant                      # noqa: F401
from models.otp_verification import OTPVerification   # noqa: F401
from models.refresh_token import RefreshToken         # noqa: F401

# ─── Logging ─────────────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} "
        f"[{settings.ENVIRONMENT}]"
    )
    # Development: auto-create tables
    # Production: use Alembic migrations exclusively
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(
            "DB tables verified/created (development mode). "
            "Use Alembic for production migrations."
        )
    yield
    await engine.dispose()
    logger.info("Database engine disposed. Shutdown complete.")


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI SaaS Platform — Authentication & User Management API\n\n"
        "## Authentication\n"
        "All protected endpoints require an `access_token` HTTP-only cookie "
        "or `Authorization: Bearer <token>` header.\n\n"
        "## Cookie-based Auth\n"
        "Tokens are stored in HTTP-only cookies automatically on login. "
        "Include `credentials: 'include'` in all frontend fetch calls."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,   # Required for cookie-based auth
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handlers ────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """
    Handles all custom AppException subclasses.
    Returns consistent error envelope.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catch-all for unexpected server errors.
    Hides internal details in production.
    """
    logger.exception(
        f"Unhandled error: {request.method} {request.url} — {exc}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": (
                str(exc)
                if settings.ENVIRONMENT == "development"
                else "An unexpected error occurred. Please try again."
            ),
        },
    )


# ─── Routes ───────────────────────────────────────────────────────────────────
# Import routers AFTER lifespan and middleware setup

API_PREFIX = "/api/v1"

# Auth router — all 9 auth endpoints
from routes.auth import router as auth_router
app.include_router(auth_router, prefix=API_PREFIX)

# Users router — GET /users/me only
from routes.users import router as users_router
app.include_router(users_router, prefix=API_PREFIX)


# ─── System Endpoints ─────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns application health status.",
)
async def health_check():
    return {
        "success": True,
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }