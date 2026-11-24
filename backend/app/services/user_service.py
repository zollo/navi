"""User lookups, authentication and account changes."""
from __future__ import annotations

import uuid

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict
from app.core.security import decode_access_token, hash_password, verify_password
from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(
    db: AsyncSession, *, email: str, password: str, display_name: str = ""
) -> User:
    if await get_by_email(db, email):
        raise Conflict("Email already registered")
    user = User(
        email=email.lower(),
        display_name=display_name or email.split("@")[0],
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession, user: User, *, display_name: str | None, password: str | None
) -> User:
    if display_name is not None:
        user.display_name = display_name
    if password is not None:
        user.hashed_password = hash_password(password)
    await db.commit()
    await db.refresh(user)
    return user


async def resolve_token(db: AsyncSession, token: str) -> User | None:
    """Return the active user behind a session JWT."""
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, ValueError):
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user
