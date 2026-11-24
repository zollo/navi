export interface User {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuthConfig {
  registration_enabled: boolean;
}

export interface BuildInfo {
  version: string;
  git_commit: string;
  build_time: string;
  environment: string;
  public_url: string;
  api_docs_url: string;
  openapi_url: string;
}

// Keep in sync with backend/app/models/page.py `Icon`.
export type IconName =
  | "link"
  | "website"
  | "email"
  | "video"
  | "music"
  | "podcast"
  | "blog"
  | "shop"
  | "calendar"
  | "instagram"
  | "threads"
  | "x"
  | "twitter"
  | "tiktok"
  | "linkedin"
  | "github"
  | "youtube"
  | "facebook"
  | "twitch"
  | "discord"
  | "signal"
  | "whatsapp"
  | "telegram"
  | "mastodon"
  | "bluesky"
  | "reddit"
  | "spotify";

export interface SocialLink {
  icon: IconName;
  url: string;
}

export interface Link {
  id?: string;
  title: string;
  url: string;
  icon: IconName;
}

export interface Section {
  id?: string;
  title: string;
  links: Link[];
}

// Keep these in sync with backend/app/schemas/theme.py.
export type BackgroundKind = "default" | "solid" | "gradient" | "image" | "curated";
export type FontName = "system" | "inter" | "nunito" | "lora" | "playfair" | "space-mono" | "caveat";
export type ButtonStyle = "filled" | "outline" | "glass" | "shadow";
export type ButtonShape = "square" | "rounded" | "pill";
export type AvatarShape = "circle" | "rounded" | "square";

export interface ThemeBackground {
  kind: BackgroundKind;
  color: string | null;
  gradient_from: string | null;
  gradient_to: string | null;
  gradient_angle: number;
  curated_id: string | null;
  image_dark: boolean;
}

// The look of a page. Null colors are automatic.
export interface PageTheme {
  background: ThemeBackground;
  font: FontName;
  text_color: string | null;
  button_style: ButtonStyle;
  button_shape: ButtonShape;
  button_color: string | null;
  button_text_color: string | null;
  avatar_shape: AvatarShape;
}

// A curated background from the gallery.
export interface Background {
  id: string;
  name: string;
  image_url: string;
  dark: boolean;
}

// What GET /api/pages/{handle} returns.
export interface Page {
  handle: string;
  title: string;
  tagline: string;
  avatar_url: string | null;
  socials: SocialLink[];
  sections: Section[];
  theme: PageTheme;
  // The background image the page shows (its own or a gallery one), if any.
  background_url: string | null;
  // The page's own uploaded background image, shown when the kind is "image".
  custom_background_url: string | null;
  updated_at: string;
}

// What PUT /api/pages/me takes.
export interface PageInput {
  handle: string;
  title: string;
  tagline: string;
  socials: SocialLink[];
  sections: Section[];
  theme: PageTheme;
}

export interface HandleCheck {
  handle: string;
  available: boolean;
  reason: string | null;
}

// What GET /api/config returns.
export interface PublicConfig {
  max_avatar_kb: number;
  avatar_types: string[];
  max_background_kb: number;
}
