import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import PageView from "../components/PageView";
import { toInput } from "../lib/page";
import type { Page } from "../types";

// The public page at /<handle>. No sign-in needed.
export default function PublicPage() {
  const { handle = "" } = useParams();
  const [page, setPage] = useState<Page | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setPage(null);
    setError(null);
    api
      .get<Page>(`/api/pages/${encodeURIComponent(handle)}`)
      .then((p) => {
        if (!live) return;
        setPage(p);
        document.title = `${p.title || "@" + p.handle} · Navi`;
      })
      .catch((err) => {
        if (live) setError(err instanceof ApiError && err.status === 404 ? "notfound" : "error");
      });
    return () => {
      live = false;
    };
  }, [handle]);

  if (error) {
    return (
      <div className="center-screen">
        <div className="card" style={{ maxWidth: 400, textAlign: "center" }}>
          <h1>{error === "notfound" ? "No page here yet" : "Something went wrong"}</h1>
          <p className="muted">
            {error === "notfound"
              ? `Nobody has claimed @${handle} on Navi.`
              : "We couldn't load this page. Try again in a moment."}
          </p>
          <Link className="btn" to="/register">
            Create your own page
          </Link>
        </div>
      </div>
    );
  }
  if (!page) return <div className="center-screen muted">Loading…</div>;

  return (
    <main className="navi-shell">
      <PageView page={toInput(page)} avatarUrl={page.avatar_url} />
    </main>
  );
}
