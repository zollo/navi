from __future__ import annotations

from tests.test_pages import PAGE, PNG

THEME = {
    "background": {
        "kind": "gradient",
        "gradient_from": "#FF0080",
        "gradient_to": "#7928ca",
        "gradient_angle": 135,
    },
    "font": "playfair",
    "text_color": "#ffffff",
    "button_style": "glass",
    "button_shape": "pill",
    "button_color": "#ffffff",
    "button_text_color": "#111111",
    "avatar_shape": "rounded",
    "avatar_border": {
        "kind": "gradient",
        "gradient_from": "#F58529",
        "gradient_to": "#dd2a7b",
        "width": 6,
    },
    "content_background": {"kind": "solid", "color": "#000000", "opacity": 40},
}


def test_default_theme(client, alice):
    page = client.put("/api/pages/me", headers=alice, json=PAGE).json()
    assert page["theme"]["background"]["kind"] == "default"
    assert page["theme"]["font"] == "system"
    assert page["theme"]["text_color"] is None
    assert page["theme"]["button_shape"] == "rounded"
    assert page["background_url"] is None
    assert page["theme"]["avatar_border"]["kind"] == "none"
    assert page["theme"]["content_background"] == {
        "kind": "none",
        "color": None,
        "gradient_from": None,
        "gradient_to": None,
        "gradient_angle": 180,
        "opacity": 80,
    }


def test_save_and_read_theme(client, alice):
    resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": THEME})
    assert resp.status_code == 201, resp.text
    theme = client.get("/api/pages/the.saasy.engineer").json()["theme"]
    assert theme["background"]["gradient_from"] == "#ff0080"  # normalized
    assert theme["background"]["gradient_angle"] == 135
    assert theme["font"] == "playfair"
    assert theme["button_style"] == "glass"
    assert theme["avatar_shape"] == "rounded"
    assert theme["avatar_border"]["gradient_from"] == "#f58529"
    assert theme["avatar_border"]["width"] == 6
    assert theme["content_background"]["kind"] == "solid"
    assert theme["content_background"]["opacity"] == 40

    # Saving without a theme resets the look, like every other omitted field.
    client.put("/api/pages/me", headers=alice, json=PAGE)
    assert client.get("/api/pages/me", headers=alice).json()["theme"]["font"] == "system"


def test_theme_validation(client, alice):
    bad = [
        {"text_color": "red"},
        {"text_color": "#12345"},
        {"text_color": "#ggg000"},
        {"font": "comic-sans"},
        {"button_shape": "blob"},
        {"background": {"kind": "solid"}},
        {"background": {"kind": "gradient", "gradient_from": "#000000"}},
        {"background": {"kind": "solid", "color": "#000000", "gradient_angle": 361}},
        {"background": {"kind": "curated"}},
        {"background": {"kind": "video"}},
        {"avatar_border": {"kind": "solid"}},
        {"avatar_border": {"kind": "gradient", "gradient_from": "#000000"}},
        {"avatar_border": {"kind": "solid", "color": "#000000", "width": 0}},
        {"avatar_border": {"kind": "solid", "color": "#000000", "width": 17}},
        {"avatar_border": {"kind": "dotted"}},
        {"content_background": {"kind": "solid"}},
        {"content_background": {"kind": "gradient", "gradient_to": "#000000"}},
        {"content_background": {"kind": "solid", "color": "#000000", "opacity": 101}},
        {"content_background": {"kind": "solid", "color": "#000000", "opacity": -1}},
        {"content_background": {"kind": "image"}},
    ]
    for theme in bad:
        resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": theme})
        assert resp.status_code == 422, theme


def test_background_image(client, alice):
    image_theme = {"background": {"kind": "image", "color": "#202020", "image_dark": True}}
    # No page yet, and no image yet.
    assert client.put(
        "/api/pages/me/background", headers=alice, files={"file": ("b.png", PNG, "image/png")}
    ).status_code == 404
    resp = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": image_theme})
    assert resp.status_code == 422
    assert "Upload a background image" in resp.json()["detail"]

    client.put("/api/pages/me", headers=alice, json=PAGE)
    up = client.put(
        "/api/pages/me/background", headers=alice, files={"file": ("b.png", PNG, "image/png")}
    )
    assert up.status_code == 200, up.text
    # Uploaded, but not shown until the page is saved with an image background.
    assert up.json()["background_url"] is None
    assert up.json()["custom_background_url"].startswith("/api/pages/the.saasy.engineer/")

    page = client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": image_theme}).json()
    url = page["background_url"]
    assert url.startswith("/api/pages/the.saasy.engineer/background?v=")
    img = client.get(url)
    assert img.status_code == 200
    assert img.content == PNG
    assert img.headers["content-type"] == "image/png"
    assert img.headers["x-content-type-options"] == "nosniff"

    # Rejected uploads.
    for name, data, ctype in [
        ("x.svg", b"<svg/>", "image/svg+xml"),
        ("x.png", b"", "image/png"),
        ("big.png", b"x" * (9 * 1024), "image/png"),
    ]:
        resp = client.put(
            "/api/pages/me/background", headers=alice, files={"file": (name, data, ctype)}
        )
        assert resp.status_code in (413, 422), name

    # Removing the image falls back to the background color.
    page = client.delete("/api/pages/me/background", headers=alice).json()
    assert page["background_url"] is None
    assert page["custom_background_url"] is None
    assert page["theme"]["background"]["kind"] == "solid"
    assert page["theme"]["background"]["color"] == "#202020"
    assert client.get(url).status_code == 404


def test_stored_theme_from_another_version_falls_back(client, alice):
    import asyncio

    from sqlalchemy import update

    from app.db import AsyncSessionLocal
    from app.models.page import Page

    client.put("/api/pages/me", headers=alice, json={**PAGE, "theme": THEME})

    async def corrupt() -> None:
        async with AsyncSessionLocal() as db:
            await db.execute(update(Page).values(theme={"font": "removed-font"}))
            await db.commit()

    asyncio.run(corrupt())
    page = client.get("/api/pages/the.saasy.engineer")
    assert page.status_code == 200
    assert page.json()["theme"]["font"] == "system"


def test_public_config(client):
    config = client.get("/api/config").json()
    assert config["max_avatar_kb"] == 4
    assert config["max_background_kb"] == 8
