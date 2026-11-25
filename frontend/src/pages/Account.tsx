import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import CustomDomainCard from "../components/CustomDomainCard";
import { useAuth } from "../context/AuthContext";
import type { BuildInfo, User } from "../types";

export default function Account() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState(user?.display_name ?? "");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [build, setBuild] = useState<BuildInfo | null>(null);

  useEffect(() => {
    api.get<BuildInfo>("/api/build-info").then(setBuild).catch(() => {});
  }, []);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    try {
      const body: Record<string, string> = { display_name: name };
      if (password) body.password = password;
      setUser(await api.patch<User>("/api/auth/me", body));
      setPassword("");
      setMsg({ kind: "success", text: "Saved." });
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't save" });
    }
  };

  const deletePage = async () => {
    if (!window.confirm("Delete your page? Your links will be gone and your handle freed.")) return;
    try {
      await api.del("/api/pages/me");
      navigate("/edit");
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't delete" });
    }
  };

  return (
    <div className="page narrow">
      <h1>Account</h1>
      <p className="subtitle">{user?.email}</p>
      {msg && <div className={`alert ${msg.kind}`}>{msg.text}</div>}
      <form className="card" onSubmit={save}>
        <div className="field">
          <label htmlFor="name">Name</label>
          <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">New password</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="help">Leave blank to keep your current password.</div>
        </div>
        <button className="btn">Save</button>
      </form>

      <CustomDomainCard />

      <div className="card">
        <h2>Danger zone</h2>
        <div className="row">
          <button type="button" className="btn danger" onClick={deletePage}>
            Delete my page
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </div>

      <p className="muted small" style={{ marginTop: 24 }}>
        Navi {build?.version ?? import.meta.env.VITE_APP_VERSION ?? "dev"}
        {build && build.git_commit !== "unknown" && ` · ${build.git_commit.slice(0, 7)}`}
        {" · "}
        <a href="/docs">API docs</a>
      </p>
    </div>
  );
}
