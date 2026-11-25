import type { CSSProperties } from "react";
import type {
  AvatarBorder,
  AvatarBorderKind,
  AvatarShape,
  ButtonShape,
  ButtonStyle,
  ContentBackground,
  ContentBackgroundKind,
  FontName,
  PageTheme,
  ThemeBackground,
} from "../types";

// Mirrors the defaults in backend/app/schemas/theme.py.
export const DEFAULT_BACKGROUND: ThemeBackground = {
  kind: "default",
  color: null,
  gradient_from: null,
  gradient_to: null,
  gradient_angle: 180,
  curated_id: null,
  image_dark: true,
};

export const DEFAULT_AVATAR_BORDER: AvatarBorder = {
  kind: "none",
  color: null,
  gradient_from: null,
  gradient_to: null,
  gradient_angle: 135,
  width: 4,
};

export const DEFAULT_CONTENT_BACKGROUND: ContentBackground = {
  kind: "none",
  color: null,
  gradient_from: null,
  gradient_to: null,
  gradient_angle: 180,
  opacity: 80,
};

export const DEFAULT_THEME: PageTheme = {
  background: DEFAULT_BACKGROUND,
  font: "system",
  text_color: null,
  button_style: "filled",
  button_shape: "rounded",
  button_color: null,
  button_text_color: null,
  avatar_shape: "circle",
  avatar_border: DEFAULT_AVATAR_BORDER,
  content_background: DEFAULT_CONTENT_BACKGROUND,
};

// Self-hosted with Fontsource (see lib/fonts.ts); browsers only download a font
// once a page uses it.
export const FONTS: Record<FontName, { label: string; stack: string }> = {
  system: {
    label: "System",
    stack: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  },
  inter: { label: "Inter", stack: '"Inter", system-ui, sans-serif' },
  nunito: { label: "Nunito (rounded)", stack: '"Nunito", system-ui, sans-serif' },
  lora: { label: "Lora (serif)", stack: '"Lora", Georgia, serif' },
  playfair: { label: "Playfair Display", stack: '"Playfair Display", Georgia, serif' },
  "space-mono": { label: "Space Mono", stack: '"Space Mono", ui-monospace, monospace' },
  caveat: { label: "Caveat (handwritten)", stack: '"Caveat", cursive' },
};

export const BUTTON_STYLES: { value: ButtonStyle; label: string }[] = [
  { value: "filled", label: "Filled" },
  { value: "outline", label: "Outline" },
  { value: "glass", label: "Glass" },
  { value: "shadow", label: "Hard shadow" },
];

export const BUTTON_SHAPES: { value: ButtonShape; label: string }[] = [
  { value: "square", label: "Square" },
  { value: "rounded", label: "Rounded" },
  { value: "pill", label: "Pill" },
];

export const AVATAR_SHAPES: { value: AvatarShape; label: string }[] = [
  { value: "circle", label: "Circle" },
  { value: "rounded", label: "Rounded" },
  { value: "square", label: "Square" },
];

export const AVATAR_BORDER_KINDS: { value: AvatarBorderKind; label: string }[] = [
  { value: "none", label: "None" },
  { value: "solid", label: "Color" },
  { value: "gradient", label: "Gradient" },
];

export const CONTENT_BACKGROUND_KINDS: { value: ContentBackgroundKind; label: string }[] = [
  { value: "none", label: "None" },
  { value: "solid", label: "Color" },
  { value: "gradient", label: "Gradient" },
];

const RADII: Record<ButtonShape, string> = { square: "4px", rounded: "14px", pill: "999px" };
const AVATAR_RADII: Record<AvatarShape, string> = { circle: "50%", rounded: "24px", square: "6px" };
// Corner radius of the ring around the photo, so it hugs the photo's corners.
function ringRadius(shape: AvatarShape, width: number): string {
  if (shape === "rounded") return `${24 + width}px`;
  if (shape === "square") return `${6 + width}px`;
  return "50%";
}

export const GRADIENT_PRESETS: [string, string][] = [
  ["#ff7e5f", "#feb47b"],
  ["#2193b0", "#6dd5ed"],
  ["#ff0080", "#7928ca"],
  ["#11998e", "#38ef7d"],
  ["#0f2027", "#2c5364"],
  ["#f8cdda", "#1d2b64"],
  ["#fdfcfb", "#e2d1c3"],
  ["#232526", "#414345"],
];

export const COLOR_PRESETS = [
  "#ffffff", "#f5efe6", "#fde68a", "#fecaca", "#bbf7d0", "#bfdbfe",
  "#111318", "#1e293b", "#1f3d2b", "#4c1d95", "#7f1d1d", "#0c4a6e",
];

// One-click looks. Each replaces the whole theme.
export const THEME_PRESETS: { name: string; theme: PageTheme }[] = [
  { name: "Default", theme: DEFAULT_THEME },
  {
    name: "Midnight",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "solid", color: "#0f172a" },
      font: "inter",
      button_style: "outline",
      button_color: "#94a3b8",
      button_text_color: "#f1f5f9",
    },
  },
  {
    name: "Sunset",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "gradient", gradient_from: "#ff7e5f", gradient_to: "#feb47b", gradient_angle: 160 },
      font: "nunito",
      button_style: "glass",
      button_shape: "pill",
    },
  },
  {
    name: "Ocean",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "gradient", gradient_from: "#2193b0", gradient_to: "#6dd5ed", gradient_angle: 200 },
      button_color: "#ffffff",
      button_text_color: "#0c4a6e",
      button_shape: "pill",
    },
  },
  {
    name: "Paper",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "solid", color: "#f5efe6" },
      font: "playfair",
      button_style: "shadow",
      button_color: "#ffffff",
      button_text_color: "#111318",
      button_shape: "square",
      avatar_shape: "rounded",
    },
  },
  {
    name: "Terminal",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "solid", color: "#0b0f0c" },
      font: "space-mono",
      text_color: "#4ade80",
      button_style: "outline",
      button_color: "#4ade80",
      button_shape: "square",
      avatar_shape: "square",
    },
  },
  {
    name: "Neon",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "gradient", gradient_from: "#ff0080", gradient_to: "#7928ca", gradient_angle: 135 },
      font: "inter",
      button_style: "glass",
      button_shape: "pill",
      avatar_border: { ...DEFAULT_AVATAR_BORDER, kind: "gradient", gradient_from: "#fde68a", gradient_to: "#ff0080", width: 4 },
      content_background: { ...DEFAULT_CONTENT_BACKGROUND, kind: "solid", color: "#111318", opacity: 45 },
    },
  },
  {
    name: "Forest",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "solid", color: "#1f3d2b" },
      font: "lora",
      button_color: "#e9f5db",
      button_text_color: "#1f3d2b",
    },
  },
];

function rgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function toHex([r, g, b]: [number, number, number]): string {
  return "#" + [r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("");
}

// WCAG relative luminance, 0 (black) to 1 (white).
export function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function isDark(hex: string): boolean {
  // The luminance where black and white text have equal contrast.
  return luminance(hex) < 0.179;
}

// Near-white or near-black, whichever reads better on `hex`.
export function readableOn(hex: string): string {
  return isDark(hex) ? "#ffffff" : "#111318";
}

export function mix(a: string, b: string): string {
  const [x, y] = [rgb(a), rgb(b)];
  return toHex([(x[0] + y[0]) / 2, (x[1] + y[1]) / 2, (x[2] + y[2]) / 2]);
}

function alpha(hex: string, a: number): string {
  const [r, g, b] = rgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

// The background image the page shows, if any: its own upload or a gallery image.
export function backgroundImageUrl(
  bg: ThemeBackground,
  customBackgroundUrl: string | null,
): string | null {
  if (bg.kind === "image") return customBackgroundUrl;
  if (bg.kind === "curated" && bg.curated_id) return `/api/backgrounds/${bg.curated_id}/image`;
  return null;
}

// Whether the background behind the text is dark, light, or follows the
// viewer's light/dark mode (null).
function backgroundIsDark(bg: ThemeBackground, hasImage: boolean): boolean | null {
  if (hasImage) return bg.image_dark;
  if (bg.kind === "solid" && bg.color) return isDark(bg.color);
  if (bg.kind === "gradient" && bg.gradient_from && bg.gradient_to) {
    return isDark(mix(bg.gradient_from, bg.gradient_to));
  }
  return null;
}

// A paint for a solid-or-gradient fill, or null when it is off or incomplete.
function paint(fill: {
  kind: string;
  color: string | null;
  gradient_from: string | null;
  gradient_to: string | null;
  gradient_angle: number;
}): string | null {
  if (fill.kind === "solid" && fill.color) return fill.color;
  if (fill.kind === "gradient" && fill.gradient_from && fill.gradient_to) {
    return `linear-gradient(${fill.gradient_angle}deg, ${fill.gradient_from}, ${fill.gradient_to})`;
  }
  return null;
}

// The panel's own color (a gradient counts as the mix of its ends), or null.
function panelColor(content: ContentBackground): string | null {
  if (content.kind === "solid" && content.color) return content.color;
  if (content.kind === "gradient" && content.gradient_from && content.gradient_to) {
    return mix(content.gradient_from, content.gradient_to);
  }
  return null;
}

// The default page background (--page-bg in index.css) in light and dark mode.
const PAGE_BG = { light: "#eceef2", dark: "#0e0f14" };

// `top` laid over `base` at `opacity` (0-1).
function blend(base: string, top: string, opacity: number): string {
  const [b, t] = [rgb(base), rgb(top)];
  return toHex([0, 1, 2].map((i) => b[i] + (t[i] - b[i]) * opacity) as [number, number, number]);
}

// Whether the text sits on something dark: the panel blended over the page
// background. Null when that follows the viewer's light/dark mode.
function contentIsDark(content: ContentBackground, bg: ThemeBackground, hasImage: boolean): boolean | null {
  const panel = panelColor(content);
  const opacity = content.opacity / 100;
  const page = backgroundIsDark(bg, hasImage);
  if (!panel) return page;
  // Approximate the page background by one color to blend the panel over.
  let base: string | null = null;
  if (hasImage) base = bg.image_dark ? "#000000" : "#ffffff";
  else if (bg.kind === "solid" && bg.color) base = bg.color;
  else if (bg.kind === "gradient" && bg.gradient_from && bg.gradient_to) base = mix(bg.gradient_from, bg.gradient_to);
  if (base) return isDark(blend(base, panel, opacity));
  // The default background follows light/dark mode: blend over both. If they
  // disagree, the app's own text color (which follows the mode too) is right.
  const onLight = isDark(blend(PAGE_BG.light, panel, opacity));
  const onDark = isDark(blend(PAGE_BG.dark, panel, opacity));
  return onLight === onDark ? onLight : null;
}

// Whether the theme puts a panel behind the content (PageView adds a class).
export function hasContentBackground(theme: PageTheme): boolean {
  return paint(theme.content_background ?? DEFAULT_CONTENT_BACKGROUND) !== null;
}

// CSS custom properties that style a page (see `.navi-shell` in index.css).
// `imageUrl` is absolute (already prefixed with the API base URL) or null.
export function themeStyle(theme: PageTheme, imageUrl: string | null): CSSProperties {
  const bg = theme.background;
  const vars: Record<string, string> = {
    "--nv-font": FONTS[theme.font]?.stack ?? FONTS.system.stack,
    "--nv-btn-radius": RADII[theme.button_shape] ?? RADII.rounded,
    "--nv-avatar-radius": AVATAR_RADII[theme.avatar_shape] ?? AVATAR_RADII.circle,
  };

  // Background
  const fill = bg.color ?? "var(--page-bg)";
  if (imageUrl) {
    vars["--nv-bg"] = `${fill} url("${encodeURI(imageUrl)}") center / cover no-repeat`;
  } else if (bg.kind === "solid" && bg.color) {
    vars["--nv-bg"] = bg.color;
  } else if (bg.kind === "gradient" && bg.gradient_from && bg.gradient_to) {
    vars["--nv-bg"] = `linear-gradient(${bg.gradient_angle}deg, ${bg.gradient_from}, ${bg.gradient_to})`;
  }

  // Content panel: over the page background, which shows through below 100%.
  const content = theme.content_background ?? DEFAULT_CONTENT_BACKGROUND;
  const panel = paint(content);
  if (panel) {
    vars["--nv-content-bg"] = panel;
    vars["--nv-content-opacity"] = String(content.opacity / 100);
  }
  const onPanel = panel !== null;

  // Avatar ring
  const border = theme.avatar_border ?? DEFAULT_AVATAR_BORDER;
  const ring = paint(border);
  if (ring) {
    vars["--nv-avatar-ring"] = ring;
    vars["--nv-avatar-ring-width"] = `${border.width}px`;
    vars["--nv-avatar-ring-radius"] = ringRadius(theme.avatar_shape, border.width);
  }

  // Text: the chosen color, else readable on the panel and background, else the app's.
  const dark = contentIsDark(content, bg, imageUrl !== null);
  const text = theme.text_color ?? (dark === null ? null : dark ? "#ffffff" : "#111318");
  if (text) vars["--nv-text"] = text;
  if (imageUrl && !theme.text_color && (!onPanel || content.opacity < 50)) {
    vars["--nv-text-shadow"] = dark ? "0 1px 3px rgba(0, 0, 0, 0.55)" : "0 1px 2px rgba(255, 255, 255, 0.6)";
  }

  // Link cards
  const btn = theme.button_color;
  const btnText = theme.button_text_color;
  const ink = text ?? "var(--text)";
  switch (theme.button_style) {
    case "outline":
      vars["--nv-btn-bg"] = "transparent";
      vars["--nv-btn-hover"] = btn ? alpha(btn, 0.14) : "color-mix(in srgb, currentColor 10%, transparent)";
      vars["--nv-btn-border"] = `2px solid ${btn ?? ink}`;
      vars["--nv-btn-fg"] = btnText ?? btn ?? ink;
      vars["--nv-btn-shadow"] = "none";
      break;
    case "glass": {
      const base = btn ?? "#ffffff";
      vars["--nv-btn-bg"] = alpha(base, dark === false ? 0.45 : 0.18);
      vars["--nv-btn-hover"] = alpha(base, dark === false ? 0.6 : 0.28);
      vars["--nv-btn-border"] = `1px solid ${alpha(base, 0.35)}`;
      vars["--nv-btn-fg"] = btnText ?? ink;
      vars["--nv-btn-shadow"] = "0 4px 24px rgba(0, 0, 0, 0.08)";
      vars["--nv-btn-blur"] = "blur(12px)";
      break;
    }
    case "shadow": {
      const edge = text ?? "#111318";
      vars["--nv-btn-bg"] = btn ?? "var(--card-bg)";
      vars["--nv-btn-hover"] = btn ?? "var(--card-hover)";
      vars["--nv-btn-border"] = `2px solid ${edge}`;
      vars["--nv-btn-fg"] = btnText ?? (btn ? readableOn(btn) : "var(--text)");
      vars["--nv-btn-shadow"] = `4px 4px 0 ${edge}`;
      vars["--nv-btn-edge"] = edge;
      break;
    }
    default:
      if (btn) {
        vars["--nv-btn-bg"] = btn;
        vars["--nv-btn-hover"] = isDark(btn) ? mix(btn, "#ffffff") : mix(btn, "#e5e7eb");
        vars["--nv-btn-fg"] = btnText ?? readableOn(btn);
      } else if (btnText) {
        vars["--nv-btn-fg"] = btnText;
      }
  }
  return vars as CSSProperties;
}

// Make a theme read from the API safe to edit and save again.
export function normalizeTheme(theme: Partial<PageTheme> | null | undefined): PageTheme {
  return {
    ...DEFAULT_THEME,
    ...(theme ?? {}),
    background: { ...DEFAULT_BACKGROUND, ...(theme?.background ?? {}) },
    avatar_border: { ...DEFAULT_AVATAR_BORDER, ...(theme?.avatar_border ?? {}) },
    content_background: { ...DEFAULT_CONTENT_BACKGROUND, ...(theme?.content_background ?? {}) },
  };
}

// Fill in colors when switching a solid-or-gradient fill on, so the theme stays valid.
export function withFillKind<T extends AvatarBorder | ContentBackground>(fill: T, kind: T["kind"], color: string): T {
  const next = { ...fill, kind };
  if (kind === "solid" && !next.color) next.color = color;
  if (kind === "gradient" && (!next.gradient_from || !next.gradient_to)) {
    [next.gradient_from, next.gradient_to] = GRADIENT_PRESETS[2];
  }
  return next;
}

// Pick a background kind, filling in sensible colors so the theme stays valid.
export function withBackgroundKind(theme: PageTheme, kind: ThemeBackground["kind"]): PageTheme {
  const bg = { ...theme.background, kind };
  if (kind === "solid" && !bg.color) bg.color = "#1e293b";
  if (kind === "gradient" && (!bg.gradient_from || !bg.gradient_to)) {
    [bg.gradient_from, bg.gradient_to] = GRADIENT_PRESETS[0];
  }
  if (kind !== "curated") bg.curated_id = null;
  return { ...theme, background: bg };
}
