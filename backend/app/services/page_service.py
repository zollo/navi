"""Pages: one per user, public at /<handle>, edited as a whole."""
from __future__ import annotations

import re

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.config import settings
from app.core.errors import Conflict, Invalid, NotFound, TooLarge
from app.core.images import check_image
from app.models.background import Background
from app.models.page import Link, Page, Section, SocialLink
from app.models.user import User
from app.schemas.page import HandleCheck, PageIn, PageRead
from app.schemas.theme import BackgroundKind, Theme

# Lowercase letters, digits, dots, underscores and hyphens; starts and ends with a
# letter or digit, e.g. "the.saasy.engineer".
HANDLE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,28})[a-z0-9]$")

# Handles that would shadow a route of the SPA, nginx or the fixed /api/pages/*
# routes (icons, handles, me), or that could be mistaken for the service itself.
# Pages live at /<handle>, so keep this in sync with frontend/src/App.tsx,
# frontend/nginx.conf and frontend/src/lib/page.ts.
RESERVED_HANDLES = frozenset(
    {
        "about", "account", "admin", "api", "app", "assets", "auth", "dashboard",
        "docs", "edit", "editor", "favicon.svg", "handles", "help", "home", "icons",
        "index.html",
        "login", "logout", "me", "navi", "new", "openapi.json", "privacy", "redoc",
        "register", "root", "settings", "signin", "signup", "static", "support",
        "terms", "www",
    }
)

HANDLE_TAKEN = "This handle is taken"
AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def normalize_handle(handle: str) -> str:
    return handle.strip().lstrip("@").lower()


def handle_problem(handle: str) -> str | None:
    """Why `handle` (already normalized) can't be used, ignoring who owns it."""
    if not HANDLE_RE.match(handle) or ".." in handle:
        return (
            "Use 3-30 lowercase letters, digits, dots, underscores or hyphens, "
            "starting and ending with a letter or digit"
        )
    if handle in RESERVED_HANDLES:
        return "This handle is reserved"
    return None


async def get_by_handle(db: AsyncSession, handle: str) -> Page | None:
    result = await db.execute(select(Page).where(Page.handle == normalize_handle(handle)))
    return result.scalar_one_or_none()


async def get_for_user(db: AsyncSession, user: User, *, lock: bool = False) -> Page | None:
    stmt = select(Page).where(Page.user_id == user.id)
    if lock:
        # Row lock (Postgres) so concurrent saves of one page run one at a time and
        # each sees the other's children; populate_existing reloads them after it.
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_handle(db: AsyncSession, handle: str, user: User | None = None) -> HandleCheck:
    norm = normalize_handle(handle)
    problem = handle_problem(norm)
    if problem is None:
        page = await get_by_handle(db, norm)
        if page is not None and (user is None or page.user_id != user.id):
            problem = HANDLE_TAKEN
    return HandleCheck(handle=norm, available=problem is None, reason=problem)


def custom_background_url(page: Page) -> str | None:
    if not page.has_background:
        return None
    return f"/api/pages/{page.handle}/background?v={page.id.hex[:12]}-{page.background_version}"


def page_theme(page: Page) -> tuple[Theme, str | None]:
    """The page's theme and the URL of its background image, if it shows one.

    If the image is gone (removed, or deleted from the gallery) the background
    falls back to its color, or to the default.
    """
    try:
        theme = Theme.model_validate(page.theme or {})
    except ValidationError:  # stored by an older or newer version: start over
        theme = Theme()
    bg = theme.background
    if bg.kind == BackgroundKind.curated and bg.curated_id and bg.curated_id == page.background_id:
        return theme, f"/api/backgrounds/{page.background_id}/image"
    if bg.kind == BackgroundKind.image and page.has_background:
        return theme, custom_background_url(page)
    if bg.kind in (BackgroundKind.image, BackgroundKind.curated):
        kind = BackgroundKind.solid if bg.color else BackgroundKind.default
        bg = bg.model_copy(update={"kind": kind, "curated_id": None})
        theme = theme.model_copy(update={"background": bg})
    return theme, None


def to_read(page: Page) -> PageRead:
    # The page id is in the cache key too: a freed handle can be claimed by
    # another page whose avatar_version restarts at 1.
    avatar_url = (
        f"/api/pages/{page.handle}/avatar?v={page.id.hex[:12]}-{page.avatar_version}"
        if page.has_avatar
        else None
    )
    theme, background_url = page_theme(page)
    return PageRead(
        handle=page.handle,
        title=page.title,
        tagline=page.tagline,
        avatar_url=avatar_url,
        socials=page.socials,  # type: ignore[arg-type]
        sections=page.sections,  # type: ignore[arg-type]
        theme=theme,
        background_url=background_url,
        custom_background_url=custom_background_url(page),
        updated_at=page.updated_at,
    )


async def public_page(db: AsyncSession, handle: str) -> PageRead:
    page = await get_by_handle(db, handle)
    if page is None:
        raise NotFound("Page not found")
    return to_read(page)


async def my_page(db: AsyncSession, user: User) -> PageRead:
    page = await get_for_user(db, user)
    if page is None:
        raise NotFound("You haven't created your page yet")
    return to_read(page)


async def save_page(db: AsyncSession, user: User, data: PageIn) -> tuple[PageRead, bool]:
    """Create the caller's page or replace its contents. Returns (page, created)."""
    # Lock first, before anything loads the page's children.
    page = await get_for_user(db, user, lock=True)
    check = await check_handle(db, data.handle, user)
    if not check.available:
        if check.reason == HANDLE_TAKEN:
            raise Conflict(HANDLE_TAKEN)
        raise Invalid(check.reason or "Invalid handle")

    bg = data.theme.background
    if bg.kind == BackgroundKind.curated and await db.get(Background, bg.curated_id) is None:
        raise Invalid("That background is no longer in the gallery. Pick another one.")
    if bg.kind == BackgroundKind.image and (page is None or not page.has_background):
        raise Invalid("Upload a background image first")

    created = page is None
    if page is None:
        page = Page(user_id=user.id)
        db.add(page)

    page.handle = check.handle
    page.title = data.title.strip()
    page.tagline = data.tagline.strip()
    page.theme = data.theme.model_dump(mode="json")
    page.background_id = bg.curated_id if bg.kind == BackgroundKind.curated else None
    # Child rows don't touch the page row, so bump its timestamp explicitly.
    page.updated_at = func.now()
    # Replace children wholesale; delete-orphan removes the old rows.
    page.socials = [
        SocialLink(position=i, icon=s.icon, url=s.url) for i, s in enumerate(data.socials)
    ]
    page.sections = [
        Section(
            position=i,
            title=s.title.strip(),
            links=[
                Link(position=j, title=link.title.strip(), url=link.url, icon=link.icon)
                for j, link in enumerate(s.links)
            ],
        )
        for i, s in enumerate(data.sections)
    ]
    try:
        await db.commit()
    except IntegrityError:
        # Someone claimed the handle between the check and the commit, or a
        # concurrent request created this user's page first.
        await db.rollback()
        raise Conflict(f"{HANDLE_TAKEN}, or your page was just saved elsewhere. "
                       "Reload and try again.") from None
    # Timestamps are server-side; the children are already in memory, in order.
    await db.refresh(page, attribute_names=["created_at", "updated_at"])
    return to_read(page), created


async def delete_page(db: AsyncSession, user: User) -> None:
    page = await get_for_user(db, user)
    if page is None:
        raise NotFound("You haven't created your page yet")
    await db.delete(page)
    await db.commit()


async def set_avatar(
    db: AsyncSession, user: User, data: bytes, content_type: str | None
) -> PageRead:
    page = await get_for_user(db, user)
    if page is None:
        raise NotFound("Create your page before adding an avatar")
    content_type = (content_type or "").split(";")[0].strip().lower()
    if content_type not in AVATAR_TYPES:
        raise Invalid("Avatar must be a PNG, JPEG, WebP or GIF image")
    if len(data) > settings.max_avatar_bytes:
        raise TooLarge(f"Avatar must be at most {settings.max_avatar_kb} KB")
    page.avatar = data
    page.avatar_content_type = content_type
    page.avatar_version += 1
    await db.commit()
    await db.refresh(page)
    return to_read(page)


async def clear_avatar(db: AsyncSession, user: User) -> PageRead:
    page = await get_for_user(db, user)
    if page is None:
        raise NotFound("You haven't created your page yet")
    page.avatar = None
    page.avatar_content_type = None
    page.avatar_version += 1
    await db.commit()
    await db.refresh(page)
    return to_read(page)


async def get_avatar(db: AsyncSession, handle: str) -> tuple[bytes, str]:
    result = await db.execute(
        select(Page).where(Page.handle == normalize_handle(handle)).options(undefer(Page.avatar))
    )
    page = result.scalar_one_or_none()
    if page is None or page.avatar is None or page.avatar_content_type is None:
        raise NotFound("No avatar")
    return page.avatar, page.avatar_content_type


async def set_background(
    db: AsyncSession, user: User, data: bytes, content_type: str | None
) -> PageRead:
    """Store the page's own background image. Show it by saving the page with a
    background of kind "image"."""
    page = await get_for_user(db, user)
    if page is None:
        raise NotFound("Create your page before adding a background")
    ctype = check_image(
        data, content_type, max_bytes=settings.max_background_bytes, what="Background image"
    )
    page.background = data
    page.background_content_type = ctype
    page.background_version += 1
    await db.commit()
    await db.refresh(page)
    return to_read(page)


async def clear_background(db: AsyncSession, user: User) -> PageRead:
    page = await get_for_user(db, user)
    if page is None:
        raise NotFound("You haven't created your page yet")
    page.background = None
    page.background_content_type = None
    page.background_version += 1
    await db.commit()
    await db.refresh(page)
    return to_read(page)


async def get_background(db: AsyncSession, handle: str) -> tuple[bytes, str]:
    result = await db.execute(
        select(Page)
        .where(Page.handle == normalize_handle(handle))
        .options(undefer(Page.background))
    )
    page = result.scalar_one_or_none()
    if page is None or page.background is None or page.background_content_type is None:
        raise NotFound("No background image")
    return page.background, page.background_content_type
