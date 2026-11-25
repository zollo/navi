import { useEffect, useMemo, useState, type FormEvent } from "react";
import { LuCheck, LuCopy, LuExternalLink, LuTrash2 } from "react-icons/lu";
import { api, ApiError } from "../api/client";
import { clientSetups, mcpUrl, type ClientId } from "../lib/mcp";
import { copyText } from "../lib/page";
import type { ApiKey } from "../types";

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="icon-btn"
      aria-label={label}
      title={done ? "Copied" : label}
      onClick={async () => {
        if (await copyText(text)) {
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        }
      }}
    >
      {done ? <LuCheck aria-hidden /> : <LuCopy aria-hidden />}
    </button>
  );
}

function CodeBlock({ label, text }: { label: string; text: string }) {
  return (
    <div className="code-block">
      <div className="code-head">
        <span className="muted small">{label}</span>
        <CopyButton text={text} label={`Copy ${label}`} />
      </div>
      <pre>
        <code>{text}</code>
      </pre>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

// Account → AI tools: API keys plus copy-paste setup for MCP clients.
export default function Integrations() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [name, setName] = useState("");
  const [created, setCreated] = useState<ApiKey | null>(null);
  const [client, setClient] = useState<ClientId>("claude-code");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const url = mcpUrl(api.baseUrl, window.location.origin);
  const setups = useMemo(() => clientSetups(url, created?.key ?? null), [url, created]);
  const setup = setups.find((s) => s.id === client) ?? setups[0];

  const load = () =>
    api
      .get<ApiKey[]>("/api/api-keys")
      .then(setKeys)
      .catch(() => {});
  useEffect(() => {
    void load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setCreated(await api.post<ApiKey>("/api/api-keys", { name: name.trim() || setup.name }));
      setName("");
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the key");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (key: ApiKey) => {
    if (!window.confirm(`Revoke “${key.name}”? Anything using it stops working.`)) return;
    try {
      await api.del(`/api/api-keys/${key.id}`);
      if (created?.id === key.id) setCreated(null);
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't revoke the key");
    }
  };

  return (
    <div className="page narrow">
      <h1>AI tools</h1>
      <p className="subtitle">
        Let Claude, Copilot, Cursor and other AI assistants read and edit your page.
      </p>

      <div className="card">
        <h2>1. Create an API key</h2>
        <p className="muted small">
          A key works like your password for the page (it can't change your password or make
          more keys). Make one per app so you can revoke them separately.
        </p>
        {error && <div className="alert error">{error}</div>}
        {created?.key && (
          <div className="alert success">
            <strong>Copy this key now. It won't be shown again.</strong>
            <div className="dns-field key-field">
              <span className="small">Key</span>
              <code>{created.key}</code>
              <CopyButton text={created.key} label="Copy key" />
            </div>
            <div className="small">The setup below now includes it.</div>
          </div>
        )}
        <form className="row nowrap" onSubmit={create}>
          <input
            type="text"
            placeholder={`Key name, e.g. ${setup.name}`}
            aria-label="Key name"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="btn" disabled={busy}>
            Create key
          </button>
        </form>
        {keys.length > 0 && (
          <div className="key-list">
            {keys.map((k) => (
              <div key={k.id} className="key-row">
                <div className="key-meta">
                  <div className="name">{k.name}</div>
                  <div className="muted small">
                    <code>{k.prefix}…</code> · created {formatDate(k.created_at)} ·{" "}
                    {k.last_used_at ? `last used ${formatDate(k.last_used_at)}` : "never used"}
                  </div>
                </div>
                <button
                  type="button"
                  className="icon-btn danger"
                  aria-label={`Revoke ${k.name}`}
                  title="Revoke"
                  onClick={() => void revoke(k)}
                >
                  <LuTrash2 aria-hidden />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2>2. Connect your assistant</h2>
        <div className="dns-field key-field">
          <span className="muted small">MCP</span>
          <code>{url}</code>
          <CopyButton text={url} label="Copy MCP URL" />
        </div>
        <div className="segmented" role="tablist" aria-label="AI assistant">
          {setups.map((s) => (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={s.id === setup.id}
              className={s.id === setup.id ? "on" : ""}
              onClick={() => setClient(s.id)}
            >
              {s.name}
            </button>
          ))}
        </div>
        <div className="setup-body" role="tabpanel">
          {!created?.key && (
            <div className="alert info small">
              Replace &lt;your API key&gt; with a key, or create one above to fill it in.
            </div>
          )}
          <ol className="setup-steps">
            {setup.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {setup.install && (
            <a className="btn" href={setup.install.href}>
              <LuExternalLink aria-hidden /> {setup.install.label}
            </a>
          )}
          {setup.snippets.map((s) => (
            <CodeBlock key={s.label} label={s.label} text={s.text} />
          ))}
          {setup.note && <p className="muted small">{setup.note}</p>}
        </div>
      </div>

      <div className="card">
        <h2>Try it</h2>
        <p className="muted small">Once connected, ask things like:</p>
        <ul className="setup-steps">
          <li>“Add my new podcast to my Navi page, under a Listen section.”</li>
          <li>“Switch my page to a dark gradient background with pill buttons.”</li>
          <li>“Which of my links still point to http:// instead of https://?”</li>
        </ul>
        <p className="muted small">
          The assistant uses the same API as this app (
          <a href={`${api.baseUrl}/docs`} target="_blank" rel="noreferrer">
            API docs
          </a>
          ), so it can do anything you can do on the My page tab.
        </p>
      </div>
    </div>
  );
}
