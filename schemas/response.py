# schemas/response.py
from typing import Optional, Any, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from models.user import AccountType

T = TypeVar("T")


# ─── Generic Wrapper ─────────────────────────────────────────────────────────

class APIResponse(BaseModel, Generic[T]):
    """
    Generic API response envelope.
    Wraps all responses in a consistent structure:

    {
        "success": true,
        "message": "Operation successful",
        "data": { ... }
    }
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(
        default=True,
        description="True if request succeeded, False otherwise",
    )
    message: str = Field(
        ...,
        description="Human-readable result message",
    )
    data: Optional[T] = Field(
        default=None,
        description="Response payload — null when no data to return",
    )


# ─── Error Response ───────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """
    Standard error envelope returned on all exceptions.
    Used in Swagger error response documentation.

    {
        "success": false,
        "message": "An account with this email already exists.",
        "error_code": "EMAIL_ALREADY_EXISTS"
    }
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(
        default=False,
        description="Always false for error responses",
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code for frontend handling",
    )


# ─── Message Response ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """
    Simple success message response.
    Used when no payload is needed (logout, resend OTP, etc.)
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True)
    message: str = Field(
        ...,
        description="Human-readable success message",
        examples=["OTP sent successfully."],
    )


# ─── User Response ────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """
    Safe user representation — never exposes password_hash.
    Returned after registration, login, and token refresh.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User UUID")
    full_name: str = Field(..., description="User's full name")
    email: str = Field(..., description="Email address")
    account_type: AccountType = Field(
        ...,
        description="individual or organization",
    )
    is_active: bool = Field(
        ...,
        description="True if email has been verified",
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp (UTC)",
    )


# ─── Token Response ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """
    Response after successful login or token refresh.

    Tokens themselves are stored in HTTP-only cookies —
    NOT returned in the response body for security.
    This response only confirms the action and returns user info.
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True)
    message: str = Field(
        default="Login successful.",
        description="Human-readable result",
    )
    token_type: str = Field(
        default="cookie",
        description="Tokens are stored in HTTP-only cookies",
    )
    user: UserResponse = Field(
        ...,
        description="Authenticated user details",
    )


# ─── Registration Response ────────────────────────────────────────────────────

class RegisterResponse(BaseModel):
    """
    Response after successful registration.
    Informs frontend that OTP has been sent.
    Does NOT return the OTP or any token in the body.
    OTP JWT is set as HTTP-only cookie automatically.
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True)
    message: str = Field(
        default="Registration successful. Please check your email for the OTP.",
        description="Human-readable result",
    )
    email_hint: str = Field(
        ...,
        description=(
            "Masked email address for UI display only. "
            "e.g. j***@example.com"
        ),
        examples=["j***@example.com"],
    )


# ─── Tenant Response ──────────────────────────────────────────────────────────

class TenantResponse(BaseModel):
    """
    Organization tenant details.
    Returned as part of org user profile responses.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Tenant UUID")
    organization_name: str = Field(
        ...,
        description="Organization name",
    )
    status: str = Field(
        ...,
        description="active | inactive | suspended",
    )
    created_at: datetime = Field(
        ...,
        description="Tenant creation timestamp (UTC)",
    )


# ─── OTP Response ────────────────────────────────────────────────────────────

class OTPResponse(BaseModel):
    """
    Response after OTP send or resend.
    Used internally — exposed via MessageResponse to frontend.
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True)
    message: str = Field(
        ...,
        description="OTP action result",
    )
    expires_in_seconds: int = Field(
        ...,
        description="OTP validity window in seconds",
        examples=[300],
    )


# ─── Utility: Email Masking ───────────────────────────────────────────────────

def mask_email(email: str) -> str:
    """
    Mask email for safe display in API responses.

    john.doe@example.com  →  j***@example.com
    ab@test.com           →  a***@test.com
    """
    try:
        local, domain = email.split("@")
        if len(local) <= 1:
            masked_local = "*"
        else:
            masked_local = local[0] + "***"
        return f"{masked_local}@{domain}"
    except Exception:
        return "***@***.***"