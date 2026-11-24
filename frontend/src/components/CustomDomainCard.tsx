import { useEffect, useState, type FormEvent } from "react";
import { LuCopy, LuExternalLink } from "react-icons/lu";
import { api, ApiError } from "../api/client";
import { copyText } from "../lib/page";
import type { CustomDomain, DnsRecord, DomainConfig } from "../types";

function Records({ records }: { records: DnsRecord[] }) {
  const [copied, setCopied] = useState<string | null>(null);
  const copy = async (text: string) => {
    if (await copyText(text)) {
      setCopied(text);
      setTimeout(() => setCopied(null), 1500);
    }
  };
  return (
    <div className="dns-records">
      {records.map((r) => (
        <div className="dns-record" key={`${r.type}-${r.name}-${r.value}`}>
          <div className="dns-type">{r.type}</div>
          <div className="dns-fields">
            {(
              [
                ["Name", r.name],
                ["Value", r.value],
              ] as const
            ).map(([label, text]) => (
              <div className="dns-field" key={label}>
                <span className="muted small">{label}</span>
                <code>{text}</code>
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => copy(text)}
                  aria-label={`Copy ${label.toLowerCase()}`}
                  title={copied === text ? "Copied" : "Copy"}
                >
                  <LuCopy aria-hidden />
                </button>
              </div>
            ))}
            <div className="muted small">{r.purpose}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Account card: connect your own domain (www.example.com) to your page.
export default function CustomDomainCard() {
  const [config, setConfig] = useState<DomainConfig | null>(null);
  const [domain, setDomain] = useState<CustomDomain | null>(null);
  const [hostname, setHostname] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api
      .get<DomainConfig>("/api/domains/config")
      .then((c) => {
        if (!live) return;
        setConfig(c);
        if (!c.enabled) return;
        api
          .get<CustomDomain>("/api/domains/me")
          .then((d) => {
            if (live) setDomain(d);
          })
          .catch(() => {});
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);

  if (!config?.enabled) return null;

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const connect = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      setDomain(await api.put<CustomDomain>("/api/domains/me", { hostname }));
      setEditing(false);
      setHostname("");
    });
  };

  const verify = () =>
    run(async () => setDomain(await api.post<CustomDomain>("/api/domains/me/verify")));

  const disconnect = () => {
    if (!domain) return;
    if (!window.confirm(`Disconnect ${domain.hostname}? Your page stays at its Navi address.`)) {
      return;
    }
    run(async () => {
      await api.del("/api/domains/me");
      setDomain(null);
    });
  };

  const showForm = !domain || editing;

  return (
    <div className="card">
      <h2>Custom domain</h2>
      {error && <div className="alert error">{error}</div>}

      {domain && !editing && (
        <>
          <p>
            <strong>{domain.hostname}</strong>{" "}
            <span className={`badge ${domain.status}`}>
              {domain.status === "active" ? "Live" : "Waiting for DNS"}
            </span>
          </p>
          {domain.status === "active" ? (
            <p className="muted small">
              Your page is live at{" "}
              <a href={domain.url} target="_blank" rel="noopener noreferrer">
                {domain.url} <LuExternalLink aria-hidden />
              </a>
              . The HTTPS certificate can take a few minutes after the domain is first verified.
              Keep the records below: they're checked again from time to time.
            </p>
          ) : (
            <p className="muted small">
              Add these records at your domain's DNS provider. We check automatically every few
              minutes for a week; DNS changes can take up to an hour to show up.
            </p>
          )}
          {domain.last_error && <div className="alert info">{domain.last_error}</div>}
          {domain.status === "active" ? (
            <details>
              <summary className="small">DNS records</summary>
              <Records records={domain.records} />
            </details>
          ) : (
            <Records records={domain.records} />
          )}
          <div className="row" style={{ marginTop: 12 }}>
            {domain.status === "pending" && (
              <button type="button" className="btn small" onClick={verify} disabled={busy}>
                {busy ? "Checking…" : "Check now"}
              </button>
            )}
            <button
              type="button"
              className="btn secondary small"
              onClick={() => {
                setHostname(domain.hostname);
                setEditing(true);
              }}
              disabled={busy}
            >
              Change
            </button>
            <button type="button" className="btn danger small" onClick={disconnect} disabled={busy}>
              Disconnect
            </button>
          </div>
        </>
      )}

      {showForm && (
        <form onSubmit={connect}>
          <p className="muted small">
            Show your page on your own domain, like <code>www.example.com</code>. You'll add a
            DNS record pointing it at <code>{config.cname_target}</code>
            {config.ips.length > 0 && <> (or, for a bare domain, at {config.ips.join(", ")})</>}.
          </p>
          <div className="field">
            <label htmlFor="domain">Domain</label>
            <input
              id="domain"
              type="text"
              inputMode="url"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder="www.example.com"
              value={hostname}
              onChange={(e) => setHostname(e.target.value)}
              required
            />
          </div>
          <div className="row">
            <button className="btn small" disabled={busy || !hostname.trim()}>
              {busy ? "Saving…" : "Connect"}
            </button>
            {editing && (
              <button
                type="button"
                className="btn secondary small"
                onClick={() => setEditing(false)}
                disabled={busy}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
