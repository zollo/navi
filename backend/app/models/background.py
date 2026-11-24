"""Curated backgrounds: images admins upload for anyone to pick for their page."""
from __future__ import annotations

from sqlalchemy import Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.db import Base
from app.models.base import TimestampMixin, UUIDMixin


class Background(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "backgrounds"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Gallery order; new uploads go last.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Whether the image is mostly dark, so pages using it default to light text.
    dark: Mapped[bool] = mapped_column(default=True, nullable=False)
