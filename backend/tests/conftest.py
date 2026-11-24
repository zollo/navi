"""Test fixtures: the real app against a throwaway SQLite database."""
from __future__ import annotations

import asyncio
import os
import tempfile

# Must be set before the app (and its settings/engine) is imported.
_DB_DIR = tempfile.mkdtemp(prefix="navi-test-")
# NAVI_TEST_DATABASE_URL runs the suite against a real Postgres instead.
os.environ["DATABASE_URL"] = os.environ.get(
    "NAVI_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{_DB_DIR}/test.db"
)
os.environ["DB_NULL_POOL"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["MAX_AVATAR_KB"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


async def _reset_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client():
    asyncio.run(_reset_db())
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str, password: str = "password-123") -> dict[str, str]:
    resp = client.post(
        "/api/auth/register", json={"email": email, "password": password, "display_name": "U"}
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def alice(client) -> dict[str, str]:
    return register(client, "alice@example.com")


@pytest.fixture
def bob(client) -> dict[str, str]:
    return register(client, "bob@example.com")
