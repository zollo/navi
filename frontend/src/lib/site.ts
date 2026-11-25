import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { DomainLookup } from "../types";

// Which site this SPA is serving: Navi itself, or someone's page on their own
// domain (www.example.com showing navi.example.net/<handle>).
export type Site =
  | { kind: "loading" }
  | { kind: "primary" }
  | { kind: "custom"; handle: string; primaryUrl: string };

const PRIMARY_KEY = "navi_primary_host";
const DAY_MS = 24 * 60 * 60 * 1000;

// Hosts that can't be custom domains: localhost, bare names, IP addresses.
export function obviouslyPrimary(host: string): boolean {
  return !host.includes(".") || /^[\d.]+$/.test(host) || host.includes(":");
}

// A host recently found not to be a custom domain is remembered for a day, so
// Navi's own pages don't wait on a lookup on every visit.
function rememberedPrimary(host: string): boolean {
  try {
    const saved = JSON.parse(localStorage.getItem(PRIMARY_KEY) ?? "null") as {
      host?: string;
      at?: number;
    } | null;
    return saved?.host === host && Date.now() - (saved.at ?? 0) < DAY_MS;
  } catch {
    return false;
  }
}

function rememberPrimary(host: string): void {
  try {
    localStorage.setItem(PRIMARY_KEY, JSON.stringify({ host, at: Date.now() }));
  } catch {
    /* storage unavailable */
  }
}

export function knownPrimary(host: string): boolean {
  return obviouslyPrimary(host) || rememberedPrimary(host);
}

export async function detectSite(host: string): Promise<Site> {
  if (knownPrimary(host)) return { kind: "primary" };
  try {
    const found = await api.get<DomainLookup>(
      `/api/domains/lookup?domain=${encodeURIComponent(host)}`,
    );
    return { kind: "custom", handle: found.handle, primaryUrl: found.primary_url };
  } catch (err) {
    // Not a custom domain. Anything else (offline, 5xx) isn't remembered.
    if (err instanceof ApiError && err.status === 404) rememberPrimary(host);
    return { kind: "primary" };
  }
}

export function useSite(host: string = window.location.hostname): Site {
  const [site, setSite] = useState<Site>(() =>
    knownPrimary(host) ? { kind: "primary" } : { kind: "loading" },
  );
  useEffect(() => {
    if (site.kind !== "loading") return;
    let live = true;
    detectSite(host).then((s) => {
      if (live) setSite(s);
    });
    return () => {
      live = false;
    };
  }, [host, site.kind]);
  return site;
}
