from __future__ import annotations

from tests.conftest import register


def test_register_login_and_me(client):
    register(client, "Carol@Example.com", "carol-password")
    resp = client.post(
        "/api/auth/login", json={"email": "carol@example.com", "password": "carol-password"}
    )
    assert resp.status_code == 200
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["email"] == "carol@example.com"


def test_duplicate_email_and_bad_password(client, alice):
    resp = client.post(
        "/api/auth/register", json={"email": "alice@example.com", "password": "whatever-123"}
    )
    assert resp.status_code == 409
    resp = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "nope"})
    assert resp.status_code == 401


def test_update_me(client, alice):
    resp = client.patch("/api/auth/me", headers=alice, json={"display_name": "Alice"})
    assert resp.json()["display_name"] == "Alice"
    client.patch("/api/auth/me", headers=alice, json={"password": "new-password-1"})
    resp = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "new-password-1"}
    )
    assert resp.status_code == 200


def test_requires_auth(client):
    assert client.get("/api/pages/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
