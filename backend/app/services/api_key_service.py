"""Personal API keys: create, list, revoke, and resolve a key to its user."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Invalid, NotFound
from app.core.security import generate_api_key, hash_api_key
from app.models.api_key import ApiKey
from app.models.user import User

# Plenty for one person's tools; stops a script from minting keys without end.
MAX_KEYS_PER_USER = 25
# Record use at most this often, so busy MCP clients don't write on every call.
LAST_USED_RESOLUTION = timedelta(minutes=1)


async def list_keys(db: AsyncSession, user: User) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars())


async def create_key(db: AsyncSession, user: User, name: str) -> tuple[ApiKey, str]:
    """A new key for `user`. Returns the row and the full key, which is never stored."""
    if len(await list_keys(db, user)) >= MAX_KEYS_PER_USER:
        raise Invalid(f"You can have at most {MAX_KEYS_PER_USER} API keys; revoke one first")
    key = generate_api_key()
    row = ApiKey(user_id=user.id, name=name.strip(), prefix=key[:12], key_hash=hash_api_key(key))
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, key


async def revoke_key(db: AsyncSession, user: User, key_id: uuid.UUID) -> None:
    row = await db.get(ApiKey, key_id)
    if row is None or row.user_id != user.id:
        raise NotFound("API key not found")
    await db.delete(row)
    await db.commit()


async def resolve_key(db: AsyncSession, key: str) -> User | None:
    """The active user owning `key`, or None. Notes when the key was last used."""
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(key)))
    row = result.scalar_one_or_none()
    if row is None or not row.user.is_active:
        return None
    now = datetime.now(UTC)
    last = row.last_used_at
    if last is not None and last.tzinfo is None:  # SQLite drops the zone
        last = last.replace(tzinfo=UTC)
    if last is None or now - last >= LAST_USED_RESOLUTION:
        row.last_used_at = now
        await db.commit()
        await db.refresh(row.user)
    return row.user
