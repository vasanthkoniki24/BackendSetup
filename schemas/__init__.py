# schemas/__init__.py
from schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    ResendOTPRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from schemas.response import (
    MessageResponse,
    TokenResponse,
    RegisterResponse,
    ErrorResponse,
    TenantResponse,
    OTPResponse,
    mask_email,
)
from schemas.user import UserResponse

__all__ = [
    # Auth requests
    "RegisterRequest",
    "VerifyOTPRequest",
    "ResendOTPRequest",
    "LoginRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    # Responses
    "MessageResponse",
    "TokenResponse",
    "RegisterResponse",
    "ErrorResponse",
    "TenantResponse",
    "OTPResponse",
    "mask_email",
    # User
    "UserResponse",
]