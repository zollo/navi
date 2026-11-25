"""Password hashing and session JWT helpers."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import settings

# Personal API keys (REST and MCP) start with this, so they're easy to spot and
# can't be confused with a session JWT.
API_KEY_PREFIX = "navi_"


def hash_password(password: str) -> str:
    # bcrypt only looks at the first 72 bytes; truncate explicitly (bcrypt>=5 raises).
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str | uuid.UUID, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """SHA-256 of the key: keys are long and random, so a slow hash adds nothing."""
    return hashlib.sha256(key.encode()).hexdigest()


def is_api_key(token: str) -> bool:
    return token.startswith(API_KEY_PREFIX)
