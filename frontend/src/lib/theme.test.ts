import { describe, expect, it } from "vitest";
import {
  DEFAULT_AVATAR_BORDER,
  DEFAULT_CONTENT_BACKGROUND,
  DEFAULT_THEME,
  THEME_PRESETS,
  backgroundImageUrl,
  hasContentBackground,
  isDark,
  normalizeTheme,
  readableOn,
  themeStyle,
  withBackgroundKind,
  withFillKind,
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

describe("avatar border", () => {
  it("is off by default", () => {
    const s = vars(themeStyle(DEFAULT_THEME, null));
    expect(s["--nv-avatar-ring"]).toBeUndefined();
  });

  it("draws a solid or gradient ring of the chosen width", () => {
    const solid = withFillKind(DEFAULT_AVATAR_BORDER, "solid", "#ffffff");
    let s = vars(themeStyle({ ...DEFAULT_THEME, avatar_border: { ...solid, width: 6 } }, null));
    expect(s["--nv-avatar-ring"]).toBe("#ffffff");
    expect(s["--nv-avatar-ring-width"]).toBe("6px");
    expect(s["--nv-avatar-ring-radius"]).toBe("50%");

    const gradient = withFillKind(DEFAULT_AVATAR_BORDER, "gradient", "#ffffff");
    s = vars(themeStyle({ ...DEFAULT_THEME, avatar_shape: "rounded", avatar_border: gradient }, null));
    expect(s["--nv-avatar-ring"]).toMatch(/^linear-gradient\(135deg, #/);
    expect(s["--nv-avatar-ring-radius"]).toBe("28px");
  });
});

describe("content background", () => {
  it("is off by default", () => {
    expect(hasContentBackground(DEFAULT_THEME)).toBe(false);
    expect(vars(themeStyle(DEFAULT_THEME, null))["--nv-content-bg"]).toBeUndefined();
  });

  it("sets the panel fill and opacity", () => {
    const content = { ...DEFAULT_CONTENT_BACKGROUND, kind: "solid" as const, color: "#ffffff", opacity: 35 };
    const theme = { ...DEFAULT_THEME, content_background: content };
    expect(hasContentBackground(theme)).toBe(true);
    const s = vars(themeStyle(theme, null));
    expect(s["--nv-content-bg"]).toBe("#ffffff");
    expect(s["--nv-content-opacity"]).toBe("0.35");
  });

  it("picks text for an opaque panel, else for the page background", () => {
    const dark = withBackgroundKind(DEFAULT_THEME, "solid");
    const page = { ...dark, background: { ...dark.background, color: "#0f172a" } };
    const white = { ...DEFAULT_CONTENT_BACKGROUND, kind: "solid" as const, color: "#ffffff" };
    expect(vars(themeStyle({ ...page, content_background: { ...white, opacity: 90 } }, null))["--nv-text"]).toBe("#111318");
    expect(vars(themeStyle({ ...page, content_background: { ...white, opacity: 20 } }, null))["--nv-text"]).toBe("#ffffff");
  });

  it("fills in themes saved before it existed", () => {
    const old = normalizeTheme({ font: "lora" } as Partial<typeof DEFAULT_THEME>);
    expect(old.content_background).toEqual(DEFAULT_CONTENT_BACKGROUND);
    expect(old.avatar_border).toEqual(DEFAULT_AVATAR_BORDER);
  });
});
