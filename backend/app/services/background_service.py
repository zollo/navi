"""The curated background gallery: anyone can list it, admins manage it."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.config import settings
from app.core.errors import Invalid, NotFound
from app.core.images import check_image
from app.models.background import Background
from app.models.page import Page
from app.schemas.background import MAX_NAME, BackgroundList, BackgroundRead, BackgroundUpdate


def to_read(bg: Background) -> BackgroundRead:
    return BackgroundRead(
        id=bg.id, name=bg.name, image_url=f"/api/backgrounds/{bg.id}/image", dark=bg.dark
    )


async def list_backgrounds(db: AsyncSession) -> BackgroundList:
    result = await db.execute(
        select(Background).order_by(Background.position, Background.created_at)
    )
    return BackgroundList(backgrounds=[to_read(b) for b in result.scalars()])


async def _get(db: AsyncSession, background_id: uuid.UUID) -> Background:
    bg = await db.get(Background, background_id)
    if bg is None:
        raise NotFound("Background not found")
    return bg


async def create(
    db: AsyncSession, *, name: str, dark: bool, data: bytes, content_type: str | None
) -> BackgroundRead:
    name = name.strip()
    if not name or len(name) > MAX_NAME:
        raise Invalid(f"Give the background a name of 1-{MAX_NAME} characters")
    ctype = check_image(
        data, content_type, max_bytes=settings.max_background_bytes, what="Background image"
    )
    last = await db.scalar(select(func.max(Background.position)))
    bg = Background(
        name=name, dark=dark, image=data, content_type=ctype, position=(last or 0) + 1
    )
    db.add(bg)
    await db.commit()
    await db.refresh(bg)
    return to_read(bg)


async def update_background(
    db: AsyncSession, background_id: uuid.UUID, data: BackgroundUpdate
) -> BackgroundRead:
    bg = await _get(db, background_id)
    if data.name is not None:
        bg.name = data.name
    if data.dark is not None:
        bg.dark = data.dark
    await db.commit()
    await db.refresh(bg)
    return to_read(bg)


async def delete(db: AsyncSession, background_id: uuid.UUID) -> None:
    bg = await _get(db, background_id)
    # The FK is ON DELETE SET NULL, but SQLite doesn't enforce it: clear it here
    # too. Pages that used it fall back to their background color.
    await db.execute(
        update(Page).where(Page.background_id == background_id).values(background_id=None)
    )
    await db.delete(bg)
    await db.commit()


async def get_image(db: AsyncSession, background_id: uuid.UUID) -> tuple[bytes, str]:
    result = await db.execute(
        select(Background)
        .where(Background.id == background_id)
        .options(undefer(Background.image))
    )
    bg = result.scalar_one_or_none()
    if bg is None:
        raise NotFound("Background not found")
    return bg.image, bg.content_type
