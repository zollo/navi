import type { IconType } from "react-icons";
import {
  FaBluesky,
  FaDiscord,
  FaFacebook,
  FaGithub,
  FaInstagram,
  FaLinkedin,
  FaMastodon,
  FaReddit,
  FaSignalMessenger,
  FaSpotify,
  FaTelegram,
  FaThreads,
  FaTiktok,
  FaTwitch,
  FaTwitter,
  FaWhatsapp,
  FaXTwitter,
  FaYoutube,
} from "react-icons/fa6";
import {
  LuCalendar,
  LuGlobe,
  LuLink,
  LuMail,
  LuMusic,
  LuPenLine,
  LuPodcast,
  LuShoppingBag,
  LuVideo,
} from "react-icons/lu";
import type { IconName } from "../types";

// Every icon the API accepts (backend/app/models/page.py `Icon`), with a label
// for pickers. Order here is picker order: generic first, then brands.
export const ICONS: Record<IconName, { label: string; Icon: IconType }> = {
  link: { label: "Link", Icon: LuLink },
  website: { label: "Website", Icon: LuGlobe },
  email: { label: "Email", Icon: LuMail },
  video: { label: "Video", Icon: LuVideo },
  music: { label: "Music", Icon: LuMusic },
  podcast: { label: "Podcast", Icon: LuPodcast },
  blog: { label: "Blog", Icon: LuPenLine },
  shop: { label: "Shop", Icon: LuShoppingBag },
  calendar: { label: "Calendar", Icon: LuCalendar },
  instagram: { label: "Instagram", Icon: FaInstagram },
  threads: { label: "Threads", Icon: FaThreads },
  x: { label: "X", Icon: FaXTwitter },
  twitter: { label: "Twitter", Icon: FaTwitter },
  tiktok: { label: "TikTok", Icon: FaTiktok },
  linkedin: { label: "LinkedIn", Icon: FaLinkedin },
  github: { label: "GitHub", Icon: FaGithub },
  youtube: { label: "YouTube", Icon: FaYoutube },
  facebook: { label: "Facebook", Icon: FaFacebook },
  twitch: { label: "Twitch", Icon: FaTwitch },
  discord: { label: "Discord", Icon: FaDiscord },
  signal: { label: "Signal", Icon: FaSignalMessenger },
  whatsapp: { label: "WhatsApp", Icon: FaWhatsapp },
  telegram: { label: "Telegram", Icon: FaTelegram },
  mastodon: { label: "Mastodon", Icon: FaMastodon },
  bluesky: { label: "Bluesky", Icon: FaBluesky },
  reddit: { label: "Reddit", Icon: FaReddit },
  spotify: { label: "Spotify", Icon: FaSpotify },
};

export const ICON_NAMES = Object.keys(ICONS) as IconName[];

const HOSTS: [RegExp, IconName][] = [
  [/(^|\.)instagram\.com$/, "instagram"],
  [/(^|\.)threads\.(net|com)$/, "threads"],
  [/(^|\.)(x|twitter)\.com$/, "x"],
  [/(^|\.)tiktok\.com$/, "tiktok"],
  [/(^|\.)linkedin\.com$/, "linkedin"],
  [/(^|\.)github\.com$/, "github"],
  [/(^|\.)(youtube\.com|youtu\.be)$/, "youtube"],
  [/(^|\.)(facebook\.com|fb\.com)$/, "facebook"],
  [/(^|\.)twitch\.tv$/, "twitch"],
  [/(^|\.)(discord\.gg|discord\.com)$/, "discord"],
  [/(^|\.)signal\.(me|org)$/, "signal"],
  [/(^|\.)(wa\.me|whatsapp\.com)$/, "whatsapp"],
  [/(^|\.)(t\.me|telegram\.me)$/, "telegram"],
  [/(^|\.)bsky\.app$/, "bluesky"],
  [/(^|\.)reddit\.com$/, "reddit"],
  [/(^|\.)spotify\.com$/, "spotify"],
  [/(^|\.)vimeo\.com$/, "video"],
];

// Best-guess icon for a URL, so the editor can pick one as you paste a link.
export function guessIcon(url: string): IconName {
  if (/^mailto:/i.test(url.trim())) return "email";
  try {
    const host = new URL(url.trim()).hostname.toLowerCase();
    for (const [re, name] of HOSTS) if (re.test(host)) return name;
  } catch {
    /* not a URL yet */
  }
  return "link";
}

export function NaviIcon({ name, size = 24 }: { name: IconName; size?: number }) {
  const entry = ICONS[name] ?? ICONS.link;
  return <entry.Icon size={size} aria-hidden focusable="false" />;
}
