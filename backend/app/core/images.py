"""Checks shared by every image upload (avatars, page and curated backgrounds)."""
from __future__ import annotations

from app.core.errors import Invalid, TooLarge

# No SVG: it can carry script.
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def check_image(data: bytes, content_type: str | None, *, max_bytes: int, what: str) -> str:
    """Validate an upload and return its normalized content type."""
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype not in IMAGE_TYPES:
        raise Invalid(f"{what} must be a PNG, JPEG, WebP or GIF image")
    if not data:
        raise Invalid(f"{what} is empty")
    if len(data) > max_bytes:
        raise TooLarge(f"{what} must be at most {max_bytes // 1024} KB")
    return ctype


def image_headers() -> dict[str, str]:
    return {"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"}
