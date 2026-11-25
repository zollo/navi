"""Build a draft Navi page from a public Linktree page.

Linktree profiles are Next.js pages: everything the page shows is embedded as JSON
in `<script id="__NEXT_DATA__">` under `props.pageProps`:

- `account.pageTitle`, `account.description`, `account.profilePictureUrl`
- `socialLinks`: `[{type: "INSTAGRAM", url, position}]`, the icon row
- `links`: a flat list ordered by `position`. Top-level items have `parent: null`.
  A `GROUP` is a titled block whose items point back at it with `parent.id`; a
  `HEADER` is a heading between links. Both become Navi sections.

Only linktr.ee (and its image CDN, for the avatar) is ever fetched, so a user can't
point the server at an arbitrary host.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx2

from app.config import settings
from app.core.errors import Forbidden, Invalid, NotFound, Upstream
from app.models.page import Icon
from app.schemas.imports import PageImport
from app.schemas.page import (
    MAX_LINKS_PER_SECTION,
    MAX_SECTIONS,
    MAX_SOCIALS,
    LinkIn,
    SectionIn,
    SocialLinkIn,
)
from app.services.icons import guess_icon
from app.services.page_service import AVATAR_TYPES

LINKTREE_ORIGIN = "https://linktr.ee"
_LINKTREE_HOSTS = ("linktr.ee", "www.linktr.ee", "linktree.com", "www.linktree.com")
# Linktree usernames: letters, digits, dots and underscores (hyphens allowed for safety).
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)
_EMAIL_RE = re.compile(r"^[^@\s/:]+@[^@\s/:]+\.[^@\s/:]+$")

MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
TIMEOUT = httpx2.Timeout(10.0)
# Some CDNs refuse requests without a browser-like agent.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NaviImporter/1.0; +https://github.com/zollo/navi)",
    "Accept": "text/html,application/xhtml+xml,image/*;q=0.9,*/*;q=0.8",
}

# Linktree social icon types -> Navi icons. Unknown types fall back to the URL.
SOCIAL_TYPES: dict[str, Icon] = {
    "INSTAGRAM": Icon.instagram,
    "THREADS": Icon.threads,
    "TWITTER": Icon.x,
    "X": Icon.x,
    "TIKTOK": Icon.tiktok,
    "LINKEDIN": Icon.linkedin,
    "GITHUB": Icon.github,
    "YOUTUBE": Icon.youtube,
    "FACEBOOK": Icon.facebook,
    "TWITCH": Icon.twitch,
    "DISCORD": Icon.discord,
    "SIGNAL": Icon.signal,
    "WHATSAPP": Icon.whatsapp,
    "TELEGRAM": Icon.telegram,
    "MASTODON": Icon.mastodon,
    "BLUESKY": Icon.bluesky,
    "REDDIT": Icon.reddit,
    "SPOTIFY": Icon.spotify,
    "EMAIL": Icon.email,
    "EMAIL_ADDRESS": Icon.email,
    "APPLE_MUSIC": Icon.music,
    "AMAZON_MUSIC": Icon.music,
    "SOUNDCLOUD": Icon.music,
    "BANDCAMP": Icon.music,
    "DEEZER": Icon.music,
    "TIDAL": Icon.music,
    "YOUTUBE_MUSIC": Icon.music,
    "APPLE_PODCAST": Icon.podcast,
    "APPLE_PODCASTS": Icon.podcast,
    "PODCAST": Icon.podcast,
    "SUBSTACK": Icon.blog,
    "MEDIUM": Icon.blog,
    "ETSY": Icon.shop,
    "SHOPIFY": Icon.shop,
    "AMAZON": Icon.shop,
    "DEPOP": Icon.shop,
    "POSHMARK": Icon.shop,
    "WEBSITE": Icon.website,
    "CALENDLY": Icon.calendar,
}


def linktree_url(source: str) -> str:
    """The canonical https://linktr.ee/<username> for a username or Linktree URL."""
    s = source.strip()
    # "linktr.ee" alone is a username (Linktree's own); a link has a slash.
    if "/" in s:
        parts = urlsplit(s if "://" in s else f"https://{s}")
        if (parts.hostname or "").lower() not in _LINKTREE_HOSTS:
            raise Invalid("Enter a Linktree username or a linktr.ee link")
        segments = [p for p in parts.path.split("/") if p]
        if len(segments) != 1:
            raise Invalid("Enter a Linktree profile link, like linktr.ee/yourname")
        s = segments[0]
    s = s.lstrip("@")
    if not _USERNAME_RE.match(s):
        raise Invalid("That doesn't look like a Linktree username")
    return f"{LINKTREE_ORIGIN}/{s}"


def _allowed_host(url: str, *, image: bool) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https":
        return False
    if host in _LINKTREE_HOSTS:
        return True
    # Profile pictures are served from Linktree's own CDN subdomains.
    return image and (host.endswith(".linktr.ee") or host.endswith(".linktree.com"))


@dataclass
class _Fetched:
    content: bytes
    content_type: str

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class _TooBig(Exception):
    pass


async def _fetch(
    client: httpx2.AsyncClient, url: str, *, max_bytes: int, image: bool = False
) -> _Fetched | None:
    """GET `url`, following redirects only within Linktree. Returns None on 404.
    The body is capped at `max_bytes`; a bigger one raises _TooBig."""
    for _ in range(MAX_REDIRECTS + 1):
        if not _allowed_host(url, image=image):
            raise Upstream("Linktree redirected somewhere unexpected")
        async with client.stream("GET", url) as resp:
            if resp.is_redirect and "location" in resp.headers:
                url = urljoin(url, resp.headers["location"])
                continue
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise Upstream(f"Linktree answered with HTTP {resp.status_code}; try again later")
            body = bytearray()
            async for chunk in resp.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise _TooBig()
            content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            return _Fetched(bytes(body), content_type)
    raise Upstream("Linktree redirected too many times")


# Tests swap in an httpx2.MockTransport.
transport: httpx2.AsyncBaseTransport | None = None


def _client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        timeout=TIMEOUT, headers=HEADERS, follow_redirects=False, transport=transport
    )


def page_props(html: str) -> dict[str, Any]:
    m = _NEXT_DATA_RE.search(html)
    if m is None:
        raise Upstream("Couldn't find the page data on that Linktree page")
    try:
        props = json.loads(m.group(1))["props"]["pageProps"]
    except (ValueError, KeyError, TypeError):
        raise Upstream("Couldn't read the page data on that Linktree page") from None
    if not isinstance(props, dict):
        raise Upstream("Couldn't read the page data on that Linktree page")
    return props


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value).split())[:limit] if isinstance(value, str) else ""


def _safe_url(value: Any) -> str | None:
    """A URL Navi accepts (https/http/mailto), or None. Bare emails become mailto:."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if _EMAIL_RE.match(url):
        url = f"mailto:{url}"
    lower = url.lower()
    if lower.startswith(("https://", "http://", "mailto:")) and 8 < len(url) <= 2048:
        return url
    return None


def _pos(item: dict[str, Any]) -> float:
    p = item.get("position")
    return p if isinstance(p, int | float) else float("inf")


def _parent_id(item: dict[str, Any]) -> str | None:
    parent = item.get("parent")
    if isinstance(parent, dict) and parent.get("id") is not None:
        return str(parent["id"])
    return None


@dataclass
class _Builder:
    sections: list[SectionIn] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: int = 0
    dropped: int = 0

    def section(self, title: str = "") -> SectionIn:
        s = SectionIn(title=title, links=[])
        self.sections.append(s)
        return s

    def add(self, section: SectionIn, item: dict[str, Any]) -> None:
        url = _safe_url(item.get("url"))
        title = _text(item.get("title"), 120) or (url or "")[:120]
        if url is None or not title:
            self.skipped += 1
            return
        if len(section.links) >= MAX_LINKS_PER_SECTION:
            self.dropped += 1
            return
        section.links.append(LinkIn(title=title, url=url, icon=guess_icon(url)))


def build_sections(links: list[Any]) -> tuple[list[SectionIn], list[str]]:
    items = [x for x in links if isinstance(x, dict)]
    children: dict[str, list[dict[str, Any]]] = {}
    top: list[dict[str, Any]] = []
    for item in items:
        pid = _parent_id(item)
        if pid is None:
            top.append(item)
        else:
            children.setdefault(pid, []).append(item)

    b = _Builder()
    loose: SectionIn | None = None  # where top-level links go until the next heading
    for item in sorted(top, key=_pos):
        kind = str(item.get("type") or "").upper()
        if kind == "GROUP":
            group = b.section(_text(item.get("title"), 80))
            for child in sorted(children.get(str(item.get("id")), []), key=_pos):
                b.add(group, child)
            loose = None
        elif kind == "HEADER":
            loose = b.section(_text(item.get("title"), 80))
        else:
            if loose is None:
                loose = b.section()
            b.add(loose, item)

    sections = [s for s in b.sections if s.links]
    if len(sections) > MAX_SECTIONS:
        b.dropped += sum(len(s.links) for s in sections[MAX_SECTIONS:])
        sections = sections[:MAX_SECTIONS]
    if b.skipped:
        b.warnings.append(
            f"Skipped {b.skipped} item(s) that aren't plain links "
            "(forms, embeds, phone numbers, ...)"
        )
    if b.dropped:
        b.warnings.append(
            f"Left out {b.dropped} link(s) over Navi's limits "
            f"({MAX_SECTIONS} sections, {MAX_LINKS_PER_SECTION} links each)"
        )
    return sections, b.warnings


def build_socials(social_links: list[Any]) -> tuple[list[SocialLinkIn], list[str]]:
    out: list[SocialLinkIn] = []
    skipped = 0
    for item in sorted((x for x in social_links if isinstance(x, dict)), key=_pos):
        url = _safe_url(item.get("url"))
        if url is None:
            skipped += 1
            continue
        icon = SOCIAL_TYPES.get(str(item.get("type") or "").upper()) or guess_icon(url)
        if icon == Icon.link:
            icon = Icon.website
        out.append(SocialLinkIn(icon=icon, url=url))
    warnings = []
    if skipped:
        warnings.append(f"Skipped {skipped} social icon(s) without a web or email link")
    if len(out) > MAX_SOCIALS:
        warnings.append(f"Kept the first {MAX_SOCIALS} social icons")
        out = out[:MAX_SOCIALS]
    return out, warnings


def _list(props: dict[str, Any], account: dict[str, Any], key: str) -> list[Any]:
    """pageProps[key], else account[key] (older pages only have the latter)."""
    for source in (props, account):
        if isinstance(source.get(key), list):
            return source[key]
    return []


def build_import(props: dict[str, Any], source_url: str) -> PageImport:
    account = props.get("account") if isinstance(props.get("account"), dict) else {}
    username = _text(account.get("username") or props.get("username"), 60)
    title = _text(account.get("pageTitle") or props.get("pageTitle"), 80)
    tagline = _text(account.get("description") or props.get("description"), 300)

    links = _list(props, account, "links")
    socials_raw = _list(props, account, "socialLinks")

    sections, warnings = build_sections(links)
    socials, social_warnings = build_socials(socials_raw)
    warnings += social_warnings
    if props.get("hasPagePassword") or (props.get("pageLockType") and not links):
        warnings.append("This Linktree page is locked, so some links may be missing")
    if not sections and not socials:
        warnings.append("No links were found on this Linktree page")

    return PageImport(
        source_url=source_url,
        title=title or (f"@{username}" if username else ""),
        tagline=tagline,
        socials=socials,
        sections=sections,
        warnings=warnings,
    )


def _avatar_source(props: dict[str, Any]) -> str | None:
    account = props.get("account") if isinstance(props.get("account"), dict) else {}
    for value in (account.get("profilePictureUrl"), props.get("customAvatar")):
        if isinstance(value, str) and value.startswith("https://"):
            return value
    return None


async def _fetch_avatar(client: httpx2.AsyncClient, url: str) -> tuple[str | None, str | None]:
    """(data URL, warning). Only Linktree-hosted images, within MAX_AVATAR_KB."""
    if not _allowed_host(url, image=True):
        return None, "Couldn't bring over the profile picture (it isn't hosted on Linktree)"
    try:
        resp = await _fetch(client, url, max_bytes=settings.max_avatar_bytes, image=True)
    except _TooBig:
        return None, (
            f"The profile picture is bigger than {settings.max_avatar_kb} KB; "
            "add a smaller one yourself"
        )
    except (Upstream, httpx2.HTTPError):
        return None, "Couldn't download the profile picture"
    if resp is None:
        return None, "Couldn't download the profile picture"
    content_type = resp.content_type
    if content_type not in AVATAR_TYPES:
        return None, "The profile picture isn't a PNG, JPEG, WebP or GIF; add one yourself"
    data = base64.b64encode(resp.content).decode("ascii")
    return f"data:{content_type};base64,{data}", None


async def import_linktree(source: str, *, include_avatar: bool = True) -> PageImport:
    if not settings.linktree_import_enabled:
        raise Forbidden("Importing from Linktree is turned off on this server")
    url = linktree_url(source)
    try:
        async with _client() as client:
            try:
                resp = await _fetch(client, url, max_bytes=MAX_PAGE_BYTES)
            except _TooBig:
                raise Upstream("That Linktree page is unexpectedly large") from None
            if resp is None:
                raise NotFound(f"No Linktree page at {url.removeprefix('https://')}")
            props = page_props(resp.text)
            result = build_import(props, url)
            if include_avatar and (avatar := _avatar_source(props)):
                result.avatar_data_url, warning = await _fetch_avatar(client, avatar)
                if warning:
                    result.warnings.append(warning)
    except httpx2.HTTPError:
        raise Upstream("Couldn't reach Linktree; try again later") from None
    return result
