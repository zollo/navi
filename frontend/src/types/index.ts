export interface User {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
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

// What GET /api/pages/{handle} returns.
export interface Page {
  handle: string;
  title: string;
  tagline: string;
  avatar_url: string | null;
  socials: SocialLink[];
  sections: Section[];
  updated_at: string;
}

// What PUT /api/pages/me takes.
export interface PageInput {
  handle: string;
  title: string;
  tagline: string;
  socials: SocialLink[];
  sections: Section[];
}

export interface HandleCheck {
  handle: string;
  available: boolean;
  reason: string | null;
}

// What POST /api/import/linktree returns: a draft, nothing saved yet.
export interface PageImport {
  source_url: string;
  title: string;
  tagline: string;
  socials: SocialLink[];
  sections: Section[];
  // The profile picture as a data: URL, to upload with PUT /api/pages/me/avatar.
  avatar_data_url: string | null;
  warnings: string[];
}

// What GET /api/config returns.
export interface PublicConfig {
  max_avatar_kb: number;
  avatar_types: string[];
}
