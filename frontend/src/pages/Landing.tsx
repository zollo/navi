import { Link, Navigate } from "react-router-dom";
import Logo from "../components/Logo";
import { useAuth } from "../context/AuthContext";

export default function Landing() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-screen muted">Loading…</div>;
  if (user) return <Navigate to="/edit" replace />;

  return (
    <div className="center-screen brand-backdrop">
      <div className="landing">
        <Logo size={112} />
        <h1 className="wordmark">Navi</h1>
        <p className="subtitle">One simple page for all of your important links.</p>
        <div className="row" style={{ justifyContent: "center" }}>
          <Link className="btn" to="/register">
            Create your page
          </Link>
          <Link className="btn secondary" to="/login">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
