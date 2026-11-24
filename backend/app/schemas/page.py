"""Page schemas.

The editor saves a whole page at once (`PUT /api/pages/me`): the header, the social
icons and every section with its links, in display order. That keeps reordering
and moving links between sections to a single request with no position bookkeeping.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.page import Icon

MAX_SECTIONS = 20
MAX_LINKS_PER_SECTION = 50
MAX_SOCIALS = 20


def _check_url(value: str) -> str:
    """Only web and mail links: rules out javascript:, data: and friends."""
    v = value.strip()
    lower = v.lower()
    if not (lower.startswith(("https://", "http://", "mailto:")) and len(v) > 8):
        raise ValueError("must start with https://, http:// or mailto:")
    return v


Url = Annotated[str, Field(min_length=1, max_length=2048), AfterValidator(_check_url)]


class SocialLinkIn(BaseModel):
    icon: Icon
    url: Url


class SocialLinkRead(SocialLinkIn):
    model_config = ConfigDict(from_attributes=True)
    url: str


class LinkIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    url: Url
    icon: Icon = Icon.link


class LinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    url: str
    icon: Icon


class SectionIn(BaseModel):
    title: str = Field(default="", max_length=80)
    links: list[LinkIn] = Field(default_factory=list, max_length=MAX_LINKS_PER_SECTION)


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    links: list[LinkRead]


class PageIn(BaseModel):
    handle: str = Field(min_length=3, max_length=30)
    title: str = Field(default="", max_length=80)
    tagline: str = Field(default="", max_length=300)
    socials: list[SocialLinkIn] = Field(default_factory=list, max_length=MAX_SOCIALS)
    sections: list[SectionIn] = Field(default_factory=list, max_length=MAX_SECTIONS)


class PageRead(BaseModel):
    """A page as anyone sees it at /<handle>."""

    model_config = ConfigDict(from_attributes=True)

    handle: str
    title: str
    tagline: str
    # Relative URL of the avatar image, or null when none was uploaded.
    avatar_url: str | None
    socials: list[SocialLinkRead]
    sections: list[SectionRead]
    updated_at: datetime


class HandleCheck(BaseModel):
    handle: str
    available: bool
    # Why it can't be used (invalid, reserved or taken); null when available.
    reason: str | None = None
