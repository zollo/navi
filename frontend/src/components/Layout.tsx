import type { ReactNode } from "react";
import { LuImages, LuPencil, LuUser } from "react-icons/lu";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

const TABS: { to: string; label: string; icon: ReactNode; admin?: boolean }[] = [
  { to: "/edit", label: "My page", icon: <LuPencil aria-hidden /> },
  { to: "/admin", label: "Backgrounds", icon: <LuImages aria-hidden />, admin: true },
  { to: "/account", label: "Account", icon: <LuUser aria-hidden /> },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const tabs = TABS.filter((t) => !t.admin || user?.is_admin);

  return (
    <>
      <nav className="app-nav">
        <NavLink to="/edit" className="brand">
          <Logo />
          Navi
        </NavLink>
        <div className="links">
          {tabs.map((t) => (
            <NavLink key={t.to} to={t.to}>
              {t.label}
            </NavLink>
          ))}
        </div>
        <div className="spacer" />
        <span className="user">{user?.display_name || user?.email}</span>
        <ThemeToggle />
        <button
          className="btn secondary small"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Sign out
        </button>
      </nav>
      <Outlet />
      <nav className="tabbar" aria-label="Main">
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to}>
            <span className="ico">{t.icon}</span>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
