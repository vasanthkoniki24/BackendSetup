from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    success: bool = True
    total: int
    users: list[UserResponse]


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str