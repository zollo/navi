from __future__ import annotations

from tests.conftest import register
from tests.test_pages import PAGE, PNG


def _upload(client, headers, name="Sunset", dark="true", data=PNG, ctype="image/png"):
    return client.post(
        "/api/admin/backgrounds",
        headers=headers,
        data={"name": name, "dark": dark},
        files={"file": ("bg.png", data, ctype)},
    )


def test_admin_from_config(client, admin, alice):
    assert client.get("/api/auth/me", headers=admin).json()["is_admin"] is True
    assert client.get("/api/auth/me", headers=alice).json()["is_admin"] is False
    # Granted on sign-in too, not only at registration.
    login = client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "password-123"}
    )
    assert login.json()["user"]["is_admin"] is True


def test_only_admins_manage_backgrounds(client, admin, alice):
    assert _upload(client, alice).status_code == 403
    assert _upload(client, {}).status_code == 401

    created = _upload(client, admin)
    assert created.status_code == 201, created.text
    bg = created.json()
    assert bg["name"] == "Sunset"
    assert bg["dark"] is True

    bg_id = bg["id"]
    assert client.patch(
        f"/api/admin/backgrounds/{bg_id}", headers=alice, json={"name": "x"}
    ).status_code == 403
    assert client.delete(f"/api/admin/backgrounds/{bg_id}", headers=alice).status_code == 403


def test_gallery_crud(client, admin):
    a = _upload(client, admin, name="  First ").json()
    b = _upload(client, admin, name="Second", dark="false").json()
    assert a["name"] == "First"
    assert _upload(client, admin, name="   ").status_code == 422
    assert _upload(client, admin, ctype="image/svg+xml", data=b"<svg/>").status_code == 422
    assert _upload(client, admin, data=b"x" * (9 * 1024)).status_code == 413

    gallery = client.get("/api/backgrounds").json()["backgrounds"]
    assert [g["name"] for g in gallery] == ["First", "Second"]
    assert gallery[1]["dark"] is False

    img = client.get(a["image_url"])
    assert img.status_code == 200
    assert img.content == PNG
    assert "immutable" in img.headers["cache-control"]

    renamed = client.patch(
        f"/api/admin/backgrounds/{b['id']}", headers=admin, json={"name": "Dusk", "dark": True}
    ).json()
    assert renamed["name"] == "Dusk"
    assert renamed["dark"] is True

    assert client.delete(f"/api/admin/backgrounds/{a['id']}", headers=admin).status_code == 204
    assert client.get(a["image_url"]).status_code == 404
    assert client.delete(f"/api/admin/backgrounds/{a['id']}", headers=admin).status_code == 404
    assert [g["name"] for g in client.get("/api/backgrounds").json()["backgrounds"]] == ["Dusk"]


def test_page_uses_curated_background(client, admin, alice):
    bg = _upload(client, admin).json()
    theme = {"background": {"kind": "curated", "curated_id": bg["id"], "color": "#101010"}}
    resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": theme})
    assert resp.status_code == 201, resp.text
    page = resp.json()
    assert page["background_url"] == bg["image_url"]
    assert page["theme"]["background"]["curated_id"] == bg["id"]

    # An unknown background is refused.
    unknown = "00000000-0000-0000-0000-000000000000"
    missing = {"background": {"kind": "curated", "curated_id": unknown}}
    resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": missing})
    assert resp.status_code == 422

    # Deleting it from the gallery falls the page back to its color.
    client.delete(f"/api/admin/backgrounds/{bg['id']}", headers=admin)
    page = client.get("/api/pages/the.saasy.engineer").json()
    assert page["background_url"] is None
    assert page["theme"]["background"]["kind"] == "solid"
    assert page["theme"]["background"]["curated_id"] is None
    # And the editor can save what it read back.
    resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": page["theme"]})
    assert resp.status_code == 200, resp.text


def test_manage_command_grants_and_revokes(client, alice):
    from app.manage import main

    assert main(["admin", "ALICE@example.com"]) == 0
    assert client.get("/api/auth/me", headers=alice).json()["is_admin"] is True
    assert main(["admin", "alice@example.com", "--revoke"]) == 0
    assert client.get("/api/auth/me", headers=alice).json()["is_admin"] is False
    assert main(["admin", "nobody@example.com"]) == 1
    # Someone in ADMIN_EMAILS who registers later is an admin right away.
    other = register(client, "other-admin@example.com")
    assert client.get("/api/auth/me", headers=other).json()["is_admin"] is True
