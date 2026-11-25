import { describe, expect, it } from "vitest";
import {
  DEFAULT_THEME,
  THEME_PRESETS,
  backgroundImageUrl,
  isDark,
  normalizeTheme,
  readableOn,
  themeStyle,
  withBackgroundKind,
} from "./theme";

const vars = (s: object) => s as Record<string, string>;

describe("colors", () => {
  it("picks readable text", () => {
    expect(isDark("#000000")).toBe(true);
    expect(isDark("#ffffff")).toBe(false);
    expect(readableOn("#1e293b")).toBe("#ffffff");
    expect(readableOn("#fde68a")).toBe("#111318");
  });
});

describe("themeStyle", () => {
  it("leaves the default look to the stylesheet", () => {
    const s = vars(themeStyle(DEFAULT_THEME, null));
    expect(s["--nv-bg"]).toBeUndefined();
    expect(s["--nv-text"]).toBeUndefined();
    expect(s["--nv-btn-radius"]).toBe("14px");
  });

  it("uses readable text on a dark solid background", () => {
    const theme = withBackgroundKind(DEFAULT_THEME, "solid");
    const s = vars(themeStyle({ ...theme, background: { ...theme.background, color: "#0f172a" } }, null));
    expect(s["--nv-bg"]).toBe("#0f172a");
    expect(s["--nv-text"]).toBe("#ffffff");
  });

  it("honors an explicit text color", () => {
    const s = vars(themeStyle({ ...DEFAULT_THEME, text_color: "#ff0000" }, null));
    expect(s["--nv-text"]).toBe("#ff0000");
  });

  it("builds gradients and image backgrounds", () => {
    const g = withBackgroundKind(DEFAULT_THEME, "gradient");
    expect(vars(themeStyle(g, null))["--nv-bg"]).toMatch(/^linear-gradient\(180deg, #/);
    const img = { ...DEFAULT_THEME, background: { ...DEFAULT_THEME.background, kind: "image" as const } };
    const s = vars(themeStyle(img, "/api/pages/x/background?v=1"));
    expect(s["--nv-bg"]).toContain('url("/api/pages/x/background?v=1")');
    expect(s["--nv-text"]).toBe("#ffffff");
    expect(s["--nv-text-shadow"]).toBeDefined();
  });

  it("styles outline and filled buttons", () => {
    const outline = vars(themeStyle({ ...DEFAULT_THEME, button_style: "outline", button_color: "#4ade80" }, null));
    expect(outline["--nv-btn-bg"]).toBe("transparent");
    expect(outline["--nv-btn-border"]).toBe("2px solid #4ade80");
    const filled = vars(themeStyle({ ...DEFAULT_THEME, button_color: "#111318", button_shape: "pill" }, null));
    expect(filled["--nv-btn-fg"]).toBe("#ffffff");
    expect(filled["--nv-btn-radius"]).toBe("999px");
  });

  it("renders every preset", () => {
    for (const p of THEME_PRESETS) expect(() => themeStyle(p.theme, null)).not.toThrow();
  });
});

describe("theme helpers", () => {
  it("fills missing fields", () => {
    const t = normalizeTheme({ font: "lora" });
    expect(t.font).toBe("lora");
    expect(t.background.kind).toBe("default");
    expect(normalizeTheme(null)).toEqual(DEFAULT_THEME);
  });

  it("keeps a kind valid when switching to it", () => {
    const g = withBackgroundKind(DEFAULT_THEME, "gradient").background;
    expect(g.gradient_from).toBeTruthy();
    expect(g.gradient_to).toBeTruthy();
    expect(withBackgroundKind(DEFAULT_THEME, "solid").background.color).toBeTruthy();
  });

  it("finds the background image", () => {
    const bg = DEFAULT_THEME.background;
    expect(backgroundImageUrl(bg, "/x")).toBeNull();
    expect(backgroundImageUrl({ ...bg, kind: "image" }, "/x")).toBe("/x");
    expect(backgroundImageUrl({ ...bg, kind: "curated", curated_id: "abc" }, null)).toBe("/api/backgrounds/abc/image");
  });
});
