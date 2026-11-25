"""User lookups, authentication and account changes."""
from __future__ import annotations

import asyncio
import uuid

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import Conflict, NotFound
from app.core.security import decode_access_token, hash_password, is_api_key, verify_password
from app.models.user import User
from app.services import api_key_service


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def _grant_configured_admin(db: AsyncSession, user: User) -> User:
    """Make the user an admin if their email is in ADMIN_EMAILS."""
    if not user.is_admin and user.email in settings.admin_email_set:
        user.is_admin = True
        await db.commit()
        await db.refresh(user)
    return user


async def set_admin(db: AsyncSession, email: str, is_admin: bool) -> User:
    user = await get_by_email(db, email)
    if user is None:
        raise NotFound(f"No account with email {email}")
    user.is_admin = is_admin
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_by_email(db, email)
    if user is None or not user.is_active:
        return None
    # bcrypt is deliberately slow: keep it off the event loop.
    if not await asyncio.to_thread(verify_password, password, user.hashed_password):
        return None
    return await _grant_configured_admin(db, user)


async def create_user(
    db: AsyncSession, *, email: str, password: str, display_name: str = ""
) -> User:
    if await get_by_email(db, email):
        raise Conflict("Email already registered")
    user = User(
        email=email.lower(),
        display_name=display_name or email.split("@")[0],
        hashed_password=await asyncio.to_thread(hash_password, password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:  # a concurrent sign-up with the same email won
        await db.rollback()
        raise Conflict("Email already registered") from None
    await db.refresh(user)
    return await _grant_configured_admin(db, user)


async def update_user(
    db: AsyncSession, user: User, *, display_name: str | None, password: str | None
) -> User:
    if display_name is not None:
        user.display_name = display_name
    if password is not None:
        user.hashed_password = await asyncio.to_thread(hash_password, password)
    await db.commit()
    await db.refresh(user)
    return user


async def resolve_token(db: AsyncSession, token: str) -> User | None:
    """Return the active user behind a session JWT or a personal API key."""
    if is_api_key(token):
        user = await api_key_service.resolve_key(db, token)
        return await _grant_configured_admin(db, user) if user else None
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, ValueError):
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return await _grant_configured_admin(db, user)
