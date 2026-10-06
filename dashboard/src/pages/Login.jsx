import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";
import { useForcedTheme } from "../theme/ThemeContext.jsx";

export default function Login() {
  useForcedTheme("dark");
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (status === "authenticated") {
    return <Navigate to={location.state?.from || "/app"} replace />;
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username.trim(), password);
      navigate(location.state?.from || "/app", { replace: true });
    } catch (err) {
      if (err?.status === 429) {
        setError("Too many attempts. Wait a minute and try again.");
      } else if (err?.status === 401) {
        setError("Incorrect username or password.");
      } else {
        setError(err?.message || "Sign in failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <Link className="lp-brand login-brand" to="/">
          <span className="lp-brand-mark" aria-hidden="true" />
          <span>
            AI<span className="lp-brand-dim">-</span>OPS
          </span>
        </Link>

        <h1>Sign in</h1>
        <p className="login-sub">
          The operations dashboard is restricted. Access level is decided by your assigned role.
        </p>

        <form onSubmit={onSubmit} noValidate>
          <label htmlFor="login-username">Username</label>
          <input
            id="login-username"
            name="username"
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck="false"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            aria-invalid={error ? "true" : undefined}
          />

          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={error ? "true" : undefined}
          />

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          <button
            className="lp-btn lp-btn--primary login-submit"
            type="submit"
            disabled={busy || !username || !password}
          >
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="login-foot">
          <Link to="/">Back to the overview</Link>
        </p>
      </div>
    </div>
  );
}
