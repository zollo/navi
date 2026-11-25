"""A custom domain (e.g. www.example.com) that shows a page instead of /<handle>."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.page import Page


class CustomDomain(UUIDMixin, Base):
    """One per page. Live once verified: a TXT record proves the owner controls the
    domain and its A/CNAME record points at Navi.

    Several pages may *claim* the same hostname, so nobody can squat a domain they
    don't control; only one claim can be verified (partial unique index).
    """

    __tablename__ = "custom_domains"
    __table_args__ = (
        Index(
            "uq_custom_domains_verified_hostname",
            "hostname",
            unique=True,
            postgresql_where=text("verified_at IS NOT NULL"),
            sqlite_where=text("verified_at IS NOT NULL"),
        ),
    )

    page_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Lowercase ASCII (IDNA) hostname, no trailing dot.
    hostname: Mapped[str] = mapped_column(String(253), index=True, nullable=False)
    # Value the owner publishes as TXT _navi-challenge.<hostname> = navi-verify=<token>.
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Why the last check failed (null after a passing check).
    last_error: Mapped[str | None] = mapped_column(Text)
    # Consecutive failed re-checks of a verified domain; it's switched off after a few.
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    page: Mapped["Page"] = relationship(back_populates="domain")

    @property
    def verified(self) -> bool:
        return self.verified_at is not None
