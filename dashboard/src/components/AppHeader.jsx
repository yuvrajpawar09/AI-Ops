import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import { useTheme } from "../theme/ThemeContext.jsx";
import { StatusDot } from "./StatusDot.jsx";

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      className="icon-button"
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {theme === "dark" ? (
        <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
          <circle cx="10" cy="10" r="4" fill="currentColor" />
          <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M10 1.5v2.2M10 16.3v2.2M1.5 10h2.2M16.3 10h2.2M4 4l1.6 1.6M14.4 14.4L16 16M16 4l-1.6 1.6M5.6 14.4L4 16" />
          </g>
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
          <path
            d="M12.5 2.3a7.7 7.7 0 1 0 5.2 9.9A6.2 6.2 0 0 1 12.5 2.3z"
            fill="currentColor"
          />
        </svg>
      )}
    </button>
  );
}

export function AppHeader({ anomalies, incidents }) {
  const { user, logout, can } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const degraded = Boolean(anomalies?.error || incidents?.error);
  const overallState = degraded ? "unknown" : "good";

  async function onLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="dashboard-header">
      <div className="dashboard-header-left">
        <Link to="/" className="lp-brand lp-brand--compact">
          <span className="lp-brand-mark" aria-hidden="true" />
          <span>
            AI<span className="lp-brand-dim">-</span>OPS
          </span>
        </Link>
        <span className="subtitle">autonomous log anomaly detection &amp; root cause analysis</span>
      </div>

      <button
        className="icon-button header-menu-toggle"
        type="button"
        aria-expanded={menuOpen}
        aria-controls="header-actions"
        aria-label="Toggle header menu"
        onClick={() => setMenuOpen((v) => !v)}
      >
        <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
          <path d="M2.5 5h15M2.5 10h15M2.5 15h15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </button>

      <div id="header-actions" className={`dashboard-header-right${menuOpen ? " is-open" : ""}`}>
        <span className="header-status">
          <StatusDot state={overallState} />
          {anomalies?.data ? `${anomalies.data.count} anomalies` : "..."} &middot;{" "}
          {incidents?.data ? `${incidents.data.count} incidents` : "..."}
        </span>

        {can("manageUsers") && (
          <Link
            className={`header-nav-link${location.pathname === "/app/users" ? " is-active" : ""}`}
            to={location.pathname === "/app/users" ? "/app" : "/app/users"}
          >
            {location.pathname === "/app/users" ? "Dashboard" : "Users"}
          </Link>
        )}

        <ThemeToggle />

        <span className="header-user">
          <span className="header-username">{user?.username}</span>
          <span className={`role-badge role-badge--${(user?.role || "").toLowerCase()}`}>
            {user?.role}
          </span>
        </span>

        <button className="header-logout" type="button" onClick={onLogout}>
          Log out
        </button>
      </div>
    </header>
  );
}
