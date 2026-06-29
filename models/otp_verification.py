# models/otp_verification.py
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Enum as SAEnum,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from core.database import Base


# ─── Enums ───────────────────────────────────────────────────────────────────

class OTPPurpose(str, Enum):
    REGISTRATION    = "registration"
    FORGOT_PASSWORD = "forgot_password"


# ─── Model ───────────────────────────────────────────────────────────────────

class OTPVerification(Base):
    """
    Table: otp_verifications

    Stores OTP records for registration and forgot password flows.
    organization_name stored here for org tenant creation on activation.
    """
    __tablename__ = "otp_verifications"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID primary key",
    )

    # ── Target Email ─────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Target email — no FK to users",
    )

    # ── OTP ──────────────────────────────────────────────────────────────────
    otp: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="6-digit OTP plain text",
    )

    # ── Purpose ──────────────────────────────────────────────────────────────
    # values_callable ensures PostgreSQL stores 'registration'
    # not 'REGISTRATION' (enum name vs value)
    purpose: Mapped[OTPPurpose] = mapped_column(
        SAEnum(
            OTPPurpose,
            name="otp_purpose_enum",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="registration | forgot_password",
    )

    # ── Expiry ───────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="UTC expiry timestamp",
    )

    # ── State ────────────────────────────────────────────────────────────────
    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="True after successful verification",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Wrong attempt counter",
    )

    # ── Organization Name ─────────────────────────────────────────────────────
    organization_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="Org name for organization registrations only",
    )

    # ── Timestamp ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC creation timestamp",
    )

    # ── Dunder ───────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<OTPVerification id={self.id!r} "
            f"email={self.email!r} "
            f"purpose={self.purpose.value!r} "
            f"verified={self.verified}>"
        )

    # ── Helpers ──────────────────────────────────────────────────────────────
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_usable(self) -> bool:
        from core.config import settings
        return (
            not self.is_expired
            and not self.verified
            and self.retry_count < settings.OTP_MAX_RETRY
        )