"""Shared FastAPI dependencies: authentication."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import is_api_key
from app.db import get_db
from app.models.user import User
from app.services import user_service

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="A session token from POST /api/auth/login, or a personal API key (navi_…).",
)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise _credentials_error
    user = await user_service.resolve_token(db, creds.credentials)
    if user is None:
        raise _credentials_error
    return user


async def get_session_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
) -> User:
    """The caller, signed in with email + password. API keys are refused, so a leaked
    key can't mint more keys or change the account's password."""
    if creds is not None and is_api_key(creds.credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sign in with your password to do this; API keys can't",
        )
    return user


async def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """The caller if a valid bearer token was sent, else None."""
    if creds is None or not creds.credentials:
        return None
    return await user_service.resolve_token(db, creds.credentials)


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return user
