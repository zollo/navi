"""Pages: one per user, public at /<handle>, edited as a whole."""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.config import settings
from app.core.errors import Conflict, Invalid, NotFound, TooLarge
from app.models.page import Link, Page, Section, SocialLink
from app.models.user import User
from app.schemas.page import HandleCheck, PageIn, PageRead

# Lowercase letters, digits, dots, underscores and hyphens; starts and ends with a
# letter or digit, e.g. "the.saasy.engineer".
HANDLE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,28})[a-z0-9]$")

# Handles that would shadow a route of the SPA, the API or nginx, or that could be
# mistaken for the service itself. Pages live at /<handle>, so keep this in sync
# with frontend/src/App.tsx and frontend/nginx.conf.
RESERVED_HANDLES = frozenset(
    {
        "about", "account", "admin", "api", "app", "assets", "auth", "dashboard",
        "docs", "edit", "editor", "favicon.svg", "help", "home", "index.html",
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


async def get_for_user(db: AsyncSession, user: User) -> Page | None:
    result = await db.execute(select(Page).where(Page.user_id == user.id))
    return result.scalar_one_or_none()


async def check_handle(db: AsyncSession, handle: str, user: User | None = None) -> HandleCheck:
    norm = normalize_handle(handle)
    problem = handle_problem(norm)
    if problem is None:
        page = await get_by_handle(db, norm)
        if page is not None and (user is None or page.user_id != user.id):
            problem = HANDLE_TAKEN
    return HandleCheck(handle=norm, available=problem is None, reason=problem)


def to_read(page: Page) -> PageRead:
    avatar_url = (
        f"/api/pages/{page.handle}/avatar?v={page.avatar_version}" if page.has_avatar else None
    )
    return PageRead(
        handle=page.handle,
        title=page.title,
        tagline=page.tagline,
        avatar_url=avatar_url,
        socials=page.socials,  # type: ignore[arg-type]
        sections=page.sections,  # type: ignore[arg-type]
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
    check = await check_handle(db, data.handle, user)
    if not check.available:
        if check.reason == HANDLE_TAKEN:
            raise Conflict(HANDLE_TAKEN)
        raise Invalid(check.reason or "Invalid handle")

    page = await get_for_user(db, user)
    created = page is None
    if page is None:
        page = Page(user_id=user.id)
        db.add(page)

    page.handle = check.handle
    page.title = data.title.strip()
    page.tagline = data.tagline.strip()
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
    except IntegrityError:  # someone claimed the handle between the check and the commit
        await db.rollback()
        raise Conflict(HANDLE_TAKEN) from None
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
