"""A user's public links page: profile header, social icons and link sections."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, UUIDMixin, str_enum

if TYPE_CHECKING:
    from app.models.domain import CustomDomain


class Icon(enum.StrEnum):
    """Icons for social buttons and link cards. Stored as VARCHAR: adding one needs
    no migration, only the enum value and an entry in the frontend's `lib/icons.tsx`."""

    link = "link"
    website = "website"
    email = "email"
    video = "video"
    music = "music"
    podcast = "podcast"
    blog = "blog"
    shop = "shop"
    calendar = "calendar"
    instagram = "instagram"
    threads = "threads"
    x = "x"
    twitter = "twitter"
    tiktok = "tiktok"
    linkedin = "linkedin"
    github = "github"
    youtube = "youtube"
    facebook = "facebook"
    twitch = "twitch"
    discord = "discord"
    signal = "signal"
    whatsapp = "whatsapp"
    telegram = "telegram"
    mastodon = "mastodon"
    bluesky = "bluesky"
    reddit = "reddit"
    spotify = "spotify"


class Page(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pages"

    # One page per user, enforced by the unique constraint.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Public address: /<handle>. Lowercase; see page_service.HANDLE_RE / RESERVED_HANDLES.
    handle: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    tagline: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Avatar bytes live in Postgres so the API stays stateless (no shared volume).
    avatar: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))
    avatar_content_type: Mapped[str | None] = mapped_column(String(64))
    # Bumped on every avatar upload; the SPA appends it to the URL to bust caches.
    avatar_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    socials: Mapped[list["SocialLink"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="SocialLink.position",
        lazy="selectin",
    )
    sections: Mapped[list["Section"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="Section.position",
        lazy="selectin",
    )

    # Optional custom domain; deleted with the page.
    domain: Mapped["CustomDomain | None"] = relationship(
        back_populates="page", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def has_avatar(self) -> bool:
        return self.avatar_content_type is not None


class SocialLink(UUIDMixin, Base):
    """An icon in the row under the tagline."""

    __tablename__ = "social_links"

    page_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icon: Mapped[Icon] = mapped_column(str_enum(Icon, "icon"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    page: Mapped["Page"] = relationship(back_populates="socials")


class Section(UUIDMixin, Base):
    """A heading (e.g. "Social Media") grouping link cards. The title may be empty."""

    __tablename__ = "sections"

    page_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(80), nullable=False, default="")

    page: Mapped["Page"] = relationship(back_populates="sections")
    links: Mapped[list["Link"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Link.position",
        lazy="selectin",
    )


class Link(UUIDMixin, Base):
    """A link card: icon on the left, centered title."""

    __tablename__ = "links"

    section_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    icon: Mapped[Icon] = mapped_column(str_enum(Icon, "icon"), nullable=False, default=Icon.link)

    section: Mapped["Section"] = relationship(back_populates="links")
