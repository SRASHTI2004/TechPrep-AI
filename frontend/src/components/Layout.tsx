import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function Layout() {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) return <div className="center muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark small">T</span> TechPrep AI
        </div>
        <nav>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/documents">Documents</NavLink>
        </nav>
        <div className="user">
          <span className="muted" title={user.email}>
            {user.email}
            {user.role === "admin" && <span className="badge">admin</span>}
          </span>
          <button className="ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
