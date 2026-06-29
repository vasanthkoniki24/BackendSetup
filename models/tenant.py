# models/tenant.py
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.database import Base

if TYPE_CHECKING:
    from models.user import User


# ─── Enums ───────────────────────────────────────────────────────────────────

class TenantStatus(str, Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"


# ─── Model ───────────────────────────────────────────────────────────────────

class Tenant(Base):
    """
    Table: tenants

    Auto-created when Organization user completes OTP verification.
    One tenant per organization user (enforced by unique FK).
    organization_name sourced from OTPVerification record.
    """
    __tablename__ = "tenants"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID primary key",
    )

    # ── Organization ─────────────────────────────────────────────────────────
    organization_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Official organization name",
    )

    # ── Owner ─────────────────────────────────────────────────────────────────
    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="FK to users.id — tenant owner/admin",
    )

    # ── Status ───────────────────────────────────────────────────────────────
    # NOTE: No server_default for enum — use Python-level default only
    # PostgreSQL enum server_default causes InvalidTextRepresentationError
    # when enum type is recreated. Python default is safer and sufficient.
    status: Mapped[TenantStatus] = mapped_column(
        SAEnum(
            TenantStatus,
            name="tenant_status_enum",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=TenantStatus.ACTIVE,
        comment="active | inactive | suspended",
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        comment="UTC last update timestamp",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="tenant",
        lazy="select",
    )

    # ── Dunder ───────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<Tenant id={self.id!r} "
            f"org={self.organization_name!r} "
            f"status={self.status.value!r}>"
        )