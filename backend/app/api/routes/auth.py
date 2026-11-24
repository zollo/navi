"""Authentication: email + password login, self-registration, the current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.core.security import create_access_token
from app.db import get_db
from app.models.user import User
from app.schemas.user import (
    AuthConfig,
    LoginRequest,
    RegisterRequest,
    Token,
    UserRead,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User) -> Token:
    return Token(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/login", response_model=Token, operation_id="login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Exchange email + password for a bearer token."""
    user = await user_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return _token_for(user)


@router.post(
    "/register", response_model=Token, status_code=status.HTTP_201_CREATED, operation_id="register"
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Self-service sign-up (if enabled)."""
    if not settings.allow_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    user = await user_service.create_user(
        db, email=payload.email, password=payload.password, display_name=payload.display_name
    )
    return _token_for(user)


@router.get("/me", response_model=UserRead, operation_id="whoami")
async def me(user: User = Depends(get_current_user)) -> User:
    """The authenticated user."""
    return user


@router.patch("/me", response_model=UserRead, operation_id="update_me")
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Change your display name or password."""
    return await user_service.update_user(
        db, user, display_name=payload.display_name, password=payload.password
    )


@router.get("/config", response_model=AuthConfig, operation_id="auth_config")
async def auth_config() -> AuthConfig:
    """Tells the sign-in page which options to render."""
    return AuthConfig(registration_enabled=settings.allow_registration)
