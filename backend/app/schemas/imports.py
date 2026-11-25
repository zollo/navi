"""Importing a page from another link-in-bio service."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.page import SectionIn, SocialLinkIn


class LinktreeImportIn(BaseModel):
    # A Linktree username ("name" or "@name") or page URL ("linktr.ee/name").
    source: str = Field(min_length=1, max_length=300)
    # Also fetch the profile picture, returned inline as a data: URL.
    include_avatar: bool = True


class PageImport(BaseModel):
    """A draft page built from someone's Linktree. Nothing is saved: the editor loads
    it so the user can review it, then saves it with `PUT /api/pages/me`."""

    source_url: str
    title: str
    tagline: str
    socials: list[SocialLinkIn]
    sections: list[SectionIn]
    # The profile picture as a data: URL (PNG/JPEG/WebP/GIF within MAX_AVATAR_KB), or
    # null. Upload it with `PUT /api/pages/me/avatar` to keep it.
    avatar_data_url: str | None = None
    # Things that couldn't be brought over (unsupported link types, limits, ...).
    warnings: list[str] = Field(default_factory=list)
