# models/user.py
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Enum as SAEnum,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.refresh_token import RefreshToken
    from models.otp_verification import OTPVerification


# ─── Enums ───────────────────────────────────────────────────────────────────

class AccountType(str, Enum):
    INDIVIDUAL   = "individual"
    ORGANIZATION = "organization"


# ─── Model ───────────────────────────────────────────────────────────────────

class User(Base):
    """
    Table: users

    Individual: full_name + email + password
    Organization: same + tenant created on OTP activation

    is_active = False until OTP verified
    is_admin  = True only for platform admins
    """
    __tablename__ = "users"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        comment="UUID primary key",
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User full name",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique email address",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hashed password",
    )

    # ── Account Type ─────────────────────────────────────────────────────────
    # values_callable ensures PostgreSQL enum uses .value not .name
    account_type: Mapped[AccountType] = mapped_column(
        SAEnum(
            AccountType,
            name="account_type_enum",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="individual or organization",
    )

    # ── Status Flags ─────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="False until email OTP verified",
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="Platform admin flag",
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC creation timestamp",
    )

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        comment="UTC last update timestamp",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant",
        back_populates="owner",
        uselist=False,
        lazy="select",
    )

    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    otp_records: Mapped[List["OTPVerification"]] = relationship(
        "OTPVerification",
        primaryjoin="User.email == foreign(OTPVerification.email)",
        lazy="select",
        viewonly=True,
    )

    # ── Dunder ───────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<User id={self.id!r} "
            f"email={self.email!r} "
            f"type={self.account_type.value!r} "
            f"active={self.is_active}>"
        )

    # ── Helper Properties ────────────────────────────────────────────────────
    @property
    def is_organization(self) -> bool:
        return self.account_type == AccountType.ORGANIZATION

    @property
    def is_individual(self) -> bool:
        return self.account_type == AccountType.INDIVIDUAL