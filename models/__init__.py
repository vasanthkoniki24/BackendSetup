# models/__init__.py
# Import all models here so Alembic can detect them during autogenerate
from models.user import User, AccountType
from models.tenant import Tenant, TenantStatus
from models.otp_verification import OTPVerification, OTPPurpose
from models.refresh_token import RefreshToken

__all__ = [
    "User",
    "AccountType",
    "Tenant",
    "TenantStatus",
    "OTPVerification",
    "OTPPurpose",
    "RefreshToken",
]