"""Importing a page from Linktree, against a mocked linktr.ee."""
from __future__ import annotations

import base64
import json

import httpx2
import pytest

from app.core.errors import Invalid
from app.services import linktree_service
from app.services.linktree_service import linktree_url

AVATAR_URL = "https://ugc.production.linktr.ee/abc_avatar.png"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32

# Shaped like the __NEXT_DATA__ of a real Linktree profile (trimmed).
PROPS = {
    "account": {
        "username": "sam.example",
        "pageTitle": "Sam Example",
        "description": "  Maker of   things.\n",
        "profilePictureUrl": AVATAR_URL,
    },
    "username": "sam.example",
    "socialLinks": [
        {"type": "TIKTOK", "url": "https://tiktok.com/@sam", "position": 1},
        {"type": "INSTAGRAM", "url": "https://instagram.com/sam", "position": 0},
        {"type": "EMAIL_ADDRESS", "url": "sam@example.com", "position": 2},
        {"type": "PHONE", "url": "tel:+15555550100", "position": 3},
        {"type": "SOMETHING_NEW", "url": "https://example.org", "position": 4},
    ],
    "links": [
        {"id": "1", "type": "CLASSIC", "title": "My blog", "url": "https://blog.example.com",
         "position": 0, "parent": None},
        {"id": "2", "type": "GROUP", "title": "Music", "url": "", "position": 2, "parent": None},
        {"id": "3", "type": "SPOTIFY_PLAYLIST", "title": "Playlist",
         "url": "https://open.spotify.com/playlist/x", "position": 1,
         "parent": {"id": 2, "context": {"layoutOption": "stack"}}},
        {"id": "4", "type": "CLASSIC", "title": "Video", "url": "https://youtu.be/x",
         "position": 0, "parent": {"id": 2}},
        {"id": "5", "type": "CLASSIC", "title": "GitHub", "url": "https://github.com/sam",
         "position": 1, "parent": None},
        {"id": "6", "type": "HEADER", "title": "Contact", "url": "", "position": 3,
         "parent": None},
        {"id": "7", "type": "FORM", "title": "Sign up", "url": "", "position": 4, "parent": None},
        {"id": "8", "type": "CLASSIC", "title": "Bad", "url": "javascript:alert(1)",
         "position": 5, "parent": None},
        {"id": "9", "type": "CLASSIC", "title": "", "url": "https://x.com/sam", "position": 6,
         "parent": None},
        # Child of a group that isn't on the page (hidden or scheduled): left out.
        {"id": "10", "type": "CLASSIC", "title": "Orphan", "url": "https://orphan.example",
         "position": 0, "parent": {"id": 999}},
        # Empty group: no section.
        {"id": "11", "type": "GROUP", "title": "", "url": "", "position": 7, "parent": None},
    ],
}


def html(props: dict) -> str:
    data = json.dumps({"props": {"pageProps": props}, "page": "/[profile]"})
    return (
        "<!DOCTYPE html><html><head><title>Sam</title></head><body><div id=__next></div>"
        f'<script id="__NEXT_DATA__" type="application/json" crossorigin="anonymous">{data}'
        "</script></body></html>"
    )


def mock(routes: dict[str, httpx2.Response]):
    seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        seen.append(url)
        return routes.get(url) or httpx2.Response(404)

    return httpx2.MockTransport(handler), seen


@pytest.fixture
def linktree(monkeypatch):
    def install(routes: dict[str, httpx2.Response]) -> list[str]:
        transport, seen = mock(routes)
        monkeypatch.setattr(linktree_service, "transport", transport)
        return seen

    return install


def page_response(props: dict = PROPS) -> httpx2.Response:
    return httpx2.Response(200, text=html(props), headers={"content-type": "text/html"})


def test_linktree_url_parsing():
    assert linktree_url("sam") == "https://linktr.ee/sam"
    assert linktree_url("@Sam_1.x") == "https://linktr.ee/Sam_1.x"
    assert linktree_url("linktr.ee") == "https://linktr.ee/linktr.ee"
    assert linktree_url("linktr.ee/sam") == "https://linktr.ee/sam"
    assert linktree_url("https://www.linktr.ee/sam/?utm_source=x") == "https://linktr.ee/sam"
    for bad in ["https://evil.example/sam", "http://169.254.169.254/x", "linktr.ee/a/b",
                "https://linktr.ee/", "sam smith", "a" * 80]:
        with pytest.raises(Invalid):
            linktree_url(bad)


def test_import_builds_a_draft(client, alice, linktree):
    seen = linktree(
        {
            "https://linktr.ee/sam.example": page_response(),
            AVATAR_URL: httpx2.Response(200, content=PNG, headers={"content-type": "image/png"}),
        }
    )
    resp = client.post(
        "/api/import/linktree", json={"source": "linktr.ee/sam.example"}, headers=alice
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source_url"] == "https://linktr.ee/sam.example"
    assert body["title"] == "Sam Example"
    assert body["tagline"] == "Maker of things."
    assert body["socials"] == [
        {"icon": "instagram", "url": "https://instagram.com/sam"},
        {"icon": "tiktok", "url": "https://tiktok.com/@sam"},
        {"icon": "email", "url": "mailto:sam@example.com"},
        {"icon": "website", "url": "https://example.org"},
    ]
    assert body["sections"] == [
        {"title": "", "links": [
            {"title": "My blog", "url": "https://blog.example.com", "icon": "link"},
            {"title": "GitHub", "url": "https://github.com/sam", "icon": "github"},
        ]},
        {"title": "Music", "links": [
            {"title": "Video", "url": "https://youtu.be/x", "icon": "youtube"},
            {"title": "Playlist", "url": "https://open.spotify.com/playlist/x", "icon": "spotify"},
        ]},
        {"title": "Contact", "links": [
            # An untitled link falls back to its URL.
            {"title": "https://x.com/sam", "url": "https://x.com/sam", "icon": "x"},
        ]},
    ]
    assert body["avatar_data_url"] == "data:image/png;base64," + base64.b64encode(PNG).decode()
    assert any("Skipped 2 item" in w for w in body["warnings"])
    assert any("1 social icon" in w for w in body["warnings"])
    assert seen == ["https://linktr.ee/sam.example", AVATAR_URL]

    # The draft is a valid page as-is.
    draft = {k: body[k] for k in ("title", "tagline", "socials", "sections")}
    saved = client.put("/api/pages/me", json={"handle": "sam", **draft}, headers=alice)
    assert saved.status_code == 201, saved.text
    assert saved.json()["sections"][1]["links"][1]["icon"] == "spotify"


def test_import_needs_auth(client):
    assert client.post("/api/import/linktree", json={"source": "sam"}).status_code == 401


def test_import_without_avatar(client, alice, linktree):
    seen = linktree({"https://linktr.ee/sam": page_response()})
    body = client.post(
        "/api/import/linktree", json={"source": "sam", "include_avatar": False}, headers=alice
    ).json()
    assert body["avatar_data_url"] is None
    assert seen == ["https://linktr.ee/sam"]


def test_avatar_too_big_or_wrong_type(client, alice, linktree):
    # MAX_AVATAR_KB is 4 in tests.
    linktree(
        {
            "https://linktr.ee/sam": page_response(),
            AVATAR_URL: httpx2.Response(
                200, content=b"x" * 5000, headers={"content-type": "image/png"}
            ),
        }
    )
    body = client.post("/api/import/linktree", json={"source": "sam"}, headers=alice).json()
    assert body["avatar_data_url"] is None
    assert any("bigger than 4 KB" in w for w in body["warnings"])

    linktree(
        {
            "https://linktr.ee/sam": page_response(),
            AVATAR_URL: httpx2.Response(
                200, content=b"<svg/>", headers={"content-type": "image/svg+xml"}
            ),
        }
    )
    body = client.post("/api/import/linktree", json={"source": "sam"}, headers=alice).json()
    assert body["avatar_data_url"] is None
    assert any("isn't a PNG" in w for w in body["warnings"])


def test_avatar_off_linktree_is_not_fetched(client, alice, linktree):
    props = {**PROPS, "account": {**PROPS["account"], "profilePictureUrl": "https://evil.example/a.png"}}
    seen = linktree({"https://linktr.ee/sam": page_response(props)})
    body = client.post("/api/import/linktree", json={"source": "sam"}, headers=alice).json()
    assert body["avatar_data_url"] is None
    assert seen == ["https://linktr.ee/sam"]


def test_redirects_stay_on_linktree(client, alice, linktree):
    seen = linktree(
        {
            "https://linktr.ee/Sam": httpx2.Response(301, headers={"location": "/sam"}),
            "https://linktr.ee/sam": page_response(),
            "https://linktr.ee/evil": httpx2.Response(
                302, headers={"location": "http://10.0.0.1/admin"}
            ),
        }
    )
    ok = client.post(
        "/api/import/linktree", json={"source": "Sam", "include_avatar": False}, headers=alice
    )
    assert ok.status_code == 200
    assert seen == ["https://linktr.ee/Sam", "https://linktr.ee/sam"]

    bad = client.post("/api/import/linktree", json={"source": "evil"}, headers=alice)
    assert bad.status_code == 502
    assert "10.0.0.1" not in seen[-1]


def test_errors(client, alice, linktree):
    linktree(
        {
            "https://linktr.ee/blocked": httpx2.Response(403),
            "https://linktr.ee/odd": httpx2.Response(200, text="<html>no data</html>"),
        }
    )
    post = lambda s: client.post("/api/import/linktree", json={"source": s}, headers=alice)  # noqa: E731
    missing = post("nobody")
    assert missing.status_code == 404
    assert "linktr.ee/nobody" in missing.json()["detail"]
    assert post("blocked").status_code == 502
    assert post("odd").status_code == 502
    assert post("https://example.com/sam").status_code == 422


def test_network_failure(client, alice, monkeypatch):
    def boom(request):
        raise httpx2.ConnectError("down", request=request)

    monkeypatch.setattr(linktree_service, "transport", httpx2.MockTransport(boom))
    resp = client.post("/api/import/linktree", json={"source": "sam"}, headers=alice)
    assert resp.status_code == 502
    assert "reach Linktree" in resp.json()["detail"]


def test_limits(client, alice, linktree):
    links = [
        {"id": f"g{i}", "type": "HEADER", "title": f"S{i}", "position": i * 100, "parent": None}
        for i in range(25)
    ] + [
        {"id": f"l{i}-{j}", "type": "CLASSIC", "title": f"L{j}", "url": f"https://e.com/{i}/{j}",
         "position": i * 100 + 1 + j, "parent": None}
        for i in range(25)
        for j in range(2 if i else 60)
    ]
    linktree({"https://linktr.ee/big": page_response({"account": {}, "links": links})})
    body = client.post(
        "/api/import/linktree", json={"source": "big", "include_avatar": False}, headers=alice
    ).json()
    assert len(body["sections"]) == 20
    assert len(body["sections"][0]["links"]) == 50
    assert body["title"] == ""
    assert any("over Navi's limits" in w for w in body["warnings"])


def test_disabled(client, alice, monkeypatch):
    monkeypatch.setattr(linktree_service.settings, "linktree_import_enabled", False)
    resp = client.post("/api/import/linktree", json={"source": "sam"}, headers=alice)
    assert resp.status_code == 403
