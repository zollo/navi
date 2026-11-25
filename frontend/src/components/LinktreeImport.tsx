import { useState } from "react";
import { LuDownload } from "react-icons/lu";
import { api, ApiError } from "../api/client";
import type { PageImport } from "../types";

interface Props {
  // Load the draft into the editor. Nothing is saved until the user presses Save.
  onApply: (draft: PageImport) => void;
  disabled?: boolean;
}

function summary(d: PageImport): string {
  const links = d.sections.reduce((n, s) => n + s.links.length, 0);
  const parts = [
    `${links} link${links === 1 ? "" : "s"}`,
    d.sections.length > 1 ? `in ${d.sections.length} sections` : "",
    `${d.socials.length} social icon${d.socials.length === 1 ? "" : "s"}`,
    d.avatar_data_url ? "a profile picture" : "",
  ].filter(Boolean);
  return parts.length > 1 ? `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}` : parts[0];
}

// "Import from Linktree": fetch someone's Linktree through the API, show what was
// found, and on confirmation hand it to the editor to replace the draft.
export default function LinktreeImport({ onApply, disabled = false }: Props) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [found, setFound] = useState<PageImport | null>(null);

  const fetchDraft = async (e: { preventDefault: () => void }) => {
    e.preventDefault();
    setError(null);
    setFound(null);
    setBusy(true);
    try {
      setFound(await api.post<PageImport>("/api/import/linktree", { source: source.trim() }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't import that page");
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setFound(null);
    setError(null);
  };

  if (!open) {
    return (
      <button
        type="button"
        className="btn secondary block import-toggle"
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        <LuDownload aria-hidden /> Import from Linktree
      </button>
    );
  }

  return (
    <div className="card">
      <h2>Import from Linktree</h2>
      <p className="muted small">
        Bring over the title, bio, social icons, links and profile picture from a public Linktree
        page. You can review everything before you save.
      </p>
      {error && <div className="alert error">{error}</div>}
      {found ? (
        <>
          <div className="alert info">
            Found {summary(found)} on{" "}
            <a href={found.source_url} target="_blank" rel="noopener noreferrer nofollow">
              {found.source_url.replace(/^https:\/\//, "")}
            </a>
            . Using it replaces your title, tagline, social icons and sections.
          </div>
          {found.warnings.length > 0 && (
            <ul className="muted small import-warnings">
              {found.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
          <div className="row">
            <button
              type="button"
              className="btn small"
              disabled={disabled}
              onClick={() => {
                onApply(found);
                reset();
                setSource("");
                setOpen(false);
              }}
            >
              Use this
            </button>
            <button type="button" className="btn ghost small" onClick={reset}>
              Cancel
            </button>
          </div>
        </>
      ) : (
        // Not a <form>: it sits inside the editor's form, and forms can't nest.
        <div className="edit-row">
          <input
            type="text"
            aria-label="Linktree username or link"
            placeholder="linktr.ee/yourname"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            value={source}
            onChange={(e) => setSource(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void fetchDraft(e);
            }}
            disabled={busy || disabled}
          />
          <button
            type="button"
            className="btn small"
            disabled={busy || disabled || !source.trim()}
            onClick={(e) => void fetchDraft(e)}
          >
            {busy ? "Importing…" : "Import"}
          </button>
          <button
            type="button"
            className="btn ghost small"
            onClick={() => {
              reset();
              setOpen(false);
            }}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}
