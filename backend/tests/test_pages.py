from __future__ import annotations

PAGE = {
    "handle": "@The.SaaSy.Engineer",
    "title": "@the.saasy.engineer",
    "tagline": "Your SaaSy Friend",
    "socials": [
        {"icon": "instagram", "url": "https://instagram.com/x"},
        {"icon": "email", "url": "mailto:me@example.com"},
    ],
    "sections": [
        {
            "title": "Social Media",
            "links": [
                {"title": "TikTok", "url": "https://tiktok.com/@x", "icon": "tiktok"},
                {"title": "GitHub", "url": "https://github.com/x", "icon": "github"},
            ],
        },
        {"title": "Misc", "links": [{"title": "Musical", "url": "https://example.com/v"}]},
    ],
}

# 1x1 transparent PNG
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def test_create_read_and_replace_page(client, alice):
    assert client.get("/api/pages/me", headers=alice).status_code == 404

    resp = client.put("/api/pages/me", headers=alice, json=PAGE)
    assert resp.status_code == 201, resp.text
    page = resp.json()
    assert page["handle"] == "the.saasy.engineer"
    assert [s["title"] for s in page["sections"]] == ["Social Media", "Misc"]
    assert [link["title"] for link in page["sections"][0]["links"]] == ["TikTok", "GitHub"]
    assert page["sections"][1]["links"][0]["icon"] == "link"
    assert page["avatar_url"] is None

    # Public, anonymous, case-insensitive.
    public = client.get("/api/pages/The.Saasy.Engineer")
    assert public.status_code == 200
    assert public.json()["socials"][1]["url"] == "mailto:me@example.com"

    # Saving again replaces everything and keeps the given order.
    update = {
        **PAGE,
        "sections": [{"title": "Only", "links": list(reversed(PAGE["sections"][0]["links"]))}],
    }
    resp = client.put("/api/pages/me", headers=alice, json=update)
    assert resp.status_code == 200
    sections = resp.json()["sections"]
    assert len(sections) == 1
    assert [link["title"] for link in sections[0]["links"]] == ["GitHub", "TikTok"]


def test_one_page_per_user_and_unique_handles(client, alice, bob):
    client.put("/api/pages/me", headers=alice, json=PAGE)
    resp = client.put("/api/pages/me", headers=bob, json=PAGE)
    assert resp.status_code == 409

    check = client.get("/api/pages/handles/the.saasy.engineer").json()
    assert check["available"] is False
    assert check["reason"] == "This handle is taken"
    # Your own handle is available to you.
    assert client.get("/api/pages/handles/the.saasy.engineer", headers=alice).json()["available"]

    # Renaming frees the old handle.
    client.put("/api/pages/me", headers=alice, json={**PAGE, "handle": "alice"})
    assert client.get("/api/pages/the.saasy.engineer").status_code == 404
    assert client.put("/api/pages/me", headers=bob, json=PAGE).status_code == 201


def test_handle_validation(client, alice):
    for bad in ("ab", "login", "icons", "handles", "-abc", "has space", "a..b", "x" * 31):
        resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "handle": bad})
        assert resp.status_code == 422, bad


def test_rejects_unsafe_urls(client, alice):
    link = {"title": "x", "url": "javascript:alert(1)"}
    bad = {**PAGE, "sections": [{"title": "", "links": [link]}]}
    assert client.put("/api/pages/me", headers=alice, json=bad).status_code == 422
    bad = {**PAGE, "socials": [{"icon": "github", "url": "data:text/html,hi"}]}
    assert client.put("/api/pages/me", headers=alice, json=bad).status_code == 422
    blank = {"title": "   ", "url": "https://example.com"}
    bad = {**PAGE, "sections": [{"title": "", "links": [blank]}]}
    assert client.put("/api/pages/me", headers=alice, json=bad).status_code == 422
    bad = {**PAGE, "socials": [{"icon": "not-an-icon", "url": "https://example.com"}]}
    assert client.put("/api/pages/me", headers=alice, json=bad).status_code == 422


def test_avatar(client, alice):
    files = {"file": ("a.png", PNG, "image/png")}
    assert client.put("/api/pages/me/avatar", headers=alice, files=files).status_code == 404

    client.put("/api/pages/me", headers=alice, json=PAGE)
    resp = client.put("/api/pages/me/avatar", headers=alice, files=files)
    assert resp.status_code == 200, resp.text
    url = resp.json()["avatar_url"]
    assert url.startswith("/api/pages/the.saasy.engineer/avatar?v=")
    assert url.endswith("-1")

    img = client.get(url)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    assert img.content == PNG

    text = {"file": ("a.svg", b"<svg/>", "image/svg+xml")}
    assert client.put("/api/pages/me/avatar", headers=alice, files=text).status_code == 422
    big = {"file": ("a.png", b"0" * 5000, "image/png")}
    assert client.put("/api/pages/me/avatar", headers=alice, files=big).status_code == 413

    assert client.delete("/api/pages/me/avatar", headers=alice).json()["avatar_url"] is None
    assert client.get(url).status_code == 404


def test_delete_page(client, alice):
    client.put("/api/pages/me", headers=alice, json=PAGE)
    assert client.delete("/api/pages/me", headers=alice).status_code == 204
    assert client.get("/api/pages/the.saasy.engineer").status_code == 404
    assert client.delete("/api/pages/me", headers=alice).status_code == 404


def test_icons(client):
    icons = client.get("/api/pages/icons").json()["icons"]
    assert "github" in icons and "link" in icons
