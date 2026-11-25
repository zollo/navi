import type { CSSProperties } from "react";
import type {
  AvatarBorder,
  AvatarBorderKind,
  AvatarShape,
  ButtonShape,
  ButtonStyle,
  ContentPanel,
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
  width: 4,
  color: null,
  gradient_from: null,
  gradient_to: null,
  gradient_angle: 135,
};

export const DEFAULT_CONTENT: ContentPanel = { enabled: false, color: "#ffffff", opacity: 85 };

// Navi's own colors, from the logo.
export const BRAND_GRADIENT: [string, string] = ["#2b1b80", "#7c1fc8"];

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
  content: DEFAULT_CONTENT,
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

const RADII: Record<ButtonShape, string> = { square: "4px", rounded: "14px", pill: "999px" };
const AVATAR_RADII: Record<AvatarShape, string> = { circle: "50%", rounded: "24px", square: "6px" };

export const GRADIENT_PRESETS: [string, string][] = [
  ["#ff7e5f", "#feb47b"],
  ["#2193b0", "#6dd5ed"],
  ["#ff0080", "#7928ca"],
  ["#11998e", "#38ef7d"],
  ["#0f2027", "#2c5364"],
  ["#f8cdda", "#1d2b64"],
  ["#fdfcfb", "#e2d1c3"],
  ["#232526", "#414345"],
  BRAND_GRADIENT,
];

export const COLOR_PRESETS = [
  "#ffffff", "#f5efe6", "#fde68a", "#fecaca", "#bbf7d0", "#bfdbfe",
  "#111318", "#1e293b", "#1f3d2b", "#4c1d95", "#7f1d1d", "#0c4a6e",
];

// One-click looks. Each replaces the whole theme.
export const THEME_PRESETS: { name: string; theme: PageTheme }[] = [
  { name: "Default", theme: DEFAULT_THEME },
  {
    name: "Navi",
    theme: {
      ...DEFAULT_THEME,
      background: { ...DEFAULT_BACKGROUND, kind: "gradient", gradient_from: BRAND_GRADIENT[0], gradient_to: BRAND_GRADIENT[1], gradient_angle: 45 },
      font: "inter",
      button_style: "glass",
      button_shape: "pill",
      avatar_border: { ...DEFAULT_AVATAR_BORDER, kind: "solid", color: "#ffffff", width: 3 },
    },
  },
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

// Whether the content panel (blended over the page background) is dark.
// `behind` is the background's darkness, or null when it follows light/dark mode.
function panelIsDark(panel: ContentPanel, behind: boolean | null): boolean | null {
  const a = Math.min(100, Math.max(0, panel.opacity)) / 100;
  if (behind === null) return a >= 0.5 ? isDark(panel.color) : null;
  const [r, g, b] = rgb(panel.color);
  const under = behind ? 17 : 245;
  return isDark(toHex([r * a + under * (1 - a), g * a + under * (1 - a), b * a + under * (1 - a)]));
}

// The CSS background that paints the avatar border, or null for none.
export function avatarBorderPaint(border: AvatarBorder | undefined): string | null {
  if (!border) return null;
  if (border.kind === "solid" && border.color) return `linear-gradient(${border.color}, ${border.color})`;
  if (border.kind === "gradient" && border.gradient_from && border.gradient_to) {
    return `linear-gradient(${border.gradient_angle}deg, ${border.gradient_from}, ${border.gradient_to})`;
  }
  return null;
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

  // Text: the chosen color, else readable on what's behind it (the content
  // panel and/or the page background), else the app's.
  const panel = theme.content;
  const dark = panel?.enabled
    ? panelIsDark(panel, backgroundIsDark(bg, imageUrl !== null))
    : backgroundIsDark(bg, imageUrl !== null);
  const text = theme.text_color ?? (dark === null ? null : dark ? "#ffffff" : "#111318");
  if (text) vars["--nv-text"] = text;
  if (panel?.enabled) {
    vars["--nv-content-bg"] = alpha(panel.color, Math.min(100, Math.max(0, panel.opacity)) / 100);
  }
  if (imageUrl && !theme.text_color && !(panel?.enabled && panel.opacity >= 50)) {
    vars["--nv-text-shadow"] = dark ? "0 1px 3px rgba(0, 0, 0, 0.55)" : "0 1px 2px rgba(255, 255, 255, 0.6)";
  }

  // Avatar border
  const border = avatarBorderPaint(theme.avatar_border);
  if (border) {
    vars["--nv-avatar-border"] = border;
    vars["--nv-avatar-border-w"] = `${theme.avatar_border.width}px`;
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
    content: { ...DEFAULT_CONTENT, ...(theme?.content ?? {}) },
  };
}

// Pick an avatar border kind, filling in colors so the theme stays valid.
export function withAvatarBorderKind(theme: PageTheme, kind: AvatarBorderKind): PageTheme {
  const b = { ...theme.avatar_border, kind };
  if (kind === "solid" && !b.color) b.color = "#ffffff";
  if (kind === "gradient" && (!b.gradient_from || !b.gradient_to)) {
    [b.gradient_from, b.gradient_to] = BRAND_GRADIENT;
  }
  return { ...theme, avatar_border: b };
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
