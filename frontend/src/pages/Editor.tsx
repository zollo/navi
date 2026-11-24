import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { LuExternalLink, LuPlus } from "react-icons/lu";
import { Link as RouterLink } from "react-router-dom";
import { api, ApiError } from "../api/client";
import AvatarEditor from "../components/AvatarEditor";
import IconSelect from "../components/IconSelect";
import PageView from "../components/PageView";
import RowActions from "../components/RowActions";
import { DEFAULT_MAX_AVATAR_KB, loadImage } from "../lib/avatar";
import { guessIcon } from "../lib/icons";
import { blankPage, handleProblem, isSafeUrl, move, normalizeHandle, toInput } from "../lib/page";
import type { HandleCheck, Link, Page, PageInput, PublicConfig, Section, SocialLink } from "../types";

// Live availability check for a handle, debounced while typing.
function useHandleCheck(handle: string, current: string | null) {
  const [check, setCheck] = useState<HandleCheck | null>(null);
  useEffect(() => {
    const h = normalizeHandle(handle);
    setCheck(null);
    if (!h || h === current) return;
    const local = handleProblem(h);
    if (local) {
      setCheck({ handle: h, available: false, reason: local });
      return;
    }
    // Ignore a response that arrives after the handle has changed again.
    let live = true;
    const t = setTimeout(() => {
      api
        .get<HandleCheck>(`/api/pages/handles/${encodeURIComponent(h)}`)
        .then((c) => {
          if (live) setCheck(c);
        })
        .catch(() => {});
    }, 300);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [handle, current]);
  return check;
}

function Claim({ onCreated }: { onCreated: (p: Page) => void }) {
  const [handle, setHandle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const check = useHandleCheck(handle, null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      onCreated(await api.put<Page>("/api/pages/me", blankPage(normalizeHandle(handle))));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create your page");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page narrow">
      <div className="card">
        <h1>Claim your page</h1>
        <p className="subtitle">Pick the handle people will use to find your links.</p>
        {error && <div className="alert error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="handle">Handle</label>
            <div className="handle-input">
              <span className="muted">{window.location.host}/</span>
              <input
                id="handle"
                type="text"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                placeholder="your.name"
                required
                autoFocus
              />
            </div>
            {check && (
              <div className={`help ${check.available ? "ok" : "bad"}`}>
                {check.available ? "Available" : check.reason}
              </div>
            )}
          </div>
          <button className="btn block" disabled={busy || (check !== null && !check.available)}>
            {busy ? "Creating…" : "Create my page"}
          </button>
        </form>
      </div>
    </div>
  );
}

// Client-side checks so the form can point at the problem; the API validates too.
function problems(page: PageInput): string[] {
  const out: string[] = [];
  const hp = handleProblem(page.handle);
  if (hp) out.push(`Handle: ${hp}`);
  page.socials.forEach((s, i) => {
    if (!isSafeUrl(s.url)) out.push(`Social icon ${i + 1}: enter a URL starting with https:// or mailto:`);
  });
  page.sections.forEach((s, si) =>
    s.links.forEach((l, li) => {
      const where = `${s.title || `Section ${si + 1}`}, link ${li + 1}`;
      if (!l.title.trim()) out.push(`${where}: add a title`);
      if (!isSafeUrl(l.url)) out.push(`${where}: enter a URL starting with https:// or mailto:`);
    }),
  );
  return out;
}

export default function Editor() {
  const [loaded, setLoaded] = useState<Page | null>(null);
  const [missing, setMissing] = useState(false);
  const [draft, setDraft] = useState<PageInput | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [maxAvatarKb, setMaxAvatarKb] = useState(DEFAULT_MAX_AVATAR_KB);
  const [editing, setEditing] = useState<{ image: HTMLImageElement; animated: boolean } | null>(null);
  const [dragging, setDragging] = useState(false);
  const check = useHandleCheck(draft?.handle ?? "", loaded?.handle ?? null);

  const adopt = useCallback((p: Page) => {
    setLoaded(p);
    setDraft(toInput(p));
    setAvatarUrl(p.avatar_url);
    setMissing(false);
  }, []);

  useEffect(() => {
    api
      .get<Page>("/api/pages/me")
      .then(adopt)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setMissing(true);
        else setError(err instanceof ApiError ? err.message : "Couldn't load your page");
      });
  }, [adopt]);

  useEffect(() => {
    api
      .get<PublicConfig>("/api/config")
      .then((c) => setMaxAvatarKb(c.max_avatar_kb))
      .catch(() => {});
  }, []);

  if (missing) return <Claim onCreated={adopt} />;
  if (!draft || !loaded) {
    return <div className="page muted">{error ? <div className="alert error">{error}</div> : "Loading…"}</div>;
  }

  const dirty = JSON.stringify(draft) !== JSON.stringify(toInput(loaded));
  const update = (patch: Partial<PageInput>) => setDraft({ ...draft, ...patch });
  const setSocials = (socials: SocialLink[]) => update({ socials });
  const setSections = (sections: Section[]) => update({ sections });
  const setSection = (i: number, s: Section) =>
    setSections(draft.sections.map((x, j) => (j === i ? s : x)));
  const setLink = (si: number, li: number, l: Link) =>
    setSection(si, { ...draft.sections[si], links: draft.sections[si].links.map((x, j) => (j === li ? l : x)) });

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    const found = problems(draft);
    if (found.length) {
      setError(found.join("\n"));
      return;
    }
    setBusy(true);
    try {
      adopt(await api.put<Page>("/api/pages/me", { ...draft, handle: normalizeHandle(draft.handle) }));
      setNotice("Saved. Your page is live.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your page");
    } finally {
      setBusy(false);
    }
  };

  // Any image the browser can decode (HEIC on Safari, AVIF, BMP…) opens in the
  // editor; what's uploaded is always the re-encoded result.
  const openEditor = async (src: Blob) => {
    setError(null);
    if (src.type && !src.type.startsWith("image/")) {
      setError("Choose an image file");
      return;
    }
    try {
      setEditing({ image: await loadImage(src), animated: src.type === "image/gif" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't open that image");
    }
  };

  const editCurrent = async () => {
    if (!avatarUrl) return;
    try {
      const resp = await fetch(api.baseUrl + avatarUrl);
      if (!resp.ok) throw new Error();
      await openEditor(await resp.blob());
    } catch {
      setError("Couldn't load your current photo");
    }
  };

  const uploadAvatar = async (file: File) => {
    try {
      const p = await api.upload<Page>("/api/pages/me/avatar", file);
      setAvatarUrl(p.avatar_url);
      setEditing(null);
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.message : "Couldn't upload the photo");
    }
  };

  const removeAvatar = async () => {
    try {
      setAvatarUrl((await api.del<Page>("/api/pages/me/avatar")).avatar_url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove the image");
    }
  };

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <h1>Your page</h1>
          <p className="subtitle">
            Live at{" "}
            <RouterLink to={`/${loaded.handle}`}>
              {window.location.host}/{loaded.handle}
            </RouterLink>
          </p>
        </div>
        <div className="row">
          <button type="button" className="btn secondary small preview-toggle" onClick={() => setShowPreview((v) => !v)}>
            {showPreview ? "Edit" : "Preview"}
          </button>
          <RouterLink className="btn secondary small" to={`/${loaded.handle}`} target="_blank">
            <LuExternalLink aria-hidden /> View
          </RouterLink>
        </div>
      </div>

      <div className={`editor ${showPreview ? "show-preview" : ""}`}>
        <form className="editor-form" onSubmit={save}>
          {/* Disabled while saving, so no edit is lost when the saved page comes back. */}
          <fieldset disabled={busy}>
          {error && <div className="alert error prewrap">{error}</div>}
          {notice && !dirty && <div className="alert success">{notice}</div>}

          <div className="card">
            <h2>Profile</h2>
            <div
              className={`avatar-row ${dragging ? "dragging" : ""}`}
              onDragOver={(e) => {
                if (!e.dataTransfer.types.includes("Files")) return;
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                const f = e.dataTransfer.files[0];
                if (f) void openEditor(f);
              }}
            >
              {avatarUrl ? (
                <img className="navi-avatar small" src={api.baseUrl + avatarUrl} alt="Your avatar" />
              ) : (
                <div className="navi-avatar small placeholder" aria-hidden>
                  ?
                </div>
              )}
              <div className="avatar-actions">
                <div className="row">
                  <button type="button" className="btn secondary small" onClick={() => fileRef.current?.click()}>
                    {avatarUrl ? "Change" : "Add photo"}
                  </button>
                  {avatarUrl && (
                    <>
                      <button type="button" className="btn ghost small" onClick={editCurrent}>
                        Edit
                      </button>
                      <button type="button" className="btn ghost small" onClick={removeAvatar}>
                        Remove
                      </button>
                    </>
                  )}
                </div>
                <span className="help">Or drop an image here. You can crop it before it's saved.</span>
              </div>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void openEditor(f);
                  e.target.value = "";
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="handle">Handle</label>
              <div className="handle-input">
                <span className="muted">{window.location.host}/</span>
                <input
                  id="handle"
                  type="text"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  value={draft.handle}
                  onChange={(e) => update({ handle: e.target.value })}
                  required
                />
              </div>
              {check && (
                <div className={`help ${check.available ? "ok" : "bad"}`}>
                  {check.available ? "Available" : check.reason}
                </div>
              )}
            </div>
            <div className="field">
              <label htmlFor="title">Title</label>
              <input
                id="title"
                type="text"
                maxLength={80}
                value={draft.title}
                placeholder={`@${draft.handle}`}
                onChange={(e) => update({ title: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="tagline">Tagline</label>
              <input
                id="tagline"
                type="text"
                maxLength={300}
                value={draft.tagline}
                onChange={(e) => update({ tagline: e.target.value })}
              />
            </div>
          </div>

          <div className="card">
            <h2>Social icons</h2>
            <p className="muted small">The row of icons under your tagline.</p>
            <div className="stack">
              {draft.socials.map((s, i) => (
                <div className="edit-row" key={i}>
                  <IconSelect
                    value={s.icon}
                    label={`Social icon ${i + 1}`}
                    onChange={(icon) => setSocials(draft.socials.map((x, j) => (j === i ? { ...x, icon } : x)))}
                  />
                  <input
                    type="url"
                    aria-label={`Social icon ${i + 1} URL`}
                    placeholder="https://"
                    value={s.url}
                    onChange={(e) => {
                      const url = e.target.value;
                      const icon = s.url ? s.icon : guessIcon(url);
                      setSocials(draft.socials.map((x, j) => (j === i ? { icon, url } : x)));
                    }}
                  />
                  <RowActions
                    what="icon"
                    index={i}
                    count={draft.socials.length}
                    onMove={(d) => setSocials(move(draft.socials, i, d))}
                    onRemove={() => setSocials(draft.socials.filter((_, j) => j !== i))}
                  />
                </div>
              ))}
            </div>
            <button
              type="button"
              className="btn ghost"
              onClick={() => setSocials([...draft.socials, { icon: "link", url: "" }])}
            >
              <LuPlus aria-hidden /> Add icon
            </button>
          </div>

          {draft.sections.map((section, si) => (
            <div className="card" key={si}>
              <div className="edit-row section-head">
                <input
                  type="text"
                  aria-label={`Section ${si + 1} heading`}
                  placeholder="Section heading (optional)"
                  maxLength={80}
                  value={section.title}
                  onChange={(e) => setSection(si, { ...section, title: e.target.value })}
                />
                <RowActions
                  what="section"
                  index={si}
                  count={draft.sections.length}
                  onMove={(d) => setSections(move(draft.sections, si, d))}
                  onRemove={() => setSections(draft.sections.filter((_, j) => j !== si))}
                />
              </div>
              <div className="stack">
                {section.links.map((link, li) => (
                  <div className="link-edit" key={li}>
                    <div className="edit-row">
                      <IconSelect
                        value={link.icon}
                        label={`Link ${li + 1} icon`}
                        onChange={(icon) => setLink(si, li, { ...link, icon })}
                      />
                      <input
                        type="text"
                        aria-label={`Link ${li + 1} title`}
                        placeholder="Title"
                        maxLength={120}
                        value={link.title}
                        onChange={(e) => setLink(si, li, { ...link, title: e.target.value })}
                      />
                      <RowActions
                        what="link"
                        index={li}
                        count={section.links.length}
                        onMove={(d) => setSection(si, { ...section, links: move(section.links, li, d) })}
                        onRemove={() =>
                          setSection(si, { ...section, links: section.links.filter((_, j) => j !== li) })
                        }
                      />
                    </div>
                    <input
                      type="url"
                      aria-label={`Link ${li + 1} URL`}
                      placeholder="https://"
                      value={link.url}
                      onChange={(e) => {
                        const url = e.target.value;
                        const icon = link.url || link.icon !== "link" ? link.icon : guessIcon(url);
                        setLink(si, li, { ...link, url, icon });
                      }}
                    />
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="btn ghost"
                onClick={() =>
                  setSection(si, { ...section, links: [...section.links, { title: "", url: "", icon: "link" }] })
                }
              >
                <LuPlus aria-hidden /> Add link
              </button>
            </div>
          ))}

          <button
            type="button"
            className="btn secondary block add-section"
            onClick={() => setSections([...draft.sections, { title: "", links: [] }])}
          >
            <LuPlus aria-hidden /> Add section
          </button>

          <div className="sticky-actions">
            <button className="btn" disabled={busy || !dirty}>
              {busy ? "Saving…" : dirty ? "Save changes" : "Saved"}
            </button>
            {dirty && (
              <button type="button" className="btn secondary" onClick={() => setDraft(toInput(loaded))}>
                Discard
              </button>
            )}
          </div>
          </fieldset>
        </form>

        <aside className="editor-preview" aria-label="Preview">
          <div className="phone">
            <PageView page={{ ...draft, handle: normalizeHandle(draft.handle) }} avatarUrl={avatarUrl} preview />
          </div>
        </aside>
      </div>

      {editing && (
        <AvatarEditor
          image={editing.image}
          animated={editing.animated}
          maxBytes={maxAvatarKb * 1024}
          onCancel={() => setEditing(null)}
          onSave={uploadAvatar}
        />
      )}
    </div>
  );
}
