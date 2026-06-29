# models/refresh_token.py
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.database import Base

if TYPE_CHECKING:
    from models.user import User


# ─── Model ───────────────────────────────────────────────────────────────────

class RefreshToken(Base):
    """
    Refresh token table.

    Design decisions:
    - Token value stored as-is (urlsafe random, not JWT)
      The actual refresh JWT lives in the cookie;
      this table stores a reference for revocation checks
    - is_revoked: soft-delete — allows audit trail
    - CASCADE delete: all tokens removed when user deleted
    - One user can have multiple active tokens
      (multiple devices / sessions)
    - Rotation strategy: on each refresh, old token is revoked
      and a new one is inserted
    """
    __tablename__ = "refresh_tokens"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID primary key",
    )

    # ── Owner ─────────────────────────────────────────────────────────────────
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to users.id",
    )

    # ── Token ─────────────────────────────────────────────────────────────────
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True,
        comment="The JWT refresh token string",
    )

    # ── Expiry ───────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="UTC expiry — matches JWT exp claim",
    )

    # ── Revocation ───────────────────────────────────────────────────────────
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="True when logged out or rotated",
    )

    # ── Timestamp ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC creation timestamp",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
        lazy="select",
    )

    # ── Dunder ───────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id!r} "
            f"user_id={self.user_id!r} "
            f"revoked={self.is_revoked}>"
        )

    # ── Helper Properties ────────────────────────────────────────────────────
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Token is valid only if not revoked and not expired."""
        return not self.is_revoked and not self.is_expired