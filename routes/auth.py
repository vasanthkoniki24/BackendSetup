import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.dependencies import get_current_user
from core.exceptions import ConflictError, UnauthorizedError
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from models.user import User
from schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, RefreshRequest, TokenResponse, MessageResponse
from schemas.user import UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    return RegisterResponse(
        message="Registration successful",
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)

    if not token_data or token_data.get("type") != "refresh":
        raise UnauthorizedError("Invalid or expired refresh token")

    user_id = token_data.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    logger.info(f"User logged out: {current_user.email}")
    return MessageResponse(message="Logged out successfully")