# schemas/auth.py
import re
from typing import Optional
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)
from models.user import AccountType


# ─── Password Policy ─────────────────────────────────────────────────────────

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

# At least: 1 uppercase, 1 lowercase, 1 digit, 1 special char
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&^#])[A-Za-z\d@$!%*?&^#]{8,}$"
)

# Basic business email domains to reject for org accounts
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "aol.com", "protonmail.com", "mail.com",
    "ymail.com", "live.com", "msn.com",
}


def validate_password_policy(password: str) -> str:
    """
    Enforce password policy:
    - Min 8, max 128 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character (@$!%*?&^#)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must not exceed {PASSWORD_MAX_LENGTH} characters."
        )
    if not PASSWORD_REGEX.match(password):
        raise ValueError(
            "Password must contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character "
            "(@$!%*?&^#)."
        )
    return password


def validate_business_email(email: str) -> str:
    """
    Reject free email providers for Organization accounts.
    Validates domain against known free email providers.
    """
    domain = email.split("@")[-1].lower()
    if domain in FREE_EMAIL_DOMAINS:
        raise ValueError(
            f"Organization accounts must use a business email address. "
            f"'{domain}' is not allowed."
        )
    return email


# ─── Registration Schema ─────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """
    User registration request.

    Individual: full_name + email + password + confirm_password + account_type
    Organization: above + organization_name + official business email

    Validations run in order:
    1. Field-level validators (email format, password policy)
    2. model_validator (password match, org-specific rules)
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
    )

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User's full name (2–255 characters)",
        examples=["John Doe"],
    )

    email: EmailStr = Field(
        ...,
        description="Valid email address",
        examples=["john@example.com"],
    )

    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description=(
            "Password: min 8 chars, must include uppercase, "
            "lowercase, digit, and special character."
        ),
        examples=["Secure@123"],
    )

    confirm_password: str = Field(
        ...,
        description="Must match password exactly",
        examples=["Secure@123"],
    )

    account_type: AccountType = Field(
        ...,
        description="Account type: 'individual' or 'organization'",
        examples=["individual"],
    )

    organization_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Required for Organization accounts only",
        examples=["Acme Corp"],
    )

    # ── Field Validators ─────────────────────────────────────────────────────

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if not v.replace(" ", "").isalpha():
            raise ValueError(
                "Full name must contain only letters and spaces."
            )
        if len(v.split()) < 2:
            raise ValueError(
                "Please provide both first and last name."
            )
        return v.title()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_policy(v)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    # ── Model Validators ─────────────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_registration(self) -> "RegisterRequest":
        # 1. Password match
        if self.password != self.confirm_password:
            raise ValueError(
                "Password and Confirm Password do not match."
            )

        # 2. Organization-specific rules
        if self.account_type == AccountType.ORGANIZATION:
            # Organization name is mandatory
            if not self.organization_name or not self.organization_name.strip():
                raise ValueError(
                    "Organization name is required for Organization accounts."
                )
            # Business email required
            try:
                validate_business_email(self.email)
            except ValueError as e:
                raise ValueError(str(e))

        return self


# ─── OTP Schemas ─────────────────────────────────────────────────────────────

class VerifyOTPRequest(BaseModel):
    """
    OTP verification request.

    IMPORTANT: Email is NOT accepted from frontend.
    Email is extracted from the OTP JWT stored in HTTP-only cookie.
    This prevents email tampering between registration and verification.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric OTP sent to registered email",
        examples=["123456"],
    )

    @field_validator("otp")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain only digits.")
        return v


class ResendOTPRequest(BaseModel):
    """
    Resend OTP request.

    Email is extracted from OTP JWT cookie — not from request body.
    Purpose is extracted from OTP JWT cookie claim.
    This schema exists only to satisfy Swagger documentation requirements.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    # No fields required — email + purpose come from cookie
    # Kept as a schema for Swagger documentation consistency


# ─── Login Schema ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Login with email and password.
    Returns access token + refresh token in HTTP-only cookies.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(
        ...,
        description="Registered email address",
        examples=["john@example.com"],
    )

    password: str = Field(
        ...,
        min_length=1,
        max_length=PASSWORD_MAX_LENGTH,
        description="Account password",
        examples=["Secure@123"],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


# ─── Forgot Password Schemas ─────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    """
    Initiate forgot password flow.
    Generates OTP and stores OTP JWT in HTTP-only cookie.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(
        ...,
        description="Email address of the account to reset",
        examples=["john@example.com"],
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class ResetPasswordRequest(BaseModel):
    """
    Reset password after OTP verification.
    Requires verified OTP JWT in HTTP-only cookie.
    New password must satisfy password policy.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description=(
            "New password: min 8 chars, must include uppercase, "
            "lowercase, digit, and special character."
        ),
        examples=["NewSecure@456"],
    )

    confirm_new_password: str = Field(
        ...,
        description="Must match new_password exactly",
        examples=["NewSecure@456"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_policy(v)

    @model_validator(mode="after")
    def passwords_must_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError(
                "New Password and Confirm New Password do not match."
            )
        return self