import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { detectSite, knownPrimary, obviouslyPrimary } from "./site";

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => void data.delete(k),
    setItem: (k, v) => void data.set(k, String(v)),
  };
}

function respond(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

describe("site detection", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", memoryStorage());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("skips hosts that can't be custom domains", () => {
    for (const host of ["localhost", "127.0.0.1", "::1", "navi"]) {
      expect(obviouslyPrimary(host)).toBe(true);
    }
    expect(obviouslyPrimary("www.example.com")).toBe(false);
  });

  it("finds the page for a custom domain", async () => {
    const fetch = respond(200, {
      hostname: "www.example.com",
      handle: "alice",
      primary_url: "https://navi.example.net",
    });
    vi.stubGlobal("fetch", fetch);
    expect(await detectSite("www.example.com")).toEqual({
      kind: "custom",
      handle: "alice",
      primaryUrl: "https://navi.example.net",
    });
    expect(String(fetch.mock.calls[0])).toContain("/api/domains/lookup?domain=www.example.com");
    expect(knownPrimary("www.example.com")).toBe(false);
  });

  it("remembers Navi's own host after a 404", async () => {
    const fetch = respond(404, { detail: "Unknown domain" });
    vi.stubGlobal("fetch", fetch);
    expect(await detectSite("navi.example.net")).toEqual({ kind: "primary" });
    expect(knownPrimary("navi.example.net")).toBe(true);
    expect(await detectSite("navi.example.net")).toEqual({ kind: "primary" });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("doesn't remember a failed lookup", async () => {
    vi.stubGlobal("fetch", respond(502, {}));
    expect(await detectSite("navi.example.net")).toEqual({ kind: "primary" });
    expect(knownPrimary("navi.example.net")).toBe(false);
  });
});
