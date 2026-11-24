import type { Page, PageInput } from "../types";
import { DEFAULT_THEME, normalizeTheme } from "./theme";

// Mirrors backend/app/services/page_service.py HANDLE_RE / RESERVED_HANDLES.
const HANDLE_RE = /^[a-z0-9][a-z0-9._-]{1,28}[a-z0-9]$/;
const RESERVED = new Set([
  "about", "account", "admin", "api", "app", "assets", "auth", "dashboard",
  "docs", "edit", "editor", "favicon.svg", "handles", "help", "home", "icons",
  "index.html",
  "login", "logout", "me", "navi", "new", "openapi.json", "privacy", "redoc",
  "register", "root", "settings", "signin", "signup", "static", "support",
  "terms", "www",
]);

export function normalizeHandle(handle: string): string {
  return handle.trim().replace(/^@/, "").toLowerCase();
}

// A message explaining why a handle is unusable, or null if it looks fine.
// The server has the final say (it also knows which handles are taken).
export function handleProblem(handle: string): string | null {
  const h = normalizeHandle(handle);
  if (!HANDLE_RE.test(h) || h.includes("..")) {
    return "Use 3–30 lowercase letters, digits, dots, underscores or hyphens, starting and ending with a letter or digit.";
  }
  if (RESERVED.has(h)) return "This handle is reserved.";
  return null;
}

export function isSafeUrl(url: string): boolean {
  const u = url.trim().toLowerCase();
  return /^(https?:\/\/|mailto:)/.test(u) && u.length > 8;
}

export function toInput(page: Page): PageInput {
  return {
    handle: page.handle,
    title: page.title,
    tagline: page.tagline,
    socials: page.socials.map(({ icon, url }) => ({ icon, url })),
    sections: page.sections.map((s) => ({
      title: s.title,
      links: s.links.map(({ title, url, icon }) => ({ title, url, icon })),
    })),
    theme: normalizeTheme(page.theme),
  };
}

export function blankPage(handle = ""): PageInput {
  return {
    handle,
    title: handle ? `@${handle}` : "",
    tagline: "",
    socials: [],
    sections: [{ title: "Links", links: [] }],
    theme: DEFAULT_THEME,
  };
}

// The absolute, shareable URL of a page.
export function pageUrl(handle: string): string {
  return `${window.location.origin}/${handle}`;
}

// Copy text to the clipboard. The Clipboard API only exists on secure origins
// (https or localhost), so fall back to a hidden textarea + execCommand for a
// plain-http deployment such as http://<truenas-ip>:30083.
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* fall through */
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  ta.remove();
  return ok;
}

export function canShare(): boolean {
  return typeof navigator.share === "function" && window.isSecureContext;
}

// Move item i of a list by delta (-1 up, +1 down); returns a new list.
export function move<T>(list: T[], i: number, delta: number): T[] {
  const j = i + delta;
  if (j < 0 || j >= list.length) return list;
  const next = list.slice();
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}
