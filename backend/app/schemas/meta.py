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


class PublicConfig(BaseModel):
    """Limits the SPA needs before it talks to the API (no auth)."""

    max_avatar_kb: int
    avatar_types: list[str]
