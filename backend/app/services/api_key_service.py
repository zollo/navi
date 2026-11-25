"""Personal API keys: create, list, revoke, and resolve a key to its user."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update
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
    # Lock the user's row so concurrent requests can't both pass the limit check
    # (FOR UPDATE on Postgres; SQLite serializes writers anyway).
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
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
    # Conditional update: concurrent requests write at most once per interval, and an
    # older request can't overwrite a newer timestamp.
    now = datetime.now(UTC)
    result = await db.execute(
        update(ApiKey)
        .where(
            ApiKey.id == row.id,
            or_(ApiKey.last_used_at.is_(None), ApiKey.last_used_at < now - LAST_USED_RESOLUTION),
        )
        .values(last_used_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount:
        await db.commit()
        await db.refresh(row.user)
    return row.user
