"""Reference data and build info schemas."""
from __future__ import annotations

from pydantic import BaseModel


class BuildInfo(BaseModel):
    version: str
    git_commit: str
    build_time: str
    environment: str
    public_url: str
    api_docs_url: str
    openapi_url: str


class IconList(BaseModel):
    icons: list[str]


class UploadLimits(BaseModel):
    """Upload size limits, so the SPA can shrink images before sending them."""

    max_avatar_kb: int
    max_background_kb: int
