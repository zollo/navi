import { useEffect, useRef, useState } from "react";
import { LuCopy, LuEllipsisVertical, LuExternalLink, LuShare } from "react-icons/lu";
import { canShare, copyText } from "../lib/page";

// The kebab menu on a link card: open, copy or share that one link.
export default function LinkMenu({ title, url }: { title: string; url: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState<"yes" | "failed" | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    setCopied(null);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const copy = async () => {
    if (await copyText(url)) {
      setCopied("yes");
      setTimeout(() => {
        setCopied(null);
        setOpen(false);
      }, 900);
    } else {
      // Leave the menu open with the URL shown so it can be copied by hand.
      setCopied("failed");
    }
  };

  const share = async () => {
    setOpen(false);
    try {
      await navigator.share({ title, url });
    } catch {
      /* dismissed */
    }
  };

  return (
    <div className="link-menu" ref={ref}>
      <button
        type="button"
        className="icon-btn"
        aria-label={`More options for ${title}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(e) => {
          e.preventDefault();
          setOpen((o) => !o);
        }}
      >
        <LuEllipsisVertical size={18} aria-hidden />
      </button>
      {open && (
        <div className="menu" role="menu">
          <a role="menuitem" href={url} target="_blank" rel="noopener noreferrer nofollow">
            <LuExternalLink aria-hidden /> Open in new tab
          </a>
          <button type="button" role="menuitem" onClick={copy}>
            <LuCopy aria-hidden /> {copied === "yes" ? "Copied!" : "Copy link"}
          </button>
          {copied === "failed" && <div className="menu-url">{url}</div>}
          {canShare() && (
            <button type="button" role="menuitem" onClick={share}>
              <LuShare aria-hidden /> Share
            </button>
          )}
        </div>
      )}
    </div>
  );
}
