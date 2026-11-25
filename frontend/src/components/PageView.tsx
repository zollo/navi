import { useState, type MouseEvent } from "react";
import { LuShare } from "react-icons/lu";
import { Link as RouterLink } from "react-router-dom";
import { api } from "../api/client";
import { ICONS, NaviIcon } from "../lib/icons";
import { canShare, copyText, pageUrl } from "../lib/page";
import { backgroundImageUrl, hasContentBackground, themeStyle } from "../lib/theme";
import type { PageInput } from "../types";
import LinkMenu from "./LinkMenu";
import Logo from "./Logo";

interface Props {
  page: PageInput;
  avatarUrl: string | null;
  // The page's own uploaded background image (shown for an "image" background).
  customBackgroundUrl?: string | null;
  // In the editor's preview, links don't navigate and the chrome is static.
  preview?: boolean;
  // On a custom domain: the page's own URL (shared instead of /<handle>), and
  // Navi's home page for the logo.
  shareUrl?: string;
  homeUrl?: string;
}

function initials(page: PageInput): string {
  const source = page.title.replace(/^@/, "") || page.handle || "?";
  return source.slice(0, 1).toUpperCase();
}

// A Navi page: logo and share button, avatar, handle, tagline, social icons and
// sectioned link cards. Used by the public page and the editor preview.
export default function PageView({
  page,
  avatarUrl,
  customBackgroundUrl = null,
  preview = false,
  shareUrl,
  homeUrl,
}: Props) {
  // After a copy attempt: "copied", or the URL to select by hand if copying failed.
  const [toast, setToast] = useState<string | null>(null);
  const url = shareUrl ?? pageUrl(page.handle);
  const title = page.title || `@${page.handle}`;
  const linkProps = preview
    ? { onClick: (e: MouseEvent) => e.preventDefault() }
    : { target: "_blank", rel: "noopener noreferrer nofollow" };

  const share = async () => {
    if (canShare()) {
      try {
        await navigator.share({ title, url });
      } catch {
        /* dismissed */
      }
      return;
    }
    const copied = await copyText(url);
    setToast(copied ? "Link copied" : url);
    setTimeout(() => setToast(null), copied ? 1500 : 6000);
  };

  const image = backgroundImageUrl(page.theme.background, customBackgroundUrl);
  const style = themeStyle(page.theme, image ? api.baseUrl + image : null);
  const Shell = preview ? "div" : "main";

  return (
    <Shell className={`navi-shell btn-${page.theme.button_style} font-${page.theme.font} ${hasContentBackground(page.theme) ? "has-content" : ""} ${preview ? "preview" : ""}`} style={style}>
    <div className="navi-backdrop" aria-hidden />
    <div className="navi-page">
      <div className="navi-top">
        {homeUrl ? (
          <a href={homeUrl} className="navi-chip" aria-label="Navi home">
            <Logo size={22} />
          </a>
        ) : (
          <RouterLink
            to="/"
            className="navi-chip"
            aria-label="Navi home"
            tabIndex={preview ? -1 : 0}
            // In the editor preview, leaving would throw away unsaved edits.
            onClick={preview ? (e: MouseEvent) => e.preventDefault() : undefined}
          >
            <Logo size={22} />
          </RouterLink>
        )}
        <button
          type="button"
          className="navi-chip"
          onClick={share}
          aria-label="Share this page"
          title="Share this page"
          disabled={preview}
        >
          <LuShare size={18} aria-hidden />
        </button>
      </div>
      {toast && (
        <div className={`navi-toast ${toast === "Link copied" ? "" : "select"}`} role="status">
          {toast}
        </div>
      )}

      <header className="navi-head">
        <div className="navi-avatar-ring">
          {avatarUrl ? (
            <img className="navi-avatar" src={api.assetUrl(avatarUrl)} alt="" />
          ) : (
            <div className="navi-avatar placeholder" aria-hidden>
              {initials(page)}
            </div>
          )}
        </div>
        <h1>{title}</h1>
        {page.tagline && <p className="navi-tagline">{page.tagline}</p>}
        {page.socials.length > 0 && (
          <nav className="navi-socials" aria-label="Social profiles">
            {page.socials.map((s, i) => (
              <a key={i} href={s.url} aria-label={ICONS[s.icon]?.label ?? s.icon} {...linkProps}>
                <NaviIcon name={s.icon} size={28} />
              </a>
            ))}
          </nav>
        )}
      </header>

      {page.sections.map((section, si) =>
        section.links.length === 0 && !preview ? null : (
          <section key={si} className="navi-section">
            {section.title && <h2>{section.title}</h2>}
            <ul>
              {section.links.map((link, li) => (
                <li key={li} className="navi-link">
                  <a href={link.url} {...linkProps}>
                    <span className="ico">
                      <NaviIcon name={link.icon} size={26} />
                    </span>
                    <span className="label">{link.title}</span>
                  </a>
                  {!preview && <LinkMenu title={link.title} url={link.url} />}
                </li>
              ))}
            </ul>
          </section>
        ),
      )}
    </div>
    </Shell>
  );
}
