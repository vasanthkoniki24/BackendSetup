# schemas/user.py
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from models.user import AccountType


class UserResponse(BaseModel):
    """
    Safe user representation.
    Returned after login, token refresh, GET /users/me.
    Never exposes password_hash.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    account_type: AccountType = Field(
        ...,
        description="individual or organization",
    )
    is_active: bool = Field(
        ...,
        description="True if email OTP verified",
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp (UTC)",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp (UTC)",
    )