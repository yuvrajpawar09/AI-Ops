import { useCallback, useEffect, useState } from "react";

import { adminApi } from "../auth/api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { AppHeader } from "../components/AppHeader.jsx";
import { PanelError } from "../components/PanelError.jsx";
import { PanelSkeleton } from "../components/PanelSkeleton.jsx";
import { ROLES } from "../auth/AuthContext.jsx";

const ROLE_LIST = [ROLES.ADMIN, ROLES.ENGINEER, ROLES.VIEWER];

export default function Users() {
  const { user } = useAuth();
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(ROLES.VIEWER);
  const [formError, setFormError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await adminApi.listUsers();
      setUsers(data.users);
      setError(null);
      setStatus(null);
    } catch (err) {
      setError(err?.message || "failed");
      setStatus(err?.status ?? null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createUser(event) {
    event.preventDefault();
    setFormError(null);
    setNotice(null);
    setBusy(true);
    try {
      await adminApi.createUser(username.trim(), password, role);
      setNotice(`Created ${username.trim()} as ${role}.`);
      setUsername("");
      setPassword("");
      setRole(ROLES.VIEWER);
      await load();
    } catch (err) {
      setFormError(err?.message || "could not create user");
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(target, nextRole) {
    setNotice(null);
    setFormError(null);
    try {
      await adminApi.setRole(target, nextRole);
      setNotice(`${target} is now ${nextRole}.`);
      await load();
    } catch (err) {
      setFormError(err?.message || "could not change role");
    }
  }

  return (
    <div className="dashboard">
      <AppHeader />

      <div className="users-page">
        <section className="panel">
          <div className="panel-header">
            <h2>Users</h2>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {users ? users.length : "..."}
            </span>
          </div>
          <div className="panel-body">
            {error ? (
              <PanelError message={error} status={status} onRetry={load} />
            ) : loading ? (
              <PanelSkeleton rows={3} />
            ) : (
              <div className="users-table-wrap">
                <table className="users-table">
                  <thead>
                    <tr>
                      <th scope="col">Username</th>
                      <th scope="col">Role</th>
                      <th scope="col">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.username}>
                        <th scope="row">
                          {u.username}
                          {u.username === user?.username && <span className="users-self">you</span>}
                        </th>
                        <td>
                          <select
                            aria-label={`Role for ${u.username}`}
                            value={u.role}
                            disabled={u.username === user?.username}
                            onChange={(e) => changeRole(u.username, e.target.value)}
                          >
                            {ROLE_LIST.map((r) => (
                              <option key={r} value={r}>
                                {r}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="mono users-created">{u.createdAt}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Add a user</h2>
          </div>
          <div className="panel-body">
            <form className="users-form" onSubmit={createUser}>
              <label htmlFor="new-username">Username</label>
              <input
                id="new-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoCapitalize="none"
                spellCheck="false"
                required
              />

              <label htmlFor="new-password">Password</label>
              <input
                id="new-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />
              <p className="users-hint">At least 8 characters.</p>

              <label htmlFor="new-role">Role</label>
              <select id="new-role" value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLE_LIST.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>

              {formError && (
                <p className="login-error" role="alert">
                  {formError}
                </p>
              )}
              {notice && (
                <p className="users-notice" role="status">
                  {notice}
                </p>
              )}

              <button
                className="lp-btn lp-btn--primary"
                type="submit"
                disabled={busy || !username || password.length < 8}
              >
                {busy ? "Creating..." : "Create user"}
              </button>
            </form>

            <dl className="role-legend">
              <div>
                <dt>ADMIN</dt>
                <dd>Everything, plus the trigger panel and user management.</dd>
              </div>
              <div>
                <dt>ENGINEER</dt>
                <dd>Views every feed and acknowledges incidents. Cannot trigger or manage users.</dd>
              </div>
              <div>
                <dt>VIEWER</dt>
                <dd>Read-only.</dd>
              </div>
            </dl>
          </div>
        </section>
      </div>
    </div>
  );
}
