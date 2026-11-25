"""Pages: public reads by handle, and the caller's own page."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user
from app.config import settings
from app.core.errors import TooLarge
from app.core.images import image_headers
from app.db import get_db
from app.models.page import Icon
from app.models.user import User
from app.schemas.meta import IconList
from app.schemas.page import HandleCheck, PageIn, PageRead
from app.services import page_service

router = APIRouter(prefix="/pages", tags=["pages"])


# Routes under /me and /handles are declared before /{handle} so they win.
@router.get("/me", response_model=PageRead, operation_id="get_my_page")
async def get_my_page(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PageRead:
    """Your page, or 404 if you haven't created it yet."""
    return await page_service.my_page(db, user)


@router.put(
    "/me",
    response_model=PageRead,
    operation_id="save_my_page",
    responses={201: {"model": PageRead, "description": "Page created"}},
)
async def save_my_page(
    payload: PageIn,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageRead:
    """Create your page, or replace its handle, header, social icons and sections.

    Send the whole page: sections and links not in the request are removed, and list
    order is display order.
    """
    page, created = await page_service.save_page(db, user, payload)
    if created:
        response.status_code = status.HTTP_201_CREATED
    return page


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_my_page")
async def delete_my_page(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Delete your page. Your account stays, and you can create a new page later."""
    await page_service.delete_page(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/me/avatar", response_model=PageRead, operation_id="upload_my_avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageRead:
    """Upload a PNG, JPEG, WebP or GIF avatar (multipart `file`)."""
    data = await file.read(settings.max_avatar_bytes + 1)
    if len(data) > settings.max_avatar_bytes:
        raise TooLarge(f"Avatar must be at most {settings.max_avatar_kb} KB")
    return await page_service.set_avatar(db, user, data, file.content_type)


@router.delete("/me/avatar", response_model=PageRead, operation_id="delete_my_avatar")
async def delete_my_avatar(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PageRead:
    """Remove your avatar."""
    return await page_service.clear_avatar(db, user)


@router.put("/me/background", response_model=PageRead, operation_id="upload_my_background")
async def upload_my_background(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PageRead:
    """Upload a PNG, JPEG, WebP or GIF background image (multipart `file`).

    It shows once the page is saved with `theme.background.kind` = `image`.
    """
    data = await file.read(settings.max_background_bytes + 1)
    if len(data) > settings.max_background_bytes:
        raise TooLarge(f"Background image must be at most {settings.max_background_kb} KB")
    return await page_service.set_background(db, user, data, file.content_type)


@router.delete("/me/background", response_model=PageRead, operation_id="delete_my_background")
async def delete_my_background(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PageRead:
    """Remove your background image. A page showing it falls back to its color."""
    return await page_service.clear_background(db, user)


@router.get("/icons", response_model=IconList, operation_id="list_icons")
async def list_icons() -> IconList:
    """Icon names accepted for social icons and links."""
    return IconList(icons=[i.value for i in Icon])


@router.get(
    "/handles/{handle}",
    response_model=HandleCheck,
    operation_id="check_handle",
    # Anonymous works; signed in, your own current handle counts as available.
    openapi_extra={"security": [{"HTTPBearer": []}, {}]},
)
async def check_handle(
    handle: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> HandleCheck:
    """Whether a handle can be used for a page."""
    return await page_service.check_handle(db, handle, user)


@router.get("/{handle}", response_model=PageRead, operation_id="get_page")
async def get_page(handle: str, db: AsyncSession = Depends(get_db)) -> PageRead:
    """A public page by handle (no authentication)."""
    return await page_service.public_page(db, handle)


@router.get(
    "/{handle}/avatar",
    operation_id="get_avatar",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}},
)
async def get_avatar(handle: str, db: AsyncSession = Depends(get_db)) -> Response:
    """A page's avatar image. URLs carry `?v=` so they can be cached for a long time."""
    data, content_type = await page_service.get_avatar(db, handle)
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{handle}/background",
    operation_id="get_page_background",
    response_class=Response,
    responses={200: {"content": {"image/*": {}}}},
)
async def get_page_background(handle: str, db: AsyncSession = Depends(get_db)) -> Response:
    """A page's own background image. URLs carry `?v=` so they can be cached."""
    data, content_type = await page_service.get_background(db, handle)
    return Response(content=data, media_type=content_type, headers=image_headers())
