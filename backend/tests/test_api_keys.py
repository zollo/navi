"""Personal API keys: shown once, hashed at rest, usable as a bearer token, revocable."""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.api_key import ApiKey


def _create(client, headers, name="Claude"):
    resp = client.post("/api/api-keys", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_list_use_and_revoke(client, alice):
    created = _create(client, alice)
    key = created["key"]
    assert key.startswith("navi_") and len(key) > 40
    assert created["prefix"] == key[:12]

    # Listed without the key itself.
    listed = client.get("/api/api-keys", headers=alice).json()
    assert [k["name"] for k in listed] == ["Claude"]
    assert "key" not in listed[0]
    assert listed[0]["last_used_at"] is None

    # Only a hash is stored.
    async def stored() -> list[ApiKey]:
        async with AsyncSessionLocal() as db:
            return list((await db.execute(select(ApiKey))).scalars())

    rows = asyncio.run(stored())
    assert len(rows) == 1 and key not in (rows[0].key_hash, rows[0].prefix)

    # Works as a bearer token for the REST API, and records the use.
    as_key = {"Authorization": f"Bearer {key}"}
    me = client.get("/api/auth/me", headers=as_key)
    assert me.status_code == 200 and me.json()["email"] == "alice@example.com"
    assert client.get("/api/api-keys", headers=alice).json()[0]["last_used_at"] is not None

    assert client.delete(f"/api/api-keys/{created['id']}", headers=alice).status_code == 204
    assert client.get("/api/auth/me", headers=as_key).status_code == 401
    assert client.get("/api/api-keys", headers=alice).json() == []


def test_keys_cannot_manage_keys_or_change_password(client, alice):
    as_key = {"Authorization": f"Bearer {_create(client, alice)['key']}"}
    assert client.get("/api/api-keys", headers=as_key).status_code == 403
    assert client.post("/api/api-keys", json={"name": "x"}, headers=as_key).status_code == 403
    resp = client.patch("/api/auth/me", json={"password": "hijacked-123"}, headers=as_key)
    assert resp.status_code == 403
    # Editing the page with a key is fine.
    page = {"handle": "alice", "title": "Alice", "sections": []}
    assert client.put("/api/pages/me", json=page, headers=as_key).status_code == 201


def test_keys_are_per_user(client, alice, bob):
    created = _create(client, alice)
    assert client.get("/api/api-keys", headers=bob).json() == []
    assert client.delete(f"/api/api-keys/{created['id']}", headers=bob).status_code == 404
    assert client.get("/api/api-keys", headers=alice).json()[0]["id"] == created["id"]


def test_bad_keys_are_rejected(client, alice):
    _create(client, alice)
    for token in ("navi_not-a-real-key", "navi_"):
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    assert client.post("/api/api-keys", json={"name": ""}, headers=alice).status_code == 422


def test_key_limit(client, alice, monkeypatch):
    from app.services import api_key_service

    monkeypatch.setattr(api_key_service, "MAX_KEYS_PER_USER", 2)
    _create(client, alice, "a")
    _create(client, alice, "b")
    resp = client.post("/api/api-keys", json={"name": "c"}, headers=alice)
    assert resp.status_code == 422 and "at most 2" in resp.json()["detail"]


def test_last_used_is_throttled(client, alice):
    as_key = {"Authorization": f"Bearer {_create(client, alice)['key']}"}
    client.get("/api/auth/me", headers=as_key)
    first = client.get("/api/api-keys", headers=alice).json()[0]["last_used_at"]
    client.get("/api/auth/me", headers=as_key)
    assert client.get("/api/api-keys", headers=alice).json()[0]["last_used_at"] == first


def test_access_log_redacts_keys():
    import logging

    from app.main import _RedactKeys

    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4", "POST", "/mcp?key=navi_secret&x=1", "1.1", 200), None,
    )
    _RedactKeys().filter(record)
    assert "navi_secret" not in record.getMessage()
    assert "/mcp?key=[redacted]&x=1" in record.getMessage()
