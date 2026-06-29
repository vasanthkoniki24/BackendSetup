# routes/users.py
"""
User routes — scoped strictly to auth module requirements.

Only endpoint in scope:
  GET /users/me — get authenticated user profile

All other user management endpoints are out of scope
for the current auth module development phase.
"""
import logging

from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from models.user import User
from schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ─── GET /users/me ────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description=(
        "Returns the authenticated user's profile. "
        "Requires valid access_token in HTTP-only cookie "
        "or Authorization: Bearer header."
    ),
    responses={
        200: {"description": "User profile returned successfully"},
        401: {"description": "Missing or invalid access token"},
        403: {"description": "Account is inactive"},
    },
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Returns authenticated user profile.
    Token is read from HTTP-only cookie (access_token)
    or Authorization header — handled by get_current_user dependency.
    """
    logger.info(f"Profile fetched: user_id={current_user.id}")
    return UserResponse.model_validate(current_user)