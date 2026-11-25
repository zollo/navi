"""Best-guess icon for a URL. Mirrors `guessIcon` in frontend/src/lib/icons.tsx."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from app.models.page import Icon

_HOSTS: list[tuple[re.Pattern[str], Icon]] = [
    (re.compile(p), icon)
    for p, icon in [
        (r"(^|\.)instagram\.com$", Icon.instagram),
        (r"(^|\.)threads\.(net|com)$", Icon.threads),
        (r"(^|\.)(x|twitter)\.com$", Icon.x),
        (r"(^|\.)tiktok\.com$", Icon.tiktok),
        (r"(^|\.)linkedin\.com$", Icon.linkedin),
        (r"(^|\.)github\.com$", Icon.github),
        (r"(^|\.)(youtube\.com|youtu\.be)$", Icon.youtube),
        (r"(^|\.)(facebook\.com|fb\.com)$", Icon.facebook),
        (r"(^|\.)twitch\.tv$", Icon.twitch),
        (r"(^|\.)(discord\.gg|discord\.com)$", Icon.discord),
        (r"(^|\.)signal\.(me|org)$", Icon.signal),
        (r"(^|\.)(wa\.me|whatsapp\.com)$", Icon.whatsapp),
        (r"(^|\.)(t\.me|telegram\.me)$", Icon.telegram),
        (r"(^|\.)bsky\.app$", Icon.bluesky),
        (r"(^|\.)reddit\.com$", Icon.reddit),
        (r"(^|\.)spotify\.com$", Icon.spotify),
        (r"(^|\.)vimeo\.com$", Icon.video),
    ]
]


def guess_icon(url: str) -> Icon:
    url = url.strip()
    if url.lower().startswith("mailto:"):
        return Icon.email
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return Icon.link
    for pattern, icon in _HOSTS:
        if pattern.search(host):
            return icon
    return Icon.link
