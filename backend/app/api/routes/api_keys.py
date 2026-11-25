"""Personal API keys for the REST API and the MCP server at /mcp.

Managing keys needs a password sign-in: an API key can't list, create or revoke keys.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_user
from app.db import get_db
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead
from app.services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead], operation_id="list_api_keys")
async def list_api_keys(
    user: User = Depends(get_session_user), db: AsyncSession = Depends(get_db)
) -> list[ApiKeyRead]:
    """Your API keys, newest first (names and prefixes; never the keys themselves)."""
    return [ApiKeyRead.model_validate(k) for k in await api_key_service.list_keys(db, user)]


@router.post(
    "",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_api_key",
)
async def create_api_key(
    payload: ApiKeyCreate,
    user: User = Depends(get_session_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    """Create a key. The full key is returned once; only its hash is stored."""
    row, key = await api_key_service.create_key(db, user, payload.name)
    return ApiKeyCreated(**ApiKeyRead.model_validate(row).model_dump(), key=key)


@router.delete(
    "/{key_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="revoke_api_key"
)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: User = Depends(get_session_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a key. Anything using it stops working at once."""
    await api_key_service.revoke_key(db, user, key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
