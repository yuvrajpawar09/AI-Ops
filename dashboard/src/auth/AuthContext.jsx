import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "./api.js";

const AuthContext = createContext(null);

export const ROLES = { ADMIN: "ADMIN", ENGINEER: "ENGINEER", VIEWER: "VIEWER" };

const CAPABILITIES = {
  ADMIN: ["view", "acknowledge", "trigger", "manageUsers"],
  ENGINEER: ["view", "acknowledge"],
  VIEWER: ["view"],
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("loading");

  const refresh = useCallback(async () => {
    try {
      const data = await authApi.me();
      setUser(data.user ?? null);
      setStatus(data.user ? "authenticated" : "anonymous");
      return data.user ?? null;
    } catch {
      setUser(null);
      setStatus("anonymous");
      return null;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (username, password) => {
    const data = await authApi.login(username, password);
    setUser(data.user);
    setStatus("authenticated");
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      status,
      login,
      logout,
      refresh,
      can: (capability) => CAPABILITIES[user?.role]?.includes(capability) ?? false,
    }),
    [user, status, login, logout, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
