import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.dependencies import get_current_user, get_current_admin
from core.exceptions import NotFoundError, ForbiddenError
from core.security import hash_password, verify_password
from models.user import User
from schemas.user import UserResponse, UserListResponse, UserUpdateRequest, ChangePasswordRequest
from schemas.auth import MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse, dependencies=[Depends(get_current_admin)])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar_one()

    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()

    return UserListResponse(total=total, users=list(users))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenError("Access denied")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User")

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenError("Access denied")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    logger.info(f"User {user_id} updated")

    return user


@router.delete("/{user_id}", response_model=MessageResponse, dependencies=[Depends(get_current_admin)])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User")

    await db.delete(user)
    logger.info(f"User {user_id} deleted")

    return MessageResponse(message="User deleted successfully")


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise ForbiddenError("Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    await db.flush()

    logger.info(f"Password changed for user {current_user.id}")
    return MessageResponse(message="Password changed successfully")