"""Curated backgrounds: a public gallery, managed by admins."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.config import settings
from app.core.errors import TooLarge
from app.db import get_db
from app.models.user import User
from app.schemas.background import BackgroundList, BackgroundRead, BackgroundUpdate
from app.services import background_service

router = APIRouter(tags=["backgrounds"])


@router.get("/backgrounds", response_model=BackgroundList, operation_id="list_backgrounds")
async def list_backgrounds(db: AsyncSession = Depends(get_db)) -> BackgroundList:
    """The curated backgrounds anyone can pick for their page."""
    return await background_service.list_backgrounds(db)


@router.get(
    "/backgrounds/{background_id}/image",
    operation_id="get_background_image",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}},
)
async def get_background_image(
    background_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    """A curated background's image. Images never change, so it is cached for good."""
    data, content_type = await background_service.get_image(db, background_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/admin/backgrounds",
    response_model=BackgroundRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_background",
)
async def create_background(
    name: str = Form(..., max_length=200),
    dark: bool = Form(True),
    file: UploadFile = File(...),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> BackgroundRead:
    """Add a background to the gallery (admins; multipart `file`, `name`, `dark`)."""
    data = await file.read(settings.max_background_bytes + 1)
    if len(data) > settings.max_background_bytes:
        raise TooLarge(f"Background image must be at most {settings.max_background_kb} KB")
    return await background_service.create(
        db, name=name, dark=dark, data=data, content_type=file.content_type
    )


@router.patch(
    "/admin/backgrounds/{background_id}",
    response_model=BackgroundRead,
    operation_id="update_background",
)
async def update_background(
    background_id: uuid.UUID,
    payload: BackgroundUpdate,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> BackgroundRead:
    """Rename a background or change whether it counts as dark (admins)."""
    return await background_service.update_background(db, background_id, payload)


@router.delete(
    "/admin/backgrounds/{background_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_background",
)
async def delete_background(
    background_id: uuid.UUID,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a background from the gallery (admins). Pages using it fall back to
    their background color."""
    await background_service.delete(db, background_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
