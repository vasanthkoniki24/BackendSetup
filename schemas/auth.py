from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: Literal["admin", "user", "tenant"] = "user"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    

class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    success: bool = True
    message: str
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    success: bool = True
    message: str