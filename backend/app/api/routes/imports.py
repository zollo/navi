"""Importing a page from another link-in-bio service."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.imports import LinktreeImportIn, PageImport
from app.services import linktree_service

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/linktree", response_model=PageImport, operation_id="import_linktree")
async def import_linktree(
    payload: LinktreeImportIn, _user: User = Depends(get_current_user)
) -> PageImport:
    """Read a public Linktree page and return it as a draft Navi page.

    Nothing is saved. Load the draft into the editor, then save it with
    `PUT /api/pages/me` (and the avatar with `PUT /api/pages/me/avatar`).
    """
    return await linktree_service.import_linktree(
        payload.source, include_avatar=payload.include_avatar
    )
