import { useEffect, useRef, useState, type FormEvent } from "react";
import { LuTrash2, LuUpload } from "react-icons/lu";
import { Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { fitImage, imageIsDark } from "../lib/image";
import type { Background, UploadLimits } from "../types";

function message(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

// Admins curate the gallery of backgrounds anyone can pick for their page.
export default function AdminBackgrounds() {
  const { user } = useAuth();
  const [items, setItems] = useState<Background[] | null>(null);
  const [limits, setLimits] = useState<UploadLimits | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dark, setDark] = useState(true);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .get<{ backgrounds: Background[] }>("/api/backgrounds")
      .then((r) => setItems(r.backgrounds))
      .catch((err) => setError(message(err, "Couldn't load the gallery")));
    api.get<UploadLimits>("/api/limits").then(setLimits).catch(() => {});
  }, []);

  if (user && !user.is_admin) return <Navigate to="/edit" replace />;

  const choose = async (f: File | undefined) => {
    setFile(f ?? null);
    if (!f) return;
    if (!name) setName(f.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").slice(0, 80));
    setDark(await imageIsDark(f));
  };

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      const fitted = await fitImage(file, (limits?.max_background_kb ?? 2048) * 1024);
      const created = await api.upload<Background>("/api/admin/backgrounds", fitted, {
        method: "POST",
        fields: { name, dark: String(dark) },
      });
      setItems((list) => [...(list ?? []), created]);
      setName("");
      setFile(null);
      setDark(true);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(message(err, "Couldn't add the background"));
    } finally {
      setBusy(false);
    }
  };

  const patch = async (bg: Background, body: Partial<Pick<Background, "name" | "dark">>) => {
    setError(null);
    try {
      const updated = await api.patch<Background>(`/api/admin/backgrounds/${bg.id}`, body);
      setItems((list) => list?.map((x) => (x.id === bg.id ? updated : x)) ?? null);
    } catch (err) {
      setError(message(err, "Couldn't save"));
    }
  };

  const remove = async (bg: Background) => {
    if (!window.confirm(`Remove "${bg.name}"? Pages using it go back to their background color.`)) return;
    setError(null);
    try {
      await api.del(`/api/admin/backgrounds/${bg.id}`);
      setItems((list) => list?.filter((x) => x.id !== bg.id) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove it");
    }
  };

  return (
    <div className="page">
      <h1>Backgrounds</h1>
      <p className="subtitle">Curated backgrounds everyone can pick for their page under Appearance.</p>
      {error && <div className="alert error">{error}</div>}

      <form className="card" onSubmit={add}>
        <h2>Add a background</h2>
        <div className="grid two">
          <div className="field">
            <label htmlFor="bg-file">Image</label>
            <input
              id="bg-file"
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={(e) => void choose(e.target.files?.[0])}
              required
            />
            <div className="help">
              Large images are resized to fit {limits ? `${limits.max_background_kb} KB` : "the size limit"}.
            </div>
          </div>
          <div className="field">
            <label htmlFor="bg-name">Name</label>
            <input id="bg-name" type="text" maxLength={80} value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
        </div>
        <label className="check field">
          <input type="checkbox" checked={dark} onChange={(e) => setDark(e.target.checked)} />
          Mostly dark (pages using it get light text)
        </label>
        <button className="btn" disabled={busy || !file}>
          <LuUpload aria-hidden /> {busy ? "Uploading…" : "Add to gallery"}
        </button>
      </form>

      <h2>Gallery</h2>
      {items === null ? (
        <p className="muted">Loading…</p>
      ) : items.length === 0 ? (
        <div className="empty">No backgrounds yet. Add the first one above.</div>
      ) : (
        <div className="admin-gallery">
          {items.map((bg) => (
            <div className="card admin-bg" key={bg.id}>
              <img src={api.baseUrl + bg.image_url} alt="" loading="lazy" />
              <input
                type="text"
                aria-label="Name"
                maxLength={80}
                defaultValue={bg.name}
                onBlur={(e) => {
                  const v = e.target.value.trim();
                  if (v && v !== bg.name) void patch(bg, { name: v });
                  else e.target.value = bg.name;
                }}
              />
              <div className="row">
                <label className="check small">
                  <input type="checkbox" checked={bg.dark} onChange={(e) => void patch(bg, { dark: e.target.checked })} />
                  Dark
                </label>
                <div className="spacer" />
                <button type="button" className="icon-btn danger" aria-label={`Remove ${bg.name}`} onClick={() => void remove(bg)}>
                  <LuTrash2 aria-hidden />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
